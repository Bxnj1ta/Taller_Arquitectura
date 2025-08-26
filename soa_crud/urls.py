from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from items import views as item_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', item_views.login_view, name='login'),
    path('register/', item_views.register_view, name='register'),
    path('logout/', item_views.logout_view, name='logout'),
    #página frontend
    path('simulador/', item_views.items_list_page, name='simular'),
    #endpoint JSON
    path("api/simular/", item_views.simular, name="api_simular"),
    path('', lambda request: redirect('login')),
    path('', include('items.urls')),  
]
