from django.db import models


from django.db import models
from django.contrib.auth.models import AbstractUser


class CustomUser(AbstractUser):
    fullname = models.CharField(max_length=150)

    email = models.EmailField(
        max_length=100,
        unique=True
    )
    phone_number = models.CharField(
    max_length=15,
    blank=True,
    default=""
)
    is_verified = models.BooleanField(default=False)
    is_google_user = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.fullname} ({self.email})"


class OTPVerification(models.Model):
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="otp_verification"
    )

    otp_hash = models.CharField(max_length=128)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    last_sent_at = models.DateTimeField(null=True, blank=True)
    def __str__(self):
        return f"OTP for {self.user.email}"
# Create your models here.
