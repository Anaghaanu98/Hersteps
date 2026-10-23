from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import user_passes_test
from django.core.paginator import Paginator
from django.db.models import Q
from django.views.decorators.http import require_POST

User=get_user_model()

def admin_login_view(request):
    
    if (request.user.is_authenticated and request.user.is_active and request.user.is_staff and request.user.is_superuser):
        return redirect('admin_panel:admin_dashboard')

    if request.method=='POST':
        username=request.POST.get('username','').strip()
        password=request.POST.get('password','')

        user=authenticate(request,username=username,password=password)
        if( user is not None and user.is_active and user.is_staff and user.is_superuser):
            login(request,user)
            return redirect('admin_panel:admin_dashboard')

        messages.error(request,'Invalid credentials')
    return render(request,'admin_panel/login.html')
def admin_required(view_func):
    return user_passes_test(
        lambda user: (
            user.is_authenticated
            and user.is_active
            and user.is_staff
            and user.is_superuser
        ),
        login_url='admin_panel:admin_login'
    )(view_func)

@admin_required
def admin_dashboard_view(request):
    return render(request,'admin_panel/dashboard.html')
