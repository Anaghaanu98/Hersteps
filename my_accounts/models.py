from django.db import models
from django.conf import settings

class Address(models.Model):
    ADDRESS_CHOICES = (
        ('home', 'Home'),
        ('work', 'Work'),
    )

    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='addresses')

    full_name = models.CharField(max_length=100)
    phone=models.CharField(max_length=15)
    house_name=models.CharField(max_length=255)
    locality=models.CharField(max_length=100)
    city=models.CharField(max_length=100)
    state=models.CharField(max_length=100)
    pincode=models.CharField(max_length=10)
    address_type=models.CharField(max_length=10,choices=ADDRESS_CHOICES,default='Home')
    created_at=models.DateTimeField(auto_now_add=True)
    is_default=models.BooleanField(default=False)
    def __str__(self):
        return f"{self.full_name} - (self.city)"

class EmailChangeVerification(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="email_change_verification"
    )
    new_email = models.EmailField()
    otp_hash = models.CharField(max_length=128)
    expires_at = models.DateTimeField()
    attempts = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Email change for {self.user.username}"
