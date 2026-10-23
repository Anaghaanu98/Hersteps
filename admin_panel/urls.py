from django.urls import path
from .import views
app_name='admin_panel'
urlpatterns = [
    path('login/',views.admin_login_view,name='admin_login'),
    path('dashboard/',views.admin_dashboard_view,name='admin_dashboard'),
    path('user-list/',views.user_list_view,name='user_list'),
    path('users/<int:user_id>/toggle-status/',views.toggle_user_status_view,name='toggle_user_status'),
    path('logout/',views.admin_logout_view,name='admin_logout')
]
