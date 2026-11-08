
from django.urls import path
from . import views

app_name = "wishlist"

urlpatterns = [
    path("",views.wishlist_page, name="page"),
    path("toggle/",views.toggle_wishlist, name="toggle"),
    path("status/",views.wishlist_status, name="status"),
]
