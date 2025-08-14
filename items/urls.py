from django.urls import path
from . import views

urlpatterns = [
    # frontend
    path('list/', views.items_list_page, name='list'),
    path('form/', views.items_form_page, name='form'),

    # api
    path('api/items/', views.api_list_items, name='api_list_items'),
    path('api/items/create/', views.api_create_item, name='api_create_item'),
    path('api/items/<int:item_id>/', views.api_get_update_delete_item, name='api_get_update_delete_item'),
]