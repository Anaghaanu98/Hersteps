from django.urls import path
from .views import admin_views,categories_views
app_name='admin_panel'
urlpatterns = [
    path('',admin_views.admin_login_view,name='admin_login'),
    path('dashboard/',admin_views.admin_dashboard_view,name='admin_dashboard'),
    path('user-list/',admin_views.user_list_view,name='user_list'),
    
    path('categories/',categories_views.category_list,name='category_list'),
    path('categories/add/',categories_views.category_add,name='category_add'),
    path('categories/edit/',categories_views.category_edit,name='category_edit'),
    path('categories/<int:pk>/toggle-status/',categories_views.category_toggle_status,name='category_toggle_status'),
    path('users/<int:user_id>/toggle-status/',admin_views.toggle_user_status_view,name='toggle_user_status'),
    path('logout/',admin_views.admin_logout_view,name='admin_logout')
]

