from django.urls import path
from . import views

urlpatterns = [
    path("api/simular/", views.simular, name="api_simular"),    #endpoint JSON
    path("api/simulaciones/", views.historial_simulaciones, name="api_simulaciones"),
    path('admin-panel/', views.admin_panel, name='admin_panel'),
]