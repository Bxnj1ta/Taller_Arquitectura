from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from django.contrib.auth import authenticate, login, get_user_model, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Simulacion, PrecioActivo
from .serializers import SimulacionSerializer
from django_ratelimit.decorators import ratelimit
from items.services.lambda_service import LambdaService
from .services.market_service import MarketService
from .services.banrep_service import BanrepService
import numpy as np
from datetime import datetime, timedelta

User = get_user_model()


# --- Autenticación ---
def login_view(request):
    if request.method == "POST":
        email = request.POST.get('email')
        password = request.POST.get('password')

        user = authenticate(request, username=email, password=password)
        if user:
            login(request, user)
            return redirect('simular')
        messages.error(request, "Credenciales inválidas")

    return render(request, 'login.html')


def register_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if password != confirm_password:
            messages.error(request, "Las contraseñas no coinciden.")
        elif User.objects.filter(email=email).exists():
            messages.error(request, "El correo ya está registrado.")
        else:
            user = User.objects.create_user(email=email, password=password)
            messages.success(request, "Usuario creado con éxito. Ahora inicia sesión.")
            return redirect("login")

    return render(request, "register.html")


def logout_view(request):
    logout(request)
    return redirect('login')


# --- Simulador ---
@login_required
def items_list_page(request):
    return render(request, 'simulador.html')


@login_required
def detalle_simulacion(request, pk):
    simulacion = get_object_or_404(Simulacion, pk=pk, user=request.user)
    return JsonResponse({"monto": simulacion.monto, "meses": simulacion.meses})


@login_required
def actualizar_precios(request):
    try:
        result = MarketService.actualizar_activos()
        return JsonResponse({"logs": result})
    except Exception as e:
        return JsonResponse({"error": f"Error actualizando precios: {str(e)}"}, status=500)


@login_required
@csrf_exempt
@ratelimit(key='user_or_ip', rate='5/m', block=True)
def simular(request):
    if request.method != "POST":
        return JsonResponse({"error": "Usa POST con monto y meses para simular."}, status=405)

    try:
        data = json.loads(request.body)
        monto = float(data.get("monto", 0))
        meses = int(data.get("meses", 1))

        if not (0 < monto <= 100000000):
            return JsonResponse({"error": "Monto inválido"}, status=400)
        if not (0 < meses <= 360):
            return JsonResponse({"error": "Meses inválidos"}, status=400)

        # --- Activos ---
        activos = {"CDT Bancario": {"retorno": 0, "volatilidad": 0.001}}
        dtf_info = BanrepService.get_cdt_rate()
        activos["CDT Bancario"]["retorno"] = float(dtf_info["tasa"]) / 12

        activos_query = {"S&P 500": "SPY", "Cripto (BTC)": "BTC-USD", "NFTs": "CRYPTOPUNKS"}
        fecha_inicio = datetime.today() - timedelta(days=120)

        # --- Activos con valores por defecto (si no funciona las apis)---
        valores_por_defecto = {
            "S&P 500": {"retorno": 0.007, "volatilidad": 0.045},      # ~8.4% anual, volatilidad moderada
            "Cripto (BTC)": {"retorno": 0.015, "volatilidad": 0.18}, # ~18% anual, alta volatilidad
            "NFTs": {"retorno": 0.02, "volatilidad": 0.25}          # ~24% anual, volatilidad muy alta
        }
        for nombre, ticker in activos_query.items():
            precios = PrecioActivo.objects.filter(simbolo=ticker, fecha__gte=fecha_inicio).order_by("fecha")
            if precios.count() > 2:
                valores = np.array([float(p.cierre) for p in precios])
                rendimientos = np.diff(valores) / valores[:-1]
                activos[nombre] = {
                    "retorno": np.mean(rendimientos), 
                    "volatilidad": np.std(rendimientos)
                }
            else:
                activos[nombre] = valores_por_defecto[nombre]

        # --- Simulación ---
        resultados = {}
        
        # calcular el esperado del CDT 
        cdt_esperado = monto * ((1 + activos["CDT Bancario"]["retorno"]) ** meses)

        for nombre, params in activos.items():
            r, vol = params["retorno"], params["volatilidad"]
            esperado = monto * ((1 + r) ** meses)
            mejor = monto * ((1 + (r + vol)) ** meses)
            peor = monto * ((1 + max(r - vol, -0.99)) ** meses)

            recomendacion = {
                "CDT Bancario": "El CDT es la opción más segura con bajo riesgo, ideal si priorizas estabilidad.",
                "S&P 500": "El S&P 500 ofrece un buen equilibrio entre riesgo y rentabilidad a mediano plazo.",
                "Cripto (BTC)": "Cripto tiene alto potencial de crecimiento, pero con mucha volatilidad.",
                "NFTs": "NFTs muestran la mayor ganancia esperada, pero también un riesgo extremo."
            }.get(nombre, "")

            # calculamos conveniencia relativa frente al CDT en porcentaje
            conveniencia = round((esperado - cdt_esperado) / cdt_esperado * 100, 2)
            
            # calculamos conveniencia relativa frente al CDT en porcentaje
            resultados[nombre] = {
                "esperado": round(esperado,2), 
                "mejor": round(mejor,2), 
                "peor": round(peor,2), 
                "recomendacion": recomendacion, 
                "conveniencia": conveniencia
            }

        simulacion = Simulacion.objects.create(user=request.user, monto=monto, meses=meses)
        serializer = SimulacionSerializer(simulacion)

        return JsonResponse({"simulacion": serializer.data, "resultados": resultados, "dtf_usada": dtf_info})

    except Exception as e:
        return JsonResponse({"error": f"Error procesando datos: {str(e)}"}, status=400)

@login_required
def historial_simulaciones(request):
    simulaciones = Simulacion.objects.filter(user=request.user).order_by("-creado")
    serializer = SimulacionSerializer(simulaciones, many=True)
    return JsonResponse(serializer.data, safe=False)


@login_required
def ejecutar_lambda(request):
    client = LambdaService()
    result = client.invoke("arquitectura_software", {"numero": 42})
    return JsonResponse(result)
