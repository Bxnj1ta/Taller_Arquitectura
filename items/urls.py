from django.urls import path
from . import views

urlpatterns = [
    path("api/simular/", views.simular, name="api_simular"),    #endpoint JSON
    path("api/simulaciones/", views.historial_simulaciones, name="api_simulaciones"),
    path("api/simulaciones/<int:simulacion_id>/", views.eliminar_simulacion, name="api_eliminar_simulacion"),
    path("api/simulaciones/todas/", views.eliminar_todas_simulaciones, name="api_eliminar_todas_simulaciones"),
    path("api/inversiones/", views.historial_inversiones, name="api_inversiones"),
    path("api/portafolio/", views.portafolio_api, name="api_portafolio"),
    path("api/analytics/", views.analytics_api, name="api_analytics"),
    path('top-up/', views.top_up_view, name='top_up'),
    path('wallet-invest/', views.wallet_invest_view, name='wallet_invest'),
    path('withdraw/', views.withdraw_view, name='withdraw'),
]