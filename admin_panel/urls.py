from django.urls import path
from .views import admin_views,categories_views,products_views,banner_views,orders_views,return_management,inventory_views
app_name='admin_panel'
urlpatterns = [
    path('',admin_views.admin_login_view,name='admin_login'),
    path('dashboard/',admin_views.admin_dashboard_view,name='admin_dashboard'),
    path('user-list/',admin_views.user_list_view,name='user_list'),
    path('users/<int:user_id>/toggle-status/',admin_views.toggle_user_status_view,name='toggle_user_status'),

    path('categories/',categories_views.category_list,name='category_list'),
    path('categories/add/',categories_views.category_add,name='category_add'),
    path("categories/<int:pk>/edit/",categories_views.category_edit,name='category_edit'),
    path('categories/<int:pk>/toggle-status/',categories_views.category_toggle_status,name='category_toggle_status'),

    path("banners/", banner_views.banner_list, name="banner_list"),
    path("banners/add/", banner_views.banner_add, name="banner_add"),
    path("banners/<int:banner_id>/edit/", banner_views.banner_edit, name="banner_edit"),
    path("banners/<int:banner_id>/toggle-status/", banner_views.banner_toggle_status, name="banner_toggle_status"),
    
    path('products/',products_views.products_list,name='products_list'),
    path( "products/add/",products_views.add_product,name="add_product"),
    path("products/<int:product_id>/variants/",products_views.add_product_variants,name="add_product_variants"),
    path("products/edit/<uuid:product_uuid>/",products_views.edit_product,name="edit_product"),
    path("products/toggle-status/<uuid:product_uuid>/",products_views.toggle_product_status,name="toggle_product_status"),
    path("products/<str:product_uuid>/variants/edit/",products_views.edit_product_variants,name="edit_product_variants",),

    

    path("orders/",orders_views.order_list,name="order_list"),

path(
    "orders/<uuid:order_uuid>/",
    orders_views.admin_order_detail,
    name="order_detail"
),

path(
    "orders/<uuid:order_uuid>/update-status/",
    orders_views.admin_update_order_status,
    name="update_order_status"
),

path(
    "orders/<uuid:order_uuid>/cancel/",
    orders_views.admin_cancel_order,
    name="cancel_order"
),
path(
    "return-requests/",
    return_management.return_request_list,
    name="return_request_list"
),

path(
    "return-requests/<int:request_id>/review/",
    return_management.admin_review_return,
    name="review_return"
),

path(
    "orders/<uuid:order_uuid>/items/<int:item_id>/cancel/",
    orders_views.admin_cancel_order_item,
    name="admin_cancel_order_item"
),


    path("orders/", orders_views.order_list, name="order_list"),
    path(
    "inventory/",
    inventory_views.inventory_dashboard,
    name="inventory_dashboard"
),
path(
    "inventory/categories/",
    inventory_views.inventory_categories,
    name="inventory_categories"
),

path(
    "inventory/products/",
    inventory_views.inventory_products,
    name="inventory_products"
),
    path('logout/',admin_views.admin_logout_view,name='admin_logout')

]

