from django.shortcuts import render
import time
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import (
    authenticate,
    get_user_model,
    login as auth_login, password_validation
)
from django.contrib.auth.hashers import make_password, check_password
from django.core.mail import send_mail
from django.db import transaction
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from .forms import SignupForm
from .models import OTPVerification
import logging
logger=logging.getLogger(__name__)
User = get_user_model()

OTP_EXPIRY_MINUTES = 2
MAX_OTP_ATTEMPTS = 5
RESEND_COOLDOWN_SECONDS = 30


def generate_otp():
    return f"{secrets.randbelow(1_000_000):06d}"


def send_verification_email(user, otp):
    send_mail(
        subject="Verify your HerSteps account",
        message=(
            f"Hello {user.fullname},\n\n"
            f"Your HerSteps verification code is: {otp}\n\n"
            f"This code expires in {OTP_EXPIRY_MINUTES} minutes.\n"
            "If you did not request this code, please ignore this email."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )

def send_password_reset_email(user, otp):
    send_mail(
        subject="Reset Your HerSteps Password",
        message=(
            f"Hello {user.fullname or user.username},\n\n"
            f"Your HerSteps password reset OTP is: {otp}\n\n"
            f"This code expires in {OTP_EXPIRY_MINUTES} minutes.\n"
            "If you did not request a password reset, ignore this email."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )
@require_http_methods(["GET", "POST"])
def signup_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == "POST":
        form = SignupForm(request.POST) 

        if form.is_valid():
            try:
                with transaction.atomic():
                    user = User(
                        fullname=form.cleaned_data["fullname"],
                        username=form.cleaned_data["username"],
                        email=form.cleaned_data["email"],
                        is_active=False,
                        is_verified=False,
                    )

                    user.set_password(form.cleaned_data["password"])
                    user.save()

                    otp = generate_otp()

                    OTPVerification.objects.update_or_create(
                        user=user,
                        defaults={
                            "otp_hash": make_password(otp),
                            "expires_at": timezone.now()
                            + timedelta(minutes=OTP_EXPIRY_MINUTES),
                            "attempts": 0,
                            'last_sent_at': timezone.now(),
                        },
                    )

                send_verification_email(user, otp)

                request.session["pending_verification_user_id"] = user.pk

                messages.success(
                    request,
                    "We sent a verification code to your email."
                )
                return redirect("verify_email")

            except Exception:
                logger.exception('Signup failed')
                messages.error(
                    request,
                    "We couldn't complete signup. Please try again."
                )
    else:
        form = SignupForm()

    return render(request, "accounts/signup.html", {"form": form})


@require_http_methods(["GET", "POST"])
def verify_email_view(request):
    if request.user.is_authenticated:
        return redirect("home")

    user_id = request.session.get("pending_verification_user_id")

    if not user_id:
        messages.error(
            request,
            "Please sign up before verifying your email."
        )
        return redirect("signup")

    user = User.objects.filter(pk=user_id).first()

    if not user:
        request.session.pop("pending_verification_user_id", None)
        messages.error(request, "Account not found. Please sign up again.")
        return redirect("signup")

    if user.is_verified:
        request.session.pop("pending_verification_user_id", None)
        return redirect("login")

    verification = OTPVerification.objects.filter(user=user).first()

    if request.method == "POST":
        action = request.POST.get("action", "verify")
        if action == "resend":
         now = timezone.now()

        #  if verification and now < verification.expires_at:
        #   remaining = int(
        #     (verification.expires_at - now).total_seconds()
        #   ) + 1

        #   messages.error(
        #     request,
        #     f"Please wait {remaining} seconds until your OTP expires."
        #   )
        #   return redirect("verify_email")

         otp = generate_otp()

         OTPVerification.objects.update_or_create(
          user=user,
          defaults={
            "otp_hash": make_password(otp),
            "expires_at": now + timedelta(minutes=OTP_EXPIRY_MINUTES),
            "attempts": 0,
            "last_sent_at": now,
           },
          )

         try:
          send_verification_email(user, otp)
         except Exception:
          logger.exception("Resend verification email failed")
          messages.error(
            request,
            "We couldn't send the email. Please try again later."
         )
         else:
          messages.success(request, "A new OTP has been sent.")

         return redirect("verify_email")
     

        otp = request.POST.get("otp", "").strip()

        if not (otp.isdigit() and len(otp) == 6):
            messages.error(request, "Enter the complete six-digit OTP.")
            return redirect("verify_email")

        verification = OTPVerification.objects.filter(user=user).first()

        if not verification:
            messages.error(request, "Request a new verification code.")
            return redirect("verify_email")

        if verification.attempts >= MAX_OTP_ATTEMPTS:
            messages.error(
                request,
                "Too many incorrect attempts. Request a new OTP."
            )
            return redirect("verify_email")

        if timezone.now() >= verification.expires_at:
            messages.error(
                request,
                "Your OTP has expired. Please request a new one."
            )
            return redirect("verify_email")

        if not check_password(otp, verification.otp_hash):
           verification.attempts += 1
           verification.save(update_fields=["attempts"])

           if verification.attempts >= MAX_OTP_ATTEMPTS:
              messages.error(
                 request,
                "Too many incorrect attempts. Request a new OTP."
              )
           else:
             remaining = MAX_OTP_ATTEMPTS - verification.attempts
             messages.error(
                 request,
                 f"Incorrect OTP. You have {remaining} attempts remaining."
        )

           return redirect("verify_email")

        user.is_verified = True
        user.is_active = True
        user.save(update_fields=["is_verified", "is_active"])

        verification.delete()
        request.session.pop("pending_verification_user_id", None)

        auth_login(request, user,backend="django.contrib.auth.backends.ModelBackend")

        messages.success(
            request,
            "Your email has been verified. Welcome to HerSteps!"
        )
        return redirect("home")

    return render(
        request,
        "accounts/verify_email.html",
        {"email": user.email,
         'expires_at_timestamp':(
             int(verification.expires_at.timestamp()*1000)
             if verification else 0
         ),},
    )

@require_http_methods(["GET", "POST"])
def login_view(request):
    if (request.user.is_authenticated and 
        request.user.is_staff or request.user.is_superuser
    ):
        return redirect('admin_panel:admin_dashboard')
    if (request.user.is_authenticated and not request.user.is_staff and not request.user.is_superuser):
        return redirect("home")


    if request.method == "POST":
        identifier = request.POST.get("identifier", "").strip()
        password = request.POST.get("password", "")

        user = User.objects.filter(
            email__iexact=identifier
        ).first()
        
        if user is None:
            user = User.objects.filter(
                username__iexact=identifier
            ).first()
        if user and user.is_blocked:
            if user.check_password(password):
                messages.error(request,"Your account has been blocked by admin")
            else:
                messages.error(request,"Invalid email/username or password.")
        elif user and not user.is_active:
            if user.check_password(password) and not user.is_verified:
                request.session["pending_verification_user_id"]=user.pk
                messages.error(request,"Please verify your email before logging in")
                return redirect("verify_email")

            messages.error(request,"This account is inactive. Please contact support.")
        else:
         authenticated_user = None

         if user:
            authenticated_user = authenticate(
                request,
                username=user.username,
                password=password,
            )

         if authenticated_user is None:
            messages.error(
                request,
                "Invalid email/username or password."
            )

         elif not authenticated_user.is_verified:
            request.session[
                "pending_verification_user_id"
            ] = authenticated_user.pk

            messages.error(
                request,
                "Please verify your email before logging in."
            )
            return redirect("verify_email")

         else:
            auth_login(request, authenticated_user)
            return redirect("home")

    return render(request, "accounts/login.html")

def forgot_password_view(request):
    if request.method == "POST":
        email=request.POST.get("email","").strip()

        # check email is empty
        if not email:
            messages.error(request,'Please enter your email address')
            return render(request,'accounts/forgot_password.html')
       
        try:
            validate_email(email)

        except ValidationError:
            messages.error(request,"Please enter a valid email address")
            return render(request,'accounts/forgot_password.html')
        
        user=User.objects.filter(email__iexact=email).first()

        
        if not user or not user.is_active or not user.is_verified:
            messages.error(request,"We couldn't process that account. Check your email ")
            return render(request,"accounts/forgot_password.html")   

        
        otp=f"{secrets.randbelow(1_000_000):06d}"

        
        OTPVerification.objects.update_or_create(
            user=user,
            defaults={
                "otp_hash":make_password(otp),
                "expires_at": timezone.now()+ timedelta(minutes=OTP_EXPIRY_MINUTES),
                "attempts":0,
                "last_sent_at": timezone.now(),
            },
        )
        #Send otp to the email
        try:
            send_mail(
                subject="Reset Your Password",
                message=(f"Hello{user.fullname or user.username},\n\n"
                         f"Your password reset otp is:{otp}\n\n"
                         f"This OTP expires in {OTP_EXPIRY_MINUTES} minutes.\n\n"
                         "If you did not request this, please ignore this email."),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
        except Exception:
            OTPVerification.objects.filter(user=user).delete()
            messages.error(request,"We couldn't send the OTP. Please try again later")
            return render(request,'accounts/forgot_password.html')

        #updating the session
        request.session['password_reset_user_id']=user.pk
        request.session.pop('password_reset_verified_user_id',None)
        request.session['password_reset_last_sent']=time.time()

        messages.success(request, 'OTP sent to your registered email address.')
        return redirect('verify_reset_otp')
     
    return render(request, "accounts/forgot_password.html")

def verify_reset_otp_view(request):
    user_id=request.session.get('password_reset_user_id')
    
    if not user_id:
        messages.error(request, "Please request a password reset first.")
        return redirect("forgot_password")

    user=User.objects.filter(pk=user_id,is_active=True,is_verified=True).first()
   
    if not user:
        request.session.pop("password_reset_user_id", None)
        messages.error(
            request,
            "Account not found. Please request a password reset again."
        )
        return redirect("forgot_password")

    verification = OTPVerification.objects.filter(user=user).first()
    if request.method == "POST":
        action = request.POST.get("action", "verify")
        now = timezone.now()

        # RESEND OTP
        if action == "resend":

            if verification and verification.last_sent_at:
                time_since_last_send = (
                    now - verification.last_sent_at
                ).total_seconds()

                if time_since_last_send < RESEND_COOLDOWN_SECONDS:
                    remaining = int(
                        RESEND_COOLDOWN_SECONDS - time_since_last_send
                    ) + 1

                    messages.error(
                        request,
                        f"Please wait {remaining} seconds before "
                        "requesting another code."
                    )
                    return redirect("verify_reset_otp")

            otp = generate_otp()

            OTPVerification.objects.update_or_create(
                user=user,
                defaults={
                    "otp_hash": make_password(otp),
                    "expires_at": now + timedelta(
                        minutes=OTP_EXPIRY_MINUTES
                    ),
                    "attempts": 0,
                    "last_sent_at": now,
                },
            )
            try:
                send_password_reset_email(user, otp)
            except Exception:
                
                OTPVerification.objects.filter(user=user).delete()

                messages.error(
                    request,
                    "We couldn't send the email. Please try again later."
                )
            else:
                messages.success(
                    request,
                    "A new password reset OTP has been sent."
                )

            return redirect("verify_reset_otp")
        # VERIFY OTP
        otp = request.POST.get("otp", "").strip()

        if not (otp.isdigit() and len(otp) == 6):
            messages.error(
                request,
                "Enter the complete six-digit OTP."
            )
            return redirect("verify_reset_otp")

        verification = OTPVerification.objects.filter(user=user).first()

        if not verification:
            messages.error(
                request,
                "Request a new password reset OTP."
            )
            return redirect("forgot_password")

        if verification.attempts >= MAX_OTP_ATTEMPTS:
            verification.delete()
            request.session.pop("password_reset_user_id", None)

            messages.error(
                request,
                "Too many incorrect attempts. Request a new OTP."
            )
            return redirect("forgot_password")

        if now >= verification.expires_at:
            verification.delete()
            request.session.pop("password_reset_user_id", None)

            messages.error(
                request,
                "Your OTP has expired. Please request a new one."
            )
            return redirect("forgot_password")

        if not check_password(otp, verification.otp_hash):
            verification.attempts += 1
            verification.save(update_fields=["attempts"])

            if verification.attempts >= MAX_OTP_ATTEMPTS:
                verification.delete()
                request.session.pop("password_reset_user_id", None)

                messages.error(
                    request,
                    "Too many incorrect attempts. Request a new OTP."
                )
            else:
                remaining = MAX_OTP_ATTEMPTS - verification.attempts

                messages.error(
                    request,
                    f"Incorrect OTP. You have {remaining} attempts remaining."
                )

            return redirect("verify_reset_otp")
        # OTP is correct: authorize password reset
        verification.delete()

        request.session["password_reset_verified_user_id"] = user.pk
        request.session.pop("password_reset_user_id", None)

        messages.success(
            request,
            "Email verified. You can now create a new password."
        )
        return redirect("reset_password")
    

    return render(
        request,
        "accounts/verify_reset_otp.html",
        {"email": user.email,"expires_at_timestamp":(int(verification.expires_at.timestamp()*1000) 
            if verification else 0 )},
    )

def reset_password_view(request):
    user_id = request.session.get("password_reset_verified_user_id")

    
    if not user_id:
        messages.error(
            request,
            "Please verify your OTP before resetting your password."
        )
        return redirect("forgot_password")

    user = User.objects.filter(
        pk=user_id,
        is_active=True,
        is_verified=True,
    ).first()

    if not user:
        request.session.pop("password_reset_verified_user_id", None)
        messages.error(request, "Please start the password reset again.")
        return redirect("forgot_password")

    if request.method == "POST":
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")

        
        if not password or not confirm_password:
            messages.error(request, "Both password fields are required.")
            return render(request, "accounts/reset_password.html")

       
        if password != confirm_password:
            messages.error(request, "The passwords do not match.")
            return render(request, "accounts/reset_password.html")

       
        try:
            password_validation.validate_password(password, user=user)
        except ValidationError as errors:
            for error in errors:
                messages.error(request, error)
            return render(request, "accounts/reset_password.html")

        
        user.set_password(password)
        user.save(update_fields=["password"])

        
        request.session.pop("password_reset_verified_user_id", None)
        request.session.pop("password_reset_user_id", None)
        request.session.pop("password_reset_last_sent", None)

       
        OTPVerification.objects.filter(user=user).delete()

        messages.success(
            request,
            "Your password has been updated successfully. Please log in."
        )
        return redirect("login")

    return render(request, "accounts/reset_password.html")
def home_view(request):
    if request.user.is_authenticated:
     if request.user.is_staff or request.user.is_superuser:
        return render(request, "admin_panel/dashboard.html")
     else:
        return render(request, "accounts/home.html")
# Create your views here.
    return render(request, "accounts/home.html")