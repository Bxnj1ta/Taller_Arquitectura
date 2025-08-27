from django.shortcuts import render, redirect 
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from django.contrib.auth import authenticate, login, get_user_model, logout
from django.contrib import messages

def login_view(request):
    if request.method == "POST":
        email = request.POST.get('email')      # aquí usamos 'email' como en el form
        password = request.POST.get('password')

        user = authenticate(request, username=email, password=password)

        if user is not None:
            login(request, user)
            return redirect('simular')  

        else:
            messages.error(request, "Credenciales inválidas")
            return render(request, 'login.html')

    return render(request, 'login.html')

User = get_user_model()

def register_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if password != confirm_password:
            messages.error(request, "Las contraseñas no coinciden.")
            return render(request, "register.html")

        if User.objects.filter(email=email).exists():
            messages.error(request, "El correo ya está registrado.")
            return render(request, "register.html")

        user = User.objects.create_user(email=email, password=password)
        user.save()

        messages.success(request, "Usuario creado con éxito. Ahora inicia sesión.")
        return redirect("login")

    return render(request, "register.html")

def logout_view(request):
    logout(request)
    return redirect('login')

def items_list_page(request):
    # la página frontend cargará datos con fetch desde la API
    return render(request, 'simulador.html')

@csrf_exempt
def simular(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            monto = float(data.get("monto", 0))
            meses = int(data.get("meses", 1))

            activos = {
                "CDT Bancario": {"retorno": 0.006, "volatilidad": 0.001},
                "S&P 500": {"retorno": 0.01, "volatilidad": 0.03},
                "Cripto (BTC)": {"retorno": 0.02, "volatilidad": 0.08},
                "NFTs": {"retorno": 0.03, "volatilidad": 0.15},
            }

            resultados = {}

            for nombre, params in activos.items():
                r = params["retorno"]
                vol = params["volatilidad"]

                esperado = monto * ((1 + r) ** meses)
                mejor = monto * ((1 + (r + vol)) ** meses)
                peor = monto * ((1 + max(r - vol, -0.99)) ** meses)

                # --- Recomendación individual ---
                if nombre == "CDT Bancario":
                    recomendacion = "El CDT es la opción más segura con bajo riesgo, ideal si priorizas estabilidad."
                elif nombre == "S&P 500":
                    recomendacion = "El S&P 500 ofrece un buen equilibrio entre riesgo y rentabilidad a mediano plazo."
                elif nombre == "Cripto (BTC)":
                    recomendacion = "Cripto tiene alto potencial de crecimiento, pero con mucha volatilidad. Úsalo solo si toleras riesgo alto."
                else:
                    recomendacion = "NFTs muestran la mayor ganancia esperada, pero también un riesgo extremo. Muy especulativo."

                resultados[nombre] = {
                    "esperado": round(esperado, 2),
                    "mejor": round(mejor, 2),
                    "peor": round(peor, 2),
                    "recomendacion": recomendacion
                }

            return JsonResponse({
                "monto": monto,
                "meses": meses,
                "resultados": resultados
            })

        except Exception as e:
            return JsonResponse({"error": f"Error procesando datos: {str(e)}"}, status=400)

    return JsonResponse({"error": "Usa POST con monto y meses para simular."}, status=405)
