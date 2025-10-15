from django.urls import reverse
# --- Simulador ---
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse, HttpResponseForbidden
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from django.contrib.auth import authenticate, login, get_user_model, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Simulacion, PrecioActivo, Item
from .serializers import SimulacionSerializer, ItemSerializer
from . import kernel

# --- CRUD seguro para Item ---
from django.views.decorators.http import require_http_methods

@login_required
@require_http_methods(["POST"])
@csrf_exempt
def crear_item(request):
    try:
        data = json.loads(request.body)
        serializer = ItemSerializer(data=data)
        if not serializer.is_valid():
            return JsonResponse({"error": serializer.errors}, status=400)
        item = serializer.save()
        return JsonResponse(ItemSerializer(item).data, status=201)
    except Exception as e:
        return JsonResponse({"error": f"Error creando item: {str(e)}"}, status=400)


@login_required
@require_http_methods(["GET"])
def listar_items(request):
    items = Item.objects.all().order_by("-created_at")
    serializer = ItemSerializer(items, many=True)
    return JsonResponse(serializer.data, safe=False)


@login_required
@require_http_methods(["PUT"])
@csrf_exempt
def actualizar_item(request, pk):
    try:
        item = get_object_or_404(Item, pk=pk)
        data = json.loads(request.body)
        serializer = ItemSerializer(item, data=data, partial=True)
        if not serializer.is_valid():
            return JsonResponse({"error": serializer.errors}, status=400)
        item = serializer.save()
        return JsonResponse(ItemSerializer(item).data)
    except Exception as e:
        return JsonResponse({"error": f"Error actualizando item: {str(e)}"}, status=400)


@login_required
@require_http_methods(["DELETE"])
@csrf_exempt
def eliminar_item(request, pk):
    try:
        item = get_object_or_404(Item, pk=pk)
        item.delete()
        return JsonResponse({"message": "Item eliminado"})
    except Exception as e:
        return JsonResponse({"error": f"Error eliminando item: {str(e)}"}, status=400)
from django_ratelimit.decorators import ratelimit
from items.services.lambda_service import LambdaService
from .services.market_service import MarketService
from .services.banrep_service import BanrepService
import numpy as np
from datetime import datetime, timedelta
import logging

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

# Nueva vista: panel administrativo (crear / borrar cuentas)
@login_required
def admin_panel(request):
    # Permitir sólo staff/superuser
    if not (request.user.is_staff or request.user.is_superuser):
        return HttpResponseForbidden("Acceso denegado")

    User = get_user_model()

    # Manejo de acciones por POST: crear o borrar
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "create":
            # Campos esperados: email (o username), password, is_staff(optional)
            email = request.POST.get("email")
            password = request.POST.get("password")
            is_staff = request.POST.get("is_staff") == "on"

            if not email or not password:
                messages.error(request, "Email y contraseña son obligatorios para crear un usuario.")
            else:
                # crear usuario respetando USERNAME_FIELD
                username_field = getattr(User, "USERNAME_FIELD", "username")
                create_kwargs = {username_field: email}

                # Si el modelo User usa un campo 'email' aparte y create_user espera (email, password):
                try:
                    # intentar create_user con keyword args + password
                    user = User.objects.create_user(**create_kwargs, password=password)
                except TypeError:
                    # fallback genérico: usar create() y set_password()
                    user = User(**create_kwargs)
                    user.set_password(password)
                    user.save()

                # marcar staff si corresponde
                if hasattr(user, "is_staff"):
                    user.is_staff = is_staff
                    user.save()

                messages.success(request, f"Usuario '{email}' creado correctamente.")

        elif action == "delete":
            user_id = request.POST.get("user_id")
            if not user_id:
                messages.error(request, "No se indicó el usuario a eliminar.")
            else:
                try:
                    to_delete = User.objects.get(pk=int(user_id))
                    # evitar que el admin se borre a sí mismo accidentalmente
                    if to_delete.pk == request.user.pk:
                        messages.error(request, "No puede eliminar su propia cuenta desde aquí.")
                    else:
                        to_delete.delete()
                        messages.success(request, "Usuario eliminado correctamente.")
                except User.DoesNotExist:
                    messages.error(request, "Usuario no encontrado.")

    # Listado de usuarios para mostrar en la UI
    users = get_user_model().objects.all().order_by("pk")
    return render(request, "admin_panel.html", {"users": users})



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
    # Identificar tipo de usuario
    user_type = "Premium" if getattr(request.user, "is_premium", False) else "Free"
    pago_url = reverse('pago_premium') if user_type == "Free" else None
    return render(request, 'simulador.html', {"user_type": user_type, "pago_url": pago_url})
# --- Pago simulado para ser premium ---
from django.views.decorators.http import require_http_methods

@login_required
@require_http_methods(["GET", "POST"])
def pago_premium(request):
    pago_exitoso = False
    if request.method == "POST":
        # Simular pago: convertir usuario en premium
        user = request.user
        user.is_premium = True
        user.save()
        pago_exitoso = True
    return render(request, "pago_premium.html", {"pago_exitoso": pago_exitoso})
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
def actualizar_precios(request):
    """Actualiza precios de todos los activos."""
    try:
        result = MarketService.actualizar_activos()
        logger.info("Precios actualizados manualmente")
        return JsonResponse({"logs": result, "success": True})
    except Exception as e:
        logger.error(f"Error actualizando precios: {e}")
        return JsonResponse({"error": f"Error actualizando precios: {str(e)}"}, status=500)


@login_required
@csrf_exempt
@ratelimit(key='user_or_ip', rate='5/m', block=True)
@require_http_methods(["POST"])
def simular(request):
    """
    Simula inversión en 4 activos basado en datos históricos y tasas reales.
    Retorna escenarios: esperado, mejor caso y peor caso.
    
    Request body:
    {
        "monto": float,  # Monto a invertir
        "meses": int     # Meses de inversión
    }
    """
    try:
        data = json.loads(request.body)
        # Sanitización y validación usando el serializer
        serializer = SimulacionSerializer(data={
            "monto": data.get("monto"),
            "meses": data.get("meses")
        })
        if not serializer.is_valid():
            return JsonResponse({"error": serializer.errors}, status=400)
        monto = serializer.validated_data["monto"]
        meses = serializer.validated_data["meses"]
        monto = float(data.get("monto", 0))
        meses = int(data.get("meses", 1))

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

        # Obtener tasas y activos
        dtf_info = BanrepService.get_cdt_rate()
        activos = _obtener_activos(dtf_info)

        # Ejecutar simulación
        resultados = _ejecutar_simulacion(monto, meses, activos)

        # --- Activos con valores por defecto (si no funciona las apis)---
        valores_por_defecto = {
            "S&P 500": {"retorno": 0.007, "volatilidad": 0.015},     # 1.5% mensual de volatilidad
            "Cripto (BTC)": {"retorno": 0.015, "volatilidad": 0.06}, # 6% mensual de volatilidad
            "NFTs": {"retorno": 0.02, "volatilidad": 0.08}          # 8% mensual de volatilidad
        # Guardar en BD
        simulacion = Simulacion.objects.create(
            user=request.user,
            monto=monto,
            meses=meses
        )
        serializer = SimulacionSerializer(simulacion)

        logger.info(f"Simulación creada para usuario {request.user.email}: ${monto} x {meses} meses")

        return JsonResponse({
            "simulacion": serializer.data,
            "resultados": resultados,
            "dtf_usada": dtf_info,
            "fecha_simulacion": datetime.now().isoformat()
        })

    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON inválido"}, status=400)
    except ValueError as e:
        return JsonResponse({"error": f"Error en valores: {str(e)}"}, status=400)
    except Exception as e:
        logger.error(f"Error en simulación para usuario {request.user.email}: {e}")
        return JsonResponse({"error": "Error procesando datos"}, status=500)


def _obtener_activos(dtf_info):
    """
    Obtiene retorno y volatilidad de activos desde BD o valores por defecto.
    
    Returns:
        dict: Diccionario con activos y sus parámetros de retorno y volatilidad
    """
    fecha_inicio = datetime.today() - timedelta(days=120)
    
    valores_por_defecto = {
        "CDT Bancario": {"retorno": 0, "volatilidad": 0.001},
        "S&P 500": {"retorno": 0.007, "volatilidad": 0.015},
        "Cripto (BTC)": {"retorno": 0.015, "volatilidad": 0.06},
        "NFTs": {"retorno": 0.02, "volatilidad": 0.08}
    }
    
    activos = {
        "CDT Bancario": {
            "retorno": float(dtf_info["tasa"]) / 12,
            "volatilidad": 0.001
        }
    }
    
    # Mapeo de nombres a símbolos en BD
    activos_query = {
        "S&P 500": "SPY",
        "Cripto (BTC)": "BTC",  # Cambiar de "BTC-USD" a "BTC"
        "NFTs": "CRYPTOPUNKS"
    }
    
    for nombre, ticker in activos_query.items():
        try:
            precios = PrecioActivo.objects.filter(
                simbolo=ticker,
                fecha__gte=fecha_inicio
            ).order_by("fecha").values_list("cierre", flat=True)
            
            if len(precios) > 2:
                valores = np.array([float(p) for p in precios])
                # Evitar división por cero
                rendimientos = np.diff(valores) / np.where(
                    valores[:-1] != 0,
                    valores[:-1],
                    1
                )
                
                activos[nombre] = {
                    "retorno": float(np.mean(rendimientos)),
                    "volatilidad": float(np.std(rendimientos))
                }
            else:
                activos[nombre] = valores_por_defecto[nombre]
                logger.warning(
                    f"Insuficientes datos para {nombre}, usando valores por defecto"
                )
        except Exception as e:
            logger.error(f"Error obteniendo datos de {nombre}: {e}")
            activos[nombre] = valores_por_defecto[nombre]
    
    return activos


def _ejecutar_simulacion(monto, meses, activos):
    """
    Calcula escenarios de inversión para cada activo.
    
    Args:
        monto: Monto inicial a invertir
        meses: Número de meses
        activos: Diccionario con parámetros de cada activo
    
    Returns:
        dict: Diccionario con resultados por activo
    """
    resultados = {}
    
    # Baseline: CDT Bancario (inversión más segura)
    cdt_retorno = activos["CDT Bancario"]["retorno"]
    cdt_esperado = monto * ((1 + cdt_retorno) ** meses)
    
    recomendaciones = {
        "CDT Bancario": "El CDT es la opción más segura con bajo riesgo, ideal si priorizas estabilidad.",
        "S&P 500": "El S&P 500 ofrece un buen equilibrio entre riesgo y rentabilidad a mediano plazo.",
        "Cripto (BTC)": "Bitcoin tiene alto potencial de crecimiento, pero con volatilidad extrema.",
        "NFTs": "NFTs muestran la mayor ganancia esperada, pero riesgo extremo de pérdida."
    }
    
    for nombre, params in activos.items():
        retorno = params["retorno"]
        volatilidad = params["volatilidad"]
        
        # Escenario esperado (retorno promedio)
        esperado = monto * ((1 + retorno) ** meses)
        
        # Mejor caso (retorno + volatilidad)
        mejor_retorno = retorno + volatilidad
        mejor = monto * ((1 + mejor_retorno) ** meses)
        
        # Peor caso (retorno - volatilidad, mínimo -99%)
        peor_retorno = max(retorno - volatilidad, -0.99)
        peor = monto * ((1 + peor_retorno) ** meses)
        
        # Conveniencia relativa al CDT (en porcentaje)
        if cdt_esperado > 0:
            conveniencia = round((esperado - cdt_esperado) / cdt_esperado * 100, 2)
            
            resultados[nombre] = {
                "esperado": round(esperado,2), 
                "mejor": round(mejor,2), 
                "peor": round(peor,2), 
                "recomendacion": recomendacion, 
                "conveniencia": conveniencia
            }
        else:
            conveniencia = 0
        
        # Ganancia/Pérdida
        ganancia = esperado - monto
        ganancia_porcentaje = round((ganancia / monto * 100), 2) if monto > 0 else 0
        
        resultados[nombre] = {
            "esperado": round(esperado, 2),
            "mejor": round(mejor, 2),
            "peor": round(peor, 2),
            "ganancia": round(ganancia, 2),
            "ganancia_porcentaje": ganancia_porcentaje,
            "recomendacion": recomendaciones.get(nombre, ""),
            "conveniencia_vs_cdt": conveniencia,
            "retorno_mensual": round(retorno * 100, 4),
            "volatilidad_mensual": round(volatilidad * 100, 4)
        }
    
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
def ejecutar_lambda(request):
    client = LambdaService()
    result = client.invoke("arquitectura_software", {"numero": 42})
    return JsonResponse(result)


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
