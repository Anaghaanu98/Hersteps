
from django.urls import path
from orders.views import checkout,place_order,user_orders,invoice

app_name = "orders"

urlpatterns = [
    path("checkout/",checkout.checkout_view,name="checkout"),
    path("place-order/",place_order.place_order,name="place_order"),
    path("order-success/<uuid:order_uuid>/",place_order.order_success,name="order_success"),
    path("my-orders/", user_orders.order_list, name="order_list"),
    path("my-orders/<uuid:order_uuid>/",user_orders.order_detail,name="order_detail"),

    path("my-orders/<uuid:order_uuid>/cancel/",user_orders.cancel_order,name="cancel_order"),

    path("my-orders/<uuid:order_uuid>/items/<int:item_id>/cancel/",user_orders.cancel_order_item,name="cancel_order_item"),
    path("my-orders/<uuid:order_uuid>/items/<int:item_id>/return/",user_orders.request_return,name="request_return"),
    path("my-orders/<uuid:order_uuid>/invoice/",invoice.download_invoice,name="download_invoice"),

    path("my-orders/<uuid:order_id>/purchase-order/",invoice.download_purchase_order,name="download_purchase_order"),

]

