from django.urls import path
from accounts.views import views,home_views
urlpatterns = [
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('verify-email/', views.verify_email_view, name='verify_email'),
    path('',home_views.home_view,name='home'),
    path('shop/',home_views.shop_view,name='shop'),
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('reset-otp/', views.verify_reset_otp_view, name='verify_reset_otp'),
    path('reset-password/', views.reset_password_view, name='reset_password'),
]

