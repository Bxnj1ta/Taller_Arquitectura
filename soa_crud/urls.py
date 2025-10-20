from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from items import views as item_views

urlpatterns = [
    path('', item_views.home_view, name='home'),
    path('superpanel/', admin.site.urls),   #Cambio de url de admin (Más seguro/API8)
    path('login/', item_views.login_view, name='login'),
    path('register/', item_views.register_view, name='register'),
    path('logout/', item_views.logout_view, name='logout'),
    path('pago-premium/', item_views.pago_premium, name='pago_premium'),
    #acceso al panel del admin
    path('admin-panel/', item_views.admin_panel, name='admin_panel'),
    #página frontend
    path('simulador/', item_views.items_list_page, name='simular'),
    path('', lambda request: redirect('home')),  # Redirige la raíz a la página de inicio
    #API endpoints
    path('', include('items.urls')),  
]
