from django.urls import path
from . import views

urlpatterns = [
    path("api/simular/", views.simular, name="api_simular"),    #endpoint JSON
    path("api/simulaciones/", views.historial_simulaciones, name="api_simulaciones"),
    path('top-up/', views.top_up_view, name='top_up'),
    path('wallet-invest/', views.wallet_invest_view, name='wallet_invest'),
]