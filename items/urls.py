from django.urls import path
from . import views

urlpatterns = [
    path("api/simular/", views.simular, name="api_simular"),    #endpoint JSON
    path("api/simulaciones/", views.historial_simulaciones, name="api_simulaciones"),

    # CRUD seguro para Item
    path("api/items/", views.listar_items, name="api_items_listar"),
    path("api/items/create/", views.crear_item, name="api_items_crear"),
    path("api/items/<int:pk>/update/", views.actualizar_item, name="api_items_actualizar"),
    path("api/items/<int:pk>/delete/", views.eliminar_item, name="api_items_eliminar"),
]