from django.urls import path
from .import views
urlpatterns = [
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('verify-email/', views.verify_email_view, name='verify_email'),
    path('home/',views.home_view,name='home'),
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('reset-otp/', views.verify_reset_otp_view, name='verify_reset_otp'),
    path('reset-password/', views.reset_password_view, name='reset_password'),
]

