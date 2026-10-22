from django.contrib import messages
from django.shortcuts import render,redirect,get_object_or_404
from allauth.socialaccount.models import SocialAccount
from my_accounts.forms import ProfileUpdateForm
from django.contrib.auth import logout
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from .forms import AddressForm
from .models import Address
def my_account_view(request):
    return render(request, "my_accounts/my_account.html")

def profile_view(request):


    user=request.user

    is_google_user=SocialAccount.objects.filter(user=user, provider='google').exists()

    if request.method == "POST":
        form=ProfileUpdateForm(request.POST, instance=user)

        if form.is_valid():
          form.save()

          messages.success(request, "Profile updated successfully.")
          return redirect("my_accounts:profile")

        messages.error(request, "Please correct the errors below.")
    else:
        form=ProfileUpdateForm(instance=user)
    context ={"user":user, "is_google_user":is_google_user, "form":form}
    return render(request, "my_accounts/profile.html")


@login_required
def change_password_view(request):
    if request.method == "POST":
        current_password = request.POST.get("current_password", "")
        new_password = request.POST.get("new_password", "")
        confirm_password = request.POST.get("confirm_password", "")

        # 1. Validate the current password
        if not request.user.check_password(current_password):
            messages.error(request, "Your current password is incorrect.")

        # 2. Check whether the new password and confirmation match
        elif new_password != confirm_password:
            messages.error(request, "New password and confirm password do not match.")

        # 3. Prevent reusing the current password
        elif request.user.check_password(new_password):
            messages.error(request, "Your new password must be different from your current password.")

        else:
            # 4. Validate the new password using Django's validators
            try:
                validate_password(new_password, user=request.user)

            except ValidationError as error:
                for message in error.messages:
                    messages.error(request, message)

            else:
                # 5. Set and save the new password securely
                request.user.set_password(new_password)
                request.user.save()

                # 6. Keep the user logged in after changing the password
                update_session_auth_hash(request, request.user)

                messages.success(request, "Your password has been changed successfully.")
                return redirect("my_accounts:profile")

    return render(request, "my_accounts/change_password.html")

@login_required
def address_list_view(request):
    addresses= Address.objects.filter(user=request.user)
    return render(request, 'my_accounts/addresses.html',{"addresses":addresses})


@login_required
def add_address_view(request):
    if request.method=='POST':
        form=AddressForm(request.POST)

        if form.is_valid():
            address=form.save(commit=False)
            address.user=request.user
            address.save()

            messages.success(request,'Address saved successfully')
            return redirect('address_list')
    else:
        form=AddressForm()

    return render(request,'my_accounts/add_address.html',{'form':form,'page_title':'Add new Address'})

@login_required
def edit_address_view(request,address_id):
    address= get_object_or_404(Address,id=address_id,user=request.user)

    if request.method=='POST':
        form=AddressForm(request.POST,instance=address)

        if form.is_valid():
            form.save()

            messages.success(request,'Address updated successfully')
            return redirect('address_list')
        else:
            form= AddressForm()
def logout_view(request):

    if request.method == "POST":

      logout(request)
      messages.success(request, "You have been logged out.")
      return redirect("home")
    return render(request,'my_accounts/logout.html')