from django.urls import path
from .import views

app_name = 'my_accounts'

urlpatterns = [
    path('', views.my_account_view, name='my_account'),
    path('profile/',views.profile_view,name='profile'),
    path('change-password/', views.change_password_view, name='change_password'),
    path('logout/', views.logout_view, name='logout'),
    path('address-list/',views.address_list_view,name='address_list'),
    path('add-address'/views.add_address_view, name='add_address'),
    path('address/<int:address_id>/edit/',views.edit_address_view,name='edit_address')
]