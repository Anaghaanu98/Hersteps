from django.urls import path
from . import views
app_name='cart'
urlpatterns = [
    path("", views.cart_page, name="page"),
    path(
        "add/",
        views.add_to_cart,
        name="add_to_cart"
    ),
    path("count/", views.cart_count, name="cart_count"),
    path("update-quantity/", views.update_cart_quantity, name="update_quantity"),
    path("change-size/", views.change_cart_size, name="change_size"),
    path("remove/", views.remove_cart_item, name="remove_item"),
    path(
    "move-to-wishlist/",
    views.move_to_wishlist,
    name="move_to_wishlist"
),
]