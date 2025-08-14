from django.shortcuts import render, redirect 
from django.http import JsonResponse, HttpResponse, HttpResponseNotFound
from django.views.decorators.csrf import csrf_exempt
import json
from django.contrib.auth import authenticate, login
from django.contrib import messages

from . import services
from .models import Item

def login_view(request):
    if request.method == "POST":
        email = request.POST.get('email')      # aquí usamos 'email' como en el form
        password = request.POST.get('password')

        user = authenticate(request, username=email, password=password)

        if user is not None:
            login(request, user)

            # Si es admin, llevar a la lista
            if user.is_superuser:
                return render(request, 'list.html')  # muestra list.html directamente

            # Si no es admin, puedes redirigir a otra página
            return redirect('login.html')  

        else:
            messages.error(request, "Credenciales inválidas")
            return render(request, 'login.html')

    return render(request, 'login.html')


def items_list_page(request):
    # la página frontend cargará datos con fetch desde la API
    return render(request, 'list.html')


def items_form_page(request):
    return render(request, 'form.html')


# API endpoints (JSON)

def api_list_items(request):
    items = services.list_items()
    data = [
        {'id': it.id, 'name': it.name, 'description': it.description, 'created_at': it.created_at.isoformat()}
        for it in items
    ]
    return JsonResponse({'items': data})


@csrf_exempt
def api_create_item(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        name = data.get('name')
        description = data.get('description')

        item = Item.objects.create(name=name, description=description)
        return JsonResponse({
            'id': item.id,
            'name': item.name,
            'description': item.description
        })

    return JsonResponse({'error': 'Método no permitido'}, status=405)

@csrf_exempt
def api_get_update_delete_item(request, item_id):
    # GET: obtener, PUT: actualizar, DELETE: borrar
    if request.method == 'GET':
        item = services.get_item(item_id)
        if not item:
            return HttpResponseNotFound()
        return JsonResponse({'id': item.id, 'name': item.name, 'description': item.description})

    if request.method == 'PUT':
        payload = json.loads(request.body.decode('utf-8'))
        name = payload.get('name')
        description = payload.get('description')
        item = services.update_item(item_id, name=name, description=description)
        if not item:
            return HttpResponseNotFound()
        return JsonResponse({'id': item.id, 'name': item.name, 'description': item.description})

    if request.method == 'DELETE':
        ok = services.delete_item(item_id)
        if not ok:
            return HttpResponseNotFound()
        return JsonResponse({'deleted': True})

    return HttpResponse(status=405)