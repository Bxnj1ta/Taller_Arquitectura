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
            tasa_interes = 0.05

            cuota = (monto * (1 + tasa_interes)) / meses

            return JsonResponse({
                "monto": monto,
                "meses": meses,
                "tasa_interes": tasa_interes,
                "cuota_mensual": round(cuota, 2)
            })
        except Exception as e:
            return JsonResponse({"error": f"Error procesando datos: {str(e)}"}, status=400)

    # 🔴 IMPORTANTE: si llega por GET, que devuelva JSON, no HTML
    return JsonResponse({"error": "Usa POST con monto y meses para simular."}, status=405)