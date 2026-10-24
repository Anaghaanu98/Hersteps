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

@admin_required
def user_list_view(request):

    users=User.objects.filter(is_staff=False,is_superuser=False)

    search_query=request.GET.get('q','').strip()
    if search_query:
           users=users.filter(Q(username__icontains=search_query)| Q(email__icontains=search_query)
                         | Q(fullname__icontains=search_query))

           

    status_filter=request.GET.get('status','all')

    if status_filter=='active':
            users=users.filter(is_active=True,is_blocked=False)

    elif status_filter=='blocked':
            users=users.filter(is_blocked=True)
    users=users.order_by('-date_joined','-pk')
    paginator=Paginator(users,10)
    page_obj=paginator.get_page(request.GET.get('page'))

    context={'page_obj':page_obj,
                 'search_query': search_query,
                 'status_filter':status_filter}

    return render(request,'admin_panel/users.html',context)


@admin_required
@require_POST
def toggle_user_status_view(request,user_id):

    customer=get_object_or_404(User,pk=user_id,is_staff=False,is_superuser=False)


    if customer.is_blocked:
        customer.is_blocked=False

        customer.is_active=(customer.is_verified or customer.is_google_user)
        message= f"{customer.username} has been unblocked"
    else:
        customer.is_blocked=True
        customer.is_active=False
        message=f"{customer.username} has been blocked"
    
    customer.save(update_fields=["is_blocked","is_active"])
    messages.success(request,message)
    return redirect('admin_panel:user_list')

@admin_required
@require_POST
def admin_logout_view(request):
    logout(request)
    return redirect('admin_panel:admin_login')