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
from .models import EmailChangeVerification
import secrets
from django.contrib.auth.hashers import make_password,check_password
from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model
import logging
from django import forms
logger = logging.getLogger(__name__)
User = get_user_model()

OTP_EXPIRY_MINUTES = 2
MAX_OTP_ATTEMPTS = 5



@login_required
def my_account_view(request):
    return render(request, "my_accounts/my_account.html")


@login_required
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
    return render(request, "my_accounts/profile.html",context)

@login_required
@require_POST
def start_email_change_view(request):
    user = request.user
    is_google_user = SocialAccount.objects.filter(
        user=user,
        provider="google"
    ).exists()

    if is_google_user:
        messages.error(
            request,
            "Your email is managed through your Google account."
        )
        return redirect("my_accounts:profile")

    new_email = request.POST.get("new_email", "").strip().lower()

    if not new_email:
        messages.error(request, "Please enter your new email address.")
        return redirect("my_accounts:profile")

    if new_email == user.email.lower():
        messages.error(
            request,
            "Your new email must be different from your current email."
        )
        return redirect("my_accounts:profile")

    
    if User.objects.filter(email__iexact=new_email).exclude(
        pk=user.pk
    ).exists():
        messages.error(
            request,
            "This email address is already registered."
        )
        return redirect("my_accounts:profile")


    try:
        new_email = forms.EmailField().clean(new_email)
    except forms.ValidationError:
        messages.error(request, "Please enter a valid email address.")
        return redirect("my_accounts:profile")

    otp = f"{secrets.randbelow(1_000_000):06d}"

    EmailChangeVerification.objects.update_or_create(
        user=user,
        defaults={
            "new_email": new_email,
            "otp_hash": make_password(otp),
            "expires_at": timezone.now() + timedelta(minutes=5),
            "attempts": 0,
        }
    )

    try:
        send_mail(
            subject="Verify your new HerSteps email",
            message=(
                f"Hi {user.fullname or user.username},\n\n"
                f"Your OTP to change your HerSteps email is: {otp}\n\n"
                "This OTP is valid for 5 minutes.\n"
                "If you did not request this change, please ignore this email."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[new_email],
            fail_silently=False,
        )
    except Exception:
        EmailChangeVerification.objects.filter(user=user).delete()
        messages.error(
            request,
            "We couldn't send the verification email. Please try again."
        )
        return redirect("my_accounts:profile")

    messages.success(
        request,
        "An OTP has been sent to your new email address."
    )
    return redirect("my_accounts:verify_email_change")


@login_required
def verify_email_change_view(request):
    user = request.user

    is_google_user = SocialAccount.objects.filter(
        user=user,
        provider="google"
    ).exists()

    if is_google_user:
        messages.error(
            request,
            "Your email is managed through your Google account."
        )
        return redirect("my_accounts:profile")

    verification = EmailChangeVerification.objects.filter(
        user=user
    ).first()

    if verification is None:
        messages.error(
            request,
            "No pending email change was found. Please try again."
        )
        return redirect("my_accounts:profile")

    if request.method == "POST":
          action = request.POST.get("action", "verify")
          now = timezone.now()
          if action == "resend":
              

              if now < verification.expires_at:
                messages.error(
                  request,
                 "You can request a new OTP after the current one expires."
                )
                return redirect("my_accounts:verify_email_change")

              otp = f"{secrets.randbelow(1_000_000):06d}"

              verification.otp_hash = make_password(otp)
              verification.expires_at = now + timedelta(minutes=OTP_EXPIRY_MINUTES)
              verification.attempts = 0
              verification.save(
                  update_fields=["otp_hash", "expires_at", "attempts"]
               )

              try:
               send_mail(
                subject="Verify your new HerSteps email",
                message=(
                f"Your OTP to change your HerSteps email is: {otp}\n\n"
                "This OTP is valid for {OTP_EXPIRY_MINUTES} minutes."
                 ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[verification.new_email],
                fail_silently=False,
           )
              except Exception:
               logger.exception("Email-change OTP resend failed")
               verification.delete()
               messages.error(
                 request,
               "We couldn't send the email. Please start the email change again."
        )
               return redirect("my_accounts:profile")

              messages.success(request, "A new OTP has been sent.")
              return redirect("my_accounts:verify_email_change")
       
          otp = request.POST.get("otp", "").strip()

          if verification.expires_at <= now:
            messages.error(
                request,
                "Your OTP has expired. You can request a new one below."
            )
            return render(
                request,
                "my_accounts/verify_email_change.html",
                {
                    "new_email": verification.new_email,
                    "expires_at_timestamp": int(
                        verification.expires_at.timestamp() * 1000
                    ),
                },
            )

          if verification.attempts >= MAX_OTP_ATTEMPTS:
            verification.delete()
            messages.error(
                request,
                "Too many incorrect attempts. Please request a new OTP."
            )
            return redirect("my_accounts:profile")

          if not check_password(otp, verification.otp_hash):
            verification.attempts += 1
            verification.save(update_fields=["attempts"])

            messages.error(request, "Invalid OTP. Please try again.")
            return render(
                request,
                "my_accounts/verify_email_change.html",
                {"new_email": verification.new_email,
                 "expires_at_timestamp":int(verification.expires_at.timestamp()*1000),}
            )

        
          if User.objects.filter(
            email__iexact=verification.new_email
        ).exclude(pk=user.pk).exists():
            verification.delete()
            messages.error(
                request,
                "This email address is now registered to another account."
            )
            return redirect("my_accounts:profile")

        
          user.email = verification.new_email
          user.save(update_fields=["email"])

          verification.delete()
          logout(request)

          messages.success(
            request,
            "Your email has been updated successfully. Please log in with your new email."
        )
          return redirect("login")

    return render(
      request,
      "my_accounts/verify_email_change.html",
     {
        "new_email": verification.new_email,
        "expires_at_timestamp": int(
            verification.expires_at.timestamp() * 1000
        ),
     },
 )
@login_required
def change_password_view(request):
    if request.method == "POST":
        current_password = request.POST.get("current_password", "")
        new_password = request.POST.get("new_password", "")
        confirm_password = request.POST.get("confirm_password", "")

        
        if not request.user.check_password(current_password):
            messages.error(request, "Your current password is incorrect.")

       
        elif new_password != confirm_password:
            messages.error(request, "New password and confirm password do not match.")

        
        elif request.user.check_password(new_password):
            messages.error(request, "Your new password must be different from your current password.")

        else:
            
            try:
                validate_password(new_password, user=request.user)

            except ValidationError as error:
                for message in error.messages:
                    messages.error(request, message)

            else:
               
                request.user.set_password(new_password)
                request.user.save()

                
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
            return redirect('my_accounts:address_list')
    else:
        form=AddressForm()
   
    return render(request,'my_accounts/add_address.html',{'form':form,'page_title':'Add new Address',"button_text": "Save Address",})

@login_required
def edit_address_view(request,address_id):
    address= get_object_or_404(Address,id=address_id,user=request.user)

    if request.method=='POST':
        form=AddressForm(request.POST,instance=address)

        if form.is_valid():
             if form.is_valid():
              updated_address = form.save(commit=False)

             if updated_address.is_default:
                Address.objects.filter(
                    user=request.user
                ).exclude(id=address.id).update(
                    is_default=False
                )

             updated_address.save()

             messages.success(request,'Address updated successfully')
             return redirect('my_accounts:address_list')
    else:
        form= AddressForm(instance=address)
    return render(request,"my_accounts/add_address.html",{"form":form,"page_title":"Edit Address","button_text": "Save Address",})
@login_required
def delete_address_view(request,address_id):
    address=get_object_or_404(Address,id=address_id,user=request.user)

    if request.method=="POST":
        address.delete()

        messages.success(request,"Address deleted successfully")
        return redirect("my_accounts:address_list")

    return render(request,"my_accounts/delete_address.html",{'address':address})
@login_required
def set_default_address_view(request, address_id):
    if request.method == "POST":
        address = get_object_or_404(
            Address,
            id=address_id,
            user=request.user
        )

        Address.objects.filter(user=request.user).update(
            is_default=False
        )

        address.is_default = True
        address.save(update_fields=["is_default"])

        messages.success(request, "Default address updated.")

    return redirect("my_accounts:address_list")

def logout_view(request):


    if request.method == "POST":

      logout(request)
      messages.success(request, "You have been logged out.")
      return redirect("home")
    return render(request,'my_accounts/logout.html')