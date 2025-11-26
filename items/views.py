from django.urls import reverse
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from django.contrib.auth import authenticate, login, get_user_model, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Simulacion, PrecioActivo
from .serializers import SimulacionSerializer
from django_ratelimit.decorators import ratelimit
from items.services.lambda_service import LambdaService
from .services.market_service import obtener_parametros_activos  
import numpy as np
from datetime import datetime, timedelta
import logging
from . import kernel
from decimal import Decimal, InvalidOperation
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import F
from .forms import TopUpForm, WithdrawForm
from .models import Wallet, Inversion


User = get_user_model()
logger = logging.getLogger(__name__)

# ===== HOME Y PÁGINAS PÚBLICAS =====

def home_view(request):
    """Página de inicio/landing page."""
    return render(request, 'home.html')

# ===== AUTENTICACIÓN =====

def login_view(request):
    """Vista de login con autenticación por email."""
    if request.method == "POST":
        email = request.POST.get('email')
        password = request.POST.get('password')

        user = authenticate(request, username=email, password=password)
        if user:
            login(request, user)
            # Si es admin o staff redirige al panel admin
            if getattr(user, "is_staff", False) or getattr(user, "is_superuser", False):
                return redirect('admin_panel')
            # Usuario normal
            return redirect('simular')
        messages.error(request, "Credenciales inválidas")

    return render(request, 'login.html')


@login_required
def admin_panel(request):
    """Panel administrativo para crear y eliminar usuarios."""
    # Permitir sólo staff/superuser
    if not (request.user.is_staff or request.user.is_superuser):
        return HttpResponseForbidden("Acceso denegado")

    # Manejo de acciones por POST: crear o borrar
    if request.method == "POST":
        action = request.POST.get("action")
        
        if action == "create":
            email = request.POST.get("email")
            password = request.POST.get("password")
            is_staff = request.POST.get("is_staff") == "on"

            if not email or not password:
                messages.error(request, "Email y contraseña son obligatorios.")
            else:
                try:
                    if User.objects.filter(email=email).exists():
                        messages.error(request, "El correo ya está registrado.")
                    else:
                        username_field = getattr(User, "USERNAME_FIELD", "username")
                        create_kwargs = {username_field: email}

                        try:
                            user = User.objects.create_user(**create_kwargs, password=password)
                        except TypeError:
                            user = User(**create_kwargs)
                            user.set_password(password)
                            user.save()

                        if hasattr(user, "is_staff"):
                            user.is_staff = is_staff
                            user.save()

                        messages.success(request, f"Usuario '{email}' creado correctamente.")
                        logger.info(f"Admin {request.user.email} creó usuario {email}")
                except Exception as e:
                    logger.error(f"Error creando usuario: {e}")
                    messages.error(request, "Error al crear el usuario.")

        elif action == "delete":
            user_id = request.POST.get("user_id")
            if not user_id:
                messages.error(request, "No se indicó el usuario a eliminar.")
            else:
                try:
                    to_delete = User.objects.get(pk=int(user_id))
                    if to_delete.pk == request.user.pk:
                        messages.error(request, "No puede eliminar su propia cuenta.")
                    else:
                        email_deleted = to_delete.email
                        to_delete.delete()
                        messages.success(request, "Usuario eliminado correctamente.")
                        logger.info(f"Admin {request.user.email} eliminó usuario {email_deleted}")
                except User.DoesNotExist:
                    messages.error(request, "Usuario no encontrado.")
                except Exception as e:
                    logger.error(f"Error eliminando usuario: {e}")
                    messages.error(request, "Error al eliminar el usuario.")

    users = User.objects.all().order_by("pk")
    return render(request, "admin_panel.html", {"users": users})


def register_view(request):
    """Vista de registro de nuevos usuarios."""
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if not email or not password:
            messages.error(request, "Email y contraseña son obligatorios.")
        elif password != confirm_password:
            messages.error(request, "Las contraseñas no coinciden.")
        elif User.objects.filter(email=email).exists():
            messages.error(request, "El correo ya está registrado.")
        else:
            try:
                user = User.objects.create_user(email=email, password=password)
                messages.success(request, "Usuario creado con éxito. Ahora inicia sesión.")
                logger.info(f"Nuevo usuario registrado: {email}")
                return redirect("login")
            except Exception as e:
                logger.error(f"Error registrando usuario: {e}")
                messages.error(request, "Error al crear el usuario.")

    return render(request, "register.html")


def logout_view(request):
    """Vista de logout."""
    logout(request)
    return redirect('login')


# ===== SIMULADOR =====

@login_required
def items_list_page(request):
    """Página principal del simulador."""
    user = request.user
    wallet, _ = Wallet.objects.get_or_create(user=user)
    user_type = "Premium" if getattr(user, "is_premium", False) else "Free"
    pago_url = reverse('pago_premium') if user_type == "Free" else None
    context = {
        "user_type": user_type,
        "pago_url": pago_url,
        "wallet_balance": wallet.balance,
        "top_up_url": reverse('top_up'),
        "withdraw_url": reverse('withdraw'),
        "wallet_invest_url": reverse('wallet_invest'),
        "investment_options": [
            {"slug": "cdt", "label": "CDT Bancario", "descripcion": "Baja volatilidad, ingresos estables"},
            {"slug": "sp500", "label": "S&P 500", "descripcion": "Portafolio diversificado de acciones"},
            {"slug": "btc", "label": "Cripto (BTC)", "descripcion": "Alta volatilidad, alto potencial"},
            {"slug": "nft", "label": "NFTs", "descripcion": "Activos digitales alternativos"}
        ]
    }
    return render(request, 'simulador.html', context)
# --- Pago simulado para ser premium ---

@login_required
@require_http_methods(["GET", "POST"])
def pago_premium(request):
    pago_exitoso = False
    datos_pago = {}
    meses = [f"{i:02d}" for i in range(1, 13)]
    anios = [f"{y}" for y in range(2025, 2036)]
    if request.method == "POST":
        nombre = request.POST.get("nombre", "")
        cedula = request.POST.get("cedula", "")
        tarjeta = request.POST.get("tarjeta", "")
        mes_venc = request.POST.get("mes_venc", "")
        anio_venc = request.POST.get("anio_venc", "")
        cvv = request.POST.get("cvv", "")
        vencimiento = f"{mes_venc}/{anio_venc[-2:]}" if mes_venc and anio_venc else ""
        # Validación simple
        error = None
        if not (nombre and cedula and tarjeta and mes_venc and anio_venc and cvv):
            error = "Por favor ingresa todos los datos correctamente."
        elif not (len(tarjeta) == 16 and tarjeta.isdigit()):
            error = "El número de tarjeta debe tener 16 dígitos."
        elif not (len(cvv) in [3,4] and cvv.isdigit()):
            error = "El CVV debe tener 3 o 4 dígitos."
        if not error:
            user = request.user
            user.is_premium = True
            user.save()
            pago_exitoso = True
            datos_pago = {"nombre": nombre, "cedula": cedula, "tarjeta": tarjeta, "vencimiento": vencimiento, "cvv": cvv, "mes_venc": mes_venc, "anio_venc": anio_venc}
        else:
            datos_pago = {"error": error, "nombre": nombre, "cedula": cedula, "tarjeta": tarjeta, "vencimiento": vencimiento, "cvv": cvv, "mes_venc": mes_venc, "anio_venc": anio_venc}
    return render(request, "pago_premium.html", {"pago_exitoso": pago_exitoso, "datos_pago": datos_pago, "meses": meses, "anios": anios})
    """Página principal del simulador."""
    return render(request, 'simulador.html')


@login_required
def detalle_simulacion(request, pk):
    """Obtiene detalles de una simulación específica."""
    try:
        simulacion = get_object_or_404(Simulacion, pk=pk, user=request.user)
        return JsonResponse({
            "monto": simulacion.monto,
            "meses": simulacion.meses,
            "creado": simulacion.creado.isoformat() if simulacion.creado else None
        })
    except Exception as e:
        logger.error(f"Error obteniendo detalle de simulación {pk}: {e}")
        return JsonResponse({"error": "Error al obtener simulación"}, status=500)


@login_required
@csrf_exempt
@ratelimit(key='user_or_ip', rate='5/m', block=True)
@require_http_methods(["POST"])
def simular(request):
    try:
        data = json.loads(request.body)
        monto = float(data.get("monto", 0))
        meses = int(data.get("meses", 1))

        # DEBUG TEMPORAL - VER QUÉ ESTÁ PASANDO
        from .services.market_service import MarketDataService
        logger.debug("INICIANDO DEBUG...")
        #MarketDataService.debug_datos_apis()
        
        # Obtener parámetros de activos
        activos = obtener_parametros_activos()
        
        # DEBUG: Mostrar qué parámetros se van a usar
        logger.debug("\nPARAMETROS QUE SE USARAN EN LA SIMULACION:")
        for nombre, params in activos.items():
            retorno = params["retorno"]
            volatilidad = params["volatilidad"]
            retorno_anual = (1 + retorno) ** 12 - 1
            print(f"   {nombre}:")
            print(f"     - Retorno mensual: {retorno:.6f} ({retorno*100:.4f}%)")
            print(f"     - Retorno anual: {retorno_anual:.4f} ({retorno_anual*100:.2f}%)")
            print(f"     - Volatilidad mensual: {volatilidad:.6f} ({volatilidad*100:.4f}%)")
            
            # Calcular qué pasaría con estos parámetros
            resultado_esperado = monto * ((1 + retorno) ** meses)
            print(f"     → Resultado esperado en {meses} meses: ${resultado_esperado:,.0f}")

        # Validar entrada
        if not (0 < monto <= 100000000):
            return JsonResponse(
                {"error": "Monto debe estar entre $1 y $100.000.000"},
                status=400
            )
        if not (0 < meses <= 360):
            return JsonResponse(
                {"error": "Meses debe estar entre 1 y 360"},
                status=400
            )

        # ===== OBTENER PARÁMETROS DE MERCADO =====
        logger.info(f"Usuario {request.user.email} simulando: ${monto:,.0f} por {meses} meses")
        
        # Ejecutar simulación
        resultados = _ejecutar_simulacion(monto, meses, activos)

        # Guardar en BD
        simulacion = Simulacion.objects.create(
            user=request.user,
            monto=monto,
            meses=meses
        )
        serializer = SimulacionSerializer(simulacion)

        # Preparar metadata
        metadata = {
            "fecha_simulacion": datetime.now().isoformat(),
            "fuentes": {
                "cdt": activos["CDT Bancario"].get("info", {}).get("fuente", "N/A"),
                "sp500": activos["S&P 500"].get("info", {}).get("fuente", "N/A"),
                "btc": activos["Cripto (BTC)"].get("info", {}).get("fuente", "N/A"),
                "nfts": activos["NFTs"].get("info", {}).get("fuente", "N/A"),
            },
            "tasa_dtf": activos["CDT Bancario"].get("info", {}).get("tasa", 0) * 100,
            "periodo_dtf": activos["CDT Bancario"].get("info", {}).get("periodo", "N/A")
        }

        logger.info(f"✅ Simulación completada para {request.user.email}")

        return JsonResponse({
            "simulacion": serializer.data,
            "resultados": resultados,
            "metadata": metadata
        })

    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON inválido"}, status=400)
    except ValueError as e:
        return JsonResponse({"error": f"Error en valores: {str(e)}"}, status=400)
    except Exception as e:
        logger.error(f"❌ Error en simulación para {request.user.email}: {e}", exc_info=True)
        return JsonResponse({"error": "Error procesando datos. Por favor intenta nuevamente."}, status=500)

def _ejecutar_simulacion(monto, meses, activos):
    """
    Versión optimizada que evita duplicar llamadas a APIs
    """
    try:
        from .hexagonal.application.use_cases.simulate_investment import SimulateInvestmentUseCase
        
        use_case = SimulateInvestmentUseCase()
        return use_case.execute_with_existing_data(monto, meses, activos)
        
    except Exception as e:
        logger.warning(f"Usando implementación legacy: {e}")
        return _ejecutar_simulacion_legacy(monto, meses, activos)


def _ejecutar_simulacion_legacy(monto, meses, activos):
    """
    Versión SEGURA con límites estrictos y crecimiento realista
    """
    resultados = {}
    
    # Factores de crecimiento MÁXIMOS realistas (por año, no en 10 años)
    # Estos se aplican proporcionalmente al tiempo
    factores_maximos_anuales = {
        "CDT Bancario": 1.12,     # 12% anual máximo (muy conservador para CDT)
        "S&P 500": 1.40,          # 40% anual máximo  
        "Cripto (BTC)": 2.0,      # 100% anual máximo
        "NFTs": 2.5               # 150% anual máximo
    }
    
    # Factores de crecimiento MÍNIMOS (por año)
    factores_minimos_anuales = {
        "CDT Bancario": 1.08,     # 8% anual mínimo (realista para CDT)
        "S&P 500": 0.95,          # -5% anual mínimo (perdida moderada)
        "Cripto (BTC)": 0.8,      # -20% anual mínimo
        "NFTs": 0.5               # -50% anual mínimo
    }
    
    for nombre, params in activos.items():
        retorno = params["retorno"]
        volatilidad = params["volatilidad"]
        
        logger.debug(f"Simulando {nombre}: retorno={retorno:.4f} mensual, vol={volatilidad:.4f}")
        
        # Calcular factores proporcionales al tiempo
        años = meses / 12.0
        factor_max_ajustado = factores_maximos_anuales.get(nombre, 1.5) ** años
        factor_min_ajustado = factores_minimos_anuales.get(nombre, 1.0) ** años
        
        # 1. ESCENARIO ESPERADO (con límites estrictos proporcionales al tiempo)
        esperado = monto * ((1 + retorno) ** meses)
        esperado = min(esperado, monto * factor_max_ajustado)
        esperado = max(esperado, monto * factor_min_ajustado)
        
        # 2. MEJOR CASO (no extremo)
        mejor_retorno = retorno + (volatilidad * 0.5)  # Solo media desviación estándar
        mejor = monto * ((1 + mejor_retorno) ** meses)
        # Para CDT, el mejor caso no debe exceder mucho el límite máximo
        if nombre == "CDT Bancario":
            mejor = min(mejor, monto * factor_max_ajustado * 1.05)  # Máximo 5% extra para CDT
        else:
            mejor = min(mejor, monto * factor_max_ajustado * 1.2)  # Máximo 20% extra para otros
        
        # 3. PEOR CASO (no catastrófico)
        peor_retorno = retorno - (volatilidad * 0.5)  # Solo media desviación estándar
        peor_retorno = max(peor_retorno, -0.2)  # Máximo -20% mensual
        peor = monto * ((1 + peor_retorno) ** meses)
        peor = max(peor, monto * factor_min_ajustado)
        
        # Cálculos
        ganancia = esperado - monto
        ganancia_porcentaje = round((ganancia / monto * 100), 2) if monto > 0 else 0
        
        resultados[nombre] = {
            "esperado": round(esperado, 2),
            "mejor": round(mejor, 2),
            "peor": round(peor, 2),
            "ganancia": round(ganancia, 2),
            "ganancia_porcentaje": ganancia_porcentaje,
            "recomendacion": params.get("recomendacion", ""),
            "retorno_mensual": round(retorno * 100, 4),
            "volatilidad_mensual": round(volatilidad * 100, 4)
        }
        
        logger.debug(f"   {nombre}: ${monto:,.0f} -> ${esperado:,.0f} (x{esperado/monto:.1f})")
    
    return resultados


@login_required
def historial_simulaciones(request):
    """Obtiene el historial de simulaciones del usuario."""
    try:
        simulaciones = Simulacion.objects.filter(
            user=request.user
        ).order_by("-creado")
        serializer = SimulacionSerializer(simulaciones, many=True)
        return JsonResponse(serializer.data, safe=False)
    except Exception as e:
        logger.error(f"Error obteniendo historial para {request.user.email}: {e}")
        return JsonResponse({"error": "Error al obtener historial"}, status=500)


@login_required
def historial_inversiones(request):
    """Obtiene el historial de inversiones del usuario (todas, no solo activas)."""
    try:
        inversiones = Inversion.objects.filter(
            user=request.user
        ).order_by("-fecha_inicio")
        
        inversiones_data = []
        for inv in inversiones:
            # Asegurar que la fecha de vencimiento se calcule si no existe
            if not inv.fecha_vencimiento and inv.fecha_inicio and inv.meses:
                inv.fecha_vencimiento = inv.calcular_fecha_vencimiento()
                inv.save(update_fields=['fecha_vencimiento'])
            
            inversiones_data.append({
                'id': inv.id,
                'tipo_activo': inv.get_tipo_activo_display(),
                'tipo_activo_codigo': inv.tipo_activo,
                'monto_invertido': float(inv.monto_invertido),
                'valor_esperado': float(inv.valor_esperado) if inv.valor_esperado else None,
                'ganancia_esperada': float(inv.ganancia_esperada) if inv.ganancia_esperada else None,
                'rentabilidad_porcentaje': float(inv.rentabilidad_porcentaje) if inv.rentabilidad_porcentaje else None,
                'meses': inv.meses,
                'estado': inv.estado,
                'fecha_inicio': inv.fecha_inicio.isoformat() if inv.fecha_inicio else None,
                'fecha_vencimiento': inv.fecha_vencimiento.isoformat() if inv.fecha_vencimiento else None,
                'fecha_finalizacion': inv.fecha_finalizacion.isoformat() if inv.fecha_finalizacion else None,
            })
        
        return JsonResponse(inversiones_data, safe=False)
    except Exception as e:
        logger.error(f"Error obteniendo historial de inversiones para {request.user.email}: {e}", exc_info=True)
        return JsonResponse({"error": "Error al obtener historial de inversiones"}, status=500)


@login_required
@require_http_methods(["DELETE"])
def eliminar_simulacion(request, simulacion_id):
    """Elimina una simulación específica del usuario."""
    try:
        simulacion = get_object_or_404(Simulacion, id=simulacion_id, user=request.user)
        simulacion.delete()
        logger.info(f"Simulación {simulacion_id} eliminada por {request.user.email}")
        return JsonResponse({"success": True, "message": "Simulación eliminada correctamente"})
    except Exception as e:
        logger.error(f"Error eliminando simulación {simulacion_id} para {request.user.email}: {e}")
        return JsonResponse({"error": "Error al eliminar la simulación"}, status=500)


@login_required
@require_http_methods(["DELETE"])
def eliminar_todas_simulaciones(request):
    """Elimina todas las simulaciones del usuario."""
    try:
        simulaciones = Simulacion.objects.filter(user=request.user)
        count = simulaciones.count()
        simulaciones.delete()
        logger.info(f"{count} simulaciones eliminadas por {request.user.email}")
        return JsonResponse({
            "success": True, 
            "message": f"{count} simulaciones eliminadas correctamente",
            "count": count
        })
    except Exception as e:
        logger.error(f"Error eliminando todas las simulaciones para {request.user.email}: {e}")
        return JsonResponse({"error": "Error al eliminar las simulaciones"}, status=500)


@login_required
def portafolio_api(request):
    """API para obtener datos del portafolio del usuario."""
    try:
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        inversiones = Inversion.objects.filter(
            user=request.user,
            estado='activa'
        ).order_by('-fecha_inicio')
        
        logger.info(f"Obteniendo portafolio para {request.user.email}: {inversiones.count()} inversiones activas")
        
        inversiones_data = []
        total_invertido = Decimal('0')
        total_esperado = Decimal('0')
        
        for inv in inversiones:
            total_invertido += inv.monto_invertido
            if inv.valor_esperado:
                total_esperado += inv.valor_esperado
            
            # Asegurar que la fecha de vencimiento se calcule si no existe
            if not inv.fecha_vencimiento and inv.fecha_inicio and inv.meses:
                inv.fecha_vencimiento = inv.calcular_fecha_vencimiento()
                inv.save(update_fields=['fecha_vencimiento'])
            
            inversiones_data.append({
                'id': inv.id,
                'tipo_activo': inv.get_tipo_activo_display(),
                'tipo_activo_codigo': inv.tipo_activo,
                'monto_invertido': float(inv.monto_invertido),
                'valor_esperado': float(inv.valor_esperado) if inv.valor_esperado else None,
                'ganancia_esperada': float(inv.ganancia_esperada) if inv.ganancia_esperada else None,
                'rentabilidad_porcentaje': float(inv.rentabilidad_porcentaje) if inv.rentabilidad_porcentaje else None,
                'meses': inv.meses,
                'fecha_inicio': inv.fecha_inicio.isoformat() if inv.fecha_inicio else None,
                'fecha_vencimiento': inv.fecha_vencimiento.isoformat() if inv.fecha_vencimiento else None,
            })
        
        # Calcular rendimiento convirtiendo todo a float para evitar errores de tipo
        total_invertido_float = float(total_invertido)
        total_esperado_float = float(total_esperado)
        
        rendimiento_total = total_esperado_float - total_invertido_float if total_esperado_float > 0 else 0.0
        rendimiento_porcentaje = 0.0
        if total_invertido_float > 0:
            rendimiento_porcentaje = (rendimiento_total / total_invertido_float) * 100.0
        
        response_data = {
            'saldo_total': float(wallet.balance),
            'total_invertido': float(total_invertido),
            'total_esperado': float(total_esperado),
            'rendimiento_total': rendimiento_total,
            'rendimiento_porcentaje': rendimiento_porcentaje,
            'inversiones_activas': len(inversiones),
            'inversiones': inversiones_data
        }
        
        logger.info(f"Portafolio para {request.user.email}: {response_data['inversiones_activas']} inversiones, saldo: {response_data['saldo_total']}")
        
        return JsonResponse(response_data)
    except Exception as e:
        logger.error(f"Error obteniendo portafolio para {request.user.email}: {e}", exc_info=True)
        return JsonResponse({"error": f"Error al obtener portafolio: {str(e)}"}, status=500)


@login_required
def analytics_api(request):
    """API para obtener datos de analíticas del usuario."""
    try:
        # Obtener tipo de analítica solicitada (simulaciones o inversiones)
        tipo_analitica = request.GET.get('tipo', 'simulaciones')  # Por defecto simulaciones
        
        simulaciones = Simulacion.objects.filter(
            user=request.user
        ).order_by('-creado')
        
        inversiones = Inversion.objects.filter(
            user=request.user
        ).order_by('-fecha_inicio')
        
        # Si se solicita analítica de inversiones
        if tipo_analitica == 'inversiones':
            # Estadísticas de inversiones
            total_invertido = sum(inv.monto_invertido for inv in inversiones)
            total_esperado = sum(inv.valor_esperado for inv in inversiones if inv.valor_esperado)
            promedio_inversion = total_invertido / len(inversiones) if inversiones else 0
            
            # Distribución por activo (de inversiones)
            distribucion_activos = {}
            for inv in inversiones:
                tipo_activo = inv.get_tipo_activo_display()
                if tipo_activo not in distribucion_activos:
                    distribucion_activos[tipo_activo] = {
                        'cantidad': 0,
                        'monto_total': Decimal('0')
                    }
                distribucion_activos[tipo_activo]['cantidad'] += 1
                distribucion_activos[tipo_activo]['monto_total'] += inv.monto_invertido
            
            # Timeline de inversiones
            inversiones_timeline = [{
                'fecha': inv.fecha_inicio.isoformat(),
                'monto': float(inv.monto_invertido),
                'meses': inv.meses,
                'tipo_activo': inv.get_tipo_activo_display()
            } for inv in inversiones[:50]]  # Últimas 50
            
            # Si no hay distribución por activos (aunque haya inversiones), crear distribución por rango como alternativa
            distribucion_rangos = None
            if not distribucion_activos:
                rangos = {
                    'Hasta $1M': {'cantidad': 0, 'monto_total': Decimal('0')},
                    '$1M - $5M': {'cantidad': 0, 'monto_total': Decimal('0')},
                    '$5M - $10M': {'cantidad': 0, 'monto_total': Decimal('0')},
                    'Más de $10M': {'cantidad': 0, 'monto_total': Decimal('0')}
                }
                
                for inv in inversiones:
                    monto = float(inv.monto_invertido)
                    if monto < 1000000:
                        rango = 'Hasta $1M'
                    elif monto < 5000000:
                        rango = '$1M - $5M'
                    elif monto < 10000000:
                        rango = '$5M - $10M'
                    else:
                        rango = 'Más de $10M'
                    
                    rangos[rango]['cantidad'] += 1
                    rangos[rango]['monto_total'] += Decimal(str(monto))
                
                distribucion_rangos = {
                    k: {
                        'cantidad': v['cantidad'],
                        'monto_total': float(v['monto_total'])
                    }
                    for k, v in rangos.items() if v['cantidad'] > 0
                }
            
            return JsonResponse({
                'tipo': 'inversiones',
                'total_invertido': float(total_invertido),
                'total_esperado': float(total_esperado),
                'promedio_inversion': float(promedio_inversion),
                'distribucion_activos': {
                    k: {
                        'cantidad': v['cantidad'],
                        'monto_total': float(v['monto_total'])
                    }
                    for k, v in distribucion_activos.items()
                } if distribucion_activos else {},
                'distribucion_rangos': distribucion_rangos,
                'inversiones_timeline': inversiones_timeline,
                'total_inversiones': len(inversiones)
            })
        
        # Analítica de simulaciones (comportamiento por defecto)
        # Estadísticas de simulaciones
        total_simulado = sum(sim.monto for sim in simulaciones)
        promedio_simulacion = total_simulado / len(simulaciones) if simulaciones else 0
        
        # Distribución por rango de monto simulado (SIEMPRE para simulaciones)
        distribucion_simulaciones = None
        if simulaciones:
            # Distribución por rango de monto simulado
            rangos = {
                'Hasta $1M': {'cantidad': 0, 'monto_total': Decimal('0')},
                '$1M - $5M': {'cantidad': 0, 'monto_total': Decimal('0')},
                '$5M - $10M': {'cantidad': 0, 'monto_total': Decimal('0')},
                'Más de $10M': {'cantidad': 0, 'monto_total': Decimal('0')}
            }
            
            for sim in simulaciones:
                monto = sim.monto
                if monto < 1000000:
                    rango = 'Hasta $1M'
                elif monto < 5000000:
                    rango = '$1M - $5M'
                elif monto < 10000000:
                    rango = '$5M - $10M'
                else:
                    rango = 'Más de $10M'
                
                rangos[rango]['cantidad'] += 1
                rangos[rango]['monto_total'] += Decimal(str(monto))
            
            # Solo incluir rangos que tengan simulaciones
            distribucion_simulaciones = {
                k: {
                    'cantidad': v['cantidad'],
                    'monto_total': float(v['monto_total'])
                }
                for k, v in rangos.items() if v['cantidad'] > 0
            }
        
        # Datos para gráficos
        simulaciones_timeline = [{
            'fecha': sim.creado.isoformat(),
            'monto': sim.monto,
            'meses': sim.meses
        } for sim in simulaciones[:50]]  # Últimas 50
        
        return JsonResponse({
            'tipo': 'simulaciones',
            'total_simulado': float(total_simulado),
            'promedio_simulacion': float(promedio_simulacion),
            'distribucion_simulaciones': distribucion_simulaciones,  # Distribución por rango de monto
            'simulaciones_timeline': simulaciones_timeline,
            'total_simulaciones': len(simulaciones),
            'total_inversiones': len(inversiones)
        })
    except Exception as e:
        logger.error(f"Error obteniendo analíticas para {request.user.email}: {e}", exc_info=True)
        return JsonResponse({"error": "Error al obtener analíticas"}, status=500)


@login_required
def actualizar_precios(request):
    """
    Endpoint para actualizar manualmente los precios de mercado.
    Útil para testing o actualizaciones forzadas.
    """
    try:
        from .services.market_service import MarketDataService
        
        logger.info(f"🔄 Actualización manual iniciada por {request.user.email}")
        
        # Obtener datos frescos
        datos = MarketDataService.obtener_datos_completos()
        
        logs = [
            f"✅ CDT: {datos['cdt']['tasa']*100:.2f}% ({datos['cdt']['fuente']})",
            f"✅ S&P 500: {len(datos['sp500']['precios'])} precios ({datos['sp500']['fuente']})",
            f"✅ Bitcoin: {len(datos['btc']['precios'])} precios ({datos['btc']['fuente']})",
            f"✅ NFTs: {len(datos['nfts']['precios'])} precios ({datos['nfts']['fuente']})"
        ]
        
        logger.info("✅ Precios actualizados manualmente")
        
        return JsonResponse({
            "success": True,
            "logs": logs,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Error actualizando precios: {e}")
        return JsonResponse(
            {"error": f"Error actualizando precios: {str(e)}"},
            status=500
        )
    

@login_required
def ejecutar_lambda(request):
    """Ejecuta función Lambda (para pruebas/arquitectura)."""
    try:
        client = LambdaService()
        result = client.invoke("arquitectura_software", {"numero": 42})
        return JsonResponse(result)
    except Exception as e:
        logger.error(f"Error invocando Lambda: {e}")
        return JsonResponse({"error": "Error invocando Lambda"}, status=500)
    
@login_required
def consultar_precio(request):
    # Ejemplo: validar tipo de usuario
    user = request.user
    if getattr(user, "is_premium", False):
        kernel.K.activate_plugin("PremiumPlan")
    else:
        kernel.K.activate_plugin("FreePlan")

    result = kernel.K.execute("consultar_precio")
    return HttpResponse(result)

@login_required
def top_up_view(request):
    """
    Permite al usuario agregar un monto a su wallet (saldo).
    """
    user = request.user
    # Asegurar que el usuario tiene wallet (la señal la crea para nuevos usuarios)
    wallet, _ = Wallet.objects.get_or_create(user=user)

    payment_receipt = None

    if request.method == 'POST':
        form = TopUpForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            try:
                with transaction.atomic():
                    # Actualizar balance usando F() para evitar race conditions
                    Wallet.objects.filter(pk=wallet.pk).update(
                        balance=F('balance') + amount
                    )
                    # Refrescar el wallet para obtener el nuevo balance
                    wallet.refresh_from_db()
                
                payment_receipt = {
                    "reference": f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    "holder": form.cleaned_data["full_name"],
                    "amount": amount,
                    "masked_card": f"**** **** **** {form.cleaned_data['card_number'][-4:]}",
                }
                messages.success(request, f"Se han agregado ${amount:,.2f} COP a tu wallet. Tu nuevo saldo es ${wallet.balance:,.2f} COP.")
                return redirect('simular')
            except Exception as e:
                logger.error(f"Error actualizando wallet para {user.email}: {e}", exc_info=True)
                messages.error(request, f"Error al actualizar el wallet: {e}")
    else:
        form = TopUpForm()

    # Refrescar wallet antes de mostrar (por si acaso)
    wallet.refresh_from_db()

    context = {
        'form': form,
        'wallet': wallet,
        'payment_receipt': payment_receipt
    }
    return render(request, 'top_up.html', context)


@login_required
@require_http_methods(["POST"])
def wallet_invest_view(request):
    """
    Permite invertir saldo del wallet en los activos principales.
    El resultado esperado se acredita inmediatamente (simulado).
    """
    asset_choice = request.POST.get("asset")
    amount_raw = request.POST.get("amount")
    months_raw = request.POST.get("months", "12")

    asset_map = {
        "cdt": "CDT Bancario",
        "sp500": "S&P 500",
        "btc": "Cripto (BTC)",
        "nft": "NFTs"
    }

    if asset_choice not in asset_map:
        messages.error(request, "Selecciona un activo válido para invertir.")
        return redirect('simular')

    try:
        amount = Decimal(amount_raw)
    except (InvalidOperation, TypeError):
        messages.error(request, "El monto ingresado no es válido.")
        return redirect('simular')

    if amount <= Decimal('0'):
        messages.error(request, "El monto a invertir debe ser mayor que 0.")
        return redirect('simular')

    try:
        months = int(months_raw)
    except (TypeError, ValueError):
        months = 12

    months = max(1, min(360, months))

    wallet, _ = Wallet.objects.get_or_create(user=request.user)

    # Verificar saldo disponible antes de procesar la simulación
    if wallet.balance < amount:
        messages.error(request, "No tienes saldo suficiente en tu wallet para esta inversión.")
        return redirect('simular')

    try:
        activos = obtener_parametros_activos()
        resultados = _ejecutar_simulacion(float(amount), months, activos)
        activo_nombre = asset_map[asset_choice]
        if activo_nombre not in resultados:
            raise KeyError("Activo no disponible.")
        resultado_activo = resultados[activo_nombre]
        valor_esperado = Decimal(str(resultado_activo["esperado"])).quantize(Decimal('0.01'))
    except Exception as exc:
        logger.error("Error procesando inversión en wallet: %s", exc, exc_info=True)
        messages.error(request, "No pudimos calcular la rentabilidad. Intenta más tarde.")
        return redirect('simular')

    ganancia = valor_esperado - amount

    try:
        with transaction.atomic():
            wallet_locked = Wallet.objects.select_for_update().get(pk=wallet.pk)
            if wallet_locked.balance < amount:
                messages.error(request, "El saldo cambió y ya no es suficiente para invertir.")
                return redirect('simular')
            wallet_locked.balance = wallet_locked.balance - amount + valor_esperado
            wallet_locked.save()
            nuevo_saldo = wallet_locked.balance
            
            # Crear registro de inversión
            Inversion.objects.create(
                user=request.user,
                wallet=wallet_locked,
                tipo_activo=asset_choice,
                monto_invertido=amount,
                meses=months,
                valor_esperado=valor_esperado,
                ganancia_esperada=ganancia,
                rentabilidad_porcentaje=Decimal(str(resultado_activo.get("ganancia_porcentaje", 0))),
                estado='activa'
            )
    except Exception as exc:
        logger.error("Error actualizando wallet tras inversión: %s", exc, exc_info=True)
        messages.error(request, "No pudimos actualizar tu wallet. Intenta nuevamente.")
        return redirect('simular')

    messages.success(
        request,
        (
            f"Inversión en {activo_nombre} ejecutada. Resultado proyectado: "
            f"${valor_esperado:,.2f} COP ({'+' if ganancia >= 0 else ''}{ganancia:,.2f}). "
            f"Nuevo saldo en wallet: ${nuevo_saldo:,.2f} COP."
        )
    )
    return redirect('simular')


@login_required
def withdraw_view(request):
    """
    Permite al usuario retirar dinero de su wallet a una cuenta bancaria.
    """
    user = request.user
    wallet, _ = Wallet.objects.get_or_create(user=user)

    if request.method == 'POST':
        form = WithdrawForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            
            # Validar que el usuario tenga saldo suficiente
            if wallet.balance < amount:
                messages.error(request, f"No tienes saldo suficiente. Tu saldo actual es ${wallet.balance:,.2f} COP.")
                form = WithdrawForm(request.POST)  # Mantener los datos ingresados
            else:
                try:
                    with transaction.atomic():
                        # Bloquear el wallet para evitar condiciones de carrera
                        wallet_locked = Wallet.objects.select_for_update().get(pk=wallet.pk)
                        
                        # Verificar nuevamente el saldo después del bloqueo
                        if wallet_locked.balance < amount:
                            messages.error(request, "El saldo cambió y ya no es suficiente para este retiro.")
                            return redirect('withdraw')
                        
                        # Descontar el monto del wallet
                        wallet_locked.balance = F('balance') - amount
                        wallet_locked.save()
                        
                        # Refrescar el objeto para obtener el nuevo balance
                        wallet_locked.refresh_from_db()
                        nuevo_saldo = wallet_locked.balance
                    
                    # Generar comprobante de retiro
                    withdrawal_receipt = {
                        "reference": f"RET-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                        "account_number": form.cleaned_data["account_number"],
                        "account_type": form.cleaned_data["account_type"],
                        "bank_name": form.cleaned_data["bank_name"],
                        "amount": amount,
                        "new_balance": nuevo_saldo,
                    }
                    
                    messages.success(
                        request,
                        f"Retiro de ${amount:,.2f} COP procesado exitosamente. "
                        f"El dinero será transferido a la cuenta {form.cleaned_data['account_number']} "
                        f"en {form.cleaned_data['bank_name']}. Nuevo saldo: ${nuevo_saldo:,.2f} COP."
                    )
                    logger.info(f"Usuario {user.email} retiró ${amount:,.2f} COP. Nuevo saldo: ${nuevo_saldo:,.2f}")
                    return redirect('simular')
                    
                except Exception as e:
                    logger.error(f"Error procesando retiro para {user.email}: {e}", exc_info=True)
                    messages.error(request, f"Error al procesar el retiro: {e}")
    else:
        form = WithdrawForm()

    context = {
        'form': form,
        'wallet': wallet,
    }
    return render(request, 'withdraw.html', context)


@login_required
def historial(request):
    if getattr(request.user, "is_premium", False):
        kernel.K.activate_plugin("PremiumPlan")
    else:
        kernel.K.activate_plugin("FreePlan")

    result = kernel.K.execute("historial")
    return HttpResponse(result)
    """Ejecuta función Lambda (para pruebas/arquitectura)."""
    try:
        client = LambdaService()
        result = client.invoke("arquitectura_software", {"numero": 42})
        return JsonResponse(result)
    except Exception as e:
        logger.error(f"Error invocando Lambda: {e}")
        return JsonResponse({"error": "Error invocando Lambda"}, status=500)
    


