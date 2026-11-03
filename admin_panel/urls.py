from django.urls import path
from .views import admin_views,categories_views,products_views
app_name='admin_panel'
urlpatterns = [
    path('',admin_views.admin_login_view,name='admin_login'),
    path('dashboard/',admin_views.admin_dashboard_view,name='admin_dashboard'),
    path('user-list/',admin_views.user_list_view,name='user_list'),
    
    path('categories/',categories_views.category_list,name='category_list'),
    path('categories/add/',categories_views.category_add,name='category_add'),
    path("categories/<int:pk>/edit/",categories_views.category_edit,name='category_edit'),
    path('categories/<int:pk>/toggle-status/',categories_views.category_toggle_status,name='category_toggle_status'),
     
    path('products/',products_views.products_list,name='products_list'),
    path( "products/add/",products_views.add_product,name="add_product"),
    path("products/<int:product_id>/variants/",products_views.add_product_variants,name="add_product_variants"),
    path("products/edit/<uuid:product_uuid>/",products_views.edit_product,name="edit_product"),
    path("products/toggle-status/<uuid:product_uuid>/",products_views.toggle_product_status,name="toggle_product_status"),
    path("products/<str:product_uuid>/variants/edit/",products_views.edit_product_variants,name="edit_product_variants",),
    path('users/<int:user_id>/toggle-status/',admin_views.toggle_user_status_view,name='toggle_user_status'),
    path('logout/',admin_views.admin_logout_view,name='admin_logout')
]

