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
    # Identificar tipo de usuario
    user_type = "Premium" if getattr(request.user, "is_premium", False) else "Free"
    pago_url = reverse('pago_premium') if user_type == "Free" else None
    return render(request, 'simulador.html', {"user_type": user_type, "pago_url": pago_url})
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
        print("🔍 INICIANDO DEBUG...")
        MarketDataService.debug_datos_apis()
        
        # Obtener parámetros de activos
        activos = obtener_parametros_activos()
        
        # DEBUG: Mostrar qué parámetros se van a usar
        print("\n🎯 PARÁMETROS QUE SE USARÁN EN LA SIMULACIÓN:")
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
        logger.info(f"🔄 Usuario {request.user.email} simulando: ${monto:,.0f} por {meses} meses")
        
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
                "cdt": activos["CDT Bancario"]["info"].get("fuente", "N/A"),
                "sp500": activos["S&P 500"]["info"].get("fuente", "N/A"),
                "btc": activos["Cripto (BTC)"]["info"].get("fuente", "N/A"),
                "nfts": activos["NFTs"]["info"].get("fuente", "N/A"),
            },
            "tasa_dtf": activos["CDT Bancario"]["info"].get("tasa", 0) * 100,
            "periodo_dtf": activos["CDT Bancario"]["info"].get("periodo", "N/A")
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
    Versión SEGURA con límites estrictos y crecimiento realista
    """
    resultados = {}
    
    # Factores de crecimiento MÁXIMOS realistas (en 10 años)
    factores_maximos = {
        "CDT Bancario": 2.5,      # 150% en 10 años
        "S&P 500": 4.0,           # 300% en 10 años  
        "Cripto (BTC)": 10.0,     # 900% en 10 años
        "NFTs": 15.0              # 1400% en 10 años
    }
    
    # Factores de crecimiento MÍNIMOS
    factores_minimos = {
        "CDT Bancario": 1.2,      # 20% en 10 años
        "S&P 500": 0.5,           # -50% en 10 años
        "Cripto (BTC)": 0.1,      # -90% en 10 años
        "NFTs": 0.01              # -99% en 10 años
    }
    
    for nombre, params in activos.items():
        retorno = params["retorno"]
        volatilidad = params["volatilidad"]
        
        print(f"🎯 Simulando {nombre}: retorno={retorno:.4f} mensual, vol={volatilidad:.4f}")
        
        # 1. ESCENARIO ESPERADO (con límites estrictos)
        esperado = monto * ((1 + retorno) ** meses)
        esperado = min(esperado, monto * factores_maximos[nombre])
        esperado = max(esperado, monto * factores_minimos[nombre])
        
        # 2. MEJOR CASO (no extremo)
        mejor_retorno = retorno + (volatilidad * 0.5)  # Solo media desviación estándar
        mejor = monto * ((1 + mejor_retorno) ** meses)
        mejor = min(mejor, monto * factores_maximos[nombre] * 1.2)  # Máximo 20% extra
        
        # 3. PEOR CASO (no catastrófico)
        peor_retorno = retorno - (volatilidad * 0.5)  # Solo media desviación estándar
        peor_retorno = max(peor_retorno, -0.2)  # Máximo -20% mensual
        peor = monto * ((1 + peor_retorno) ** meses)
        peor = max(peor, monto * factores_minimos[nombre])
        
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
        
        print(f"   ✅ {nombre}: ${monto:,.0f} → ${esperado:,.0f} (x{esperado/monto:.1f})")
    
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