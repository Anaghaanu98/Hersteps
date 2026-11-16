
from django.urls import path
from orders.views import checkout,place_order,user_orders

app_name = "orders"

urlpatterns = [
    path("checkout/",checkout.checkout_view,name="checkout"),
     path(
        "place-order/",
        place_order.place_order,
        name="place_order"
    ),
    path(
        "order-success/<uuid:order_uuid>/",
        place_order.order_success,
        name="order_success"
    ),
    path("my-orders/", user_orders.order_list, name="order_list"),
]
