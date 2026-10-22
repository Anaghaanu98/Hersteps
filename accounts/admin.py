from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser, OTPVerification


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("HerSteps account", {"fields": ("fullname", "is_verified", "is_google_user")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            "HerSteps account",
            {"fields": ("fullname", "email", "is_verified", "is_google_user")},
        ),
    )
    list_display = (
        "username",
        "email",
        "fullname",
        "is_google_user",
        "is_verified",
        "is_staff",
    )
    list_filter = UserAdmin.list_filter + ("is_google_user", "is_verified")
    search_fields = ("username", "email", "fullname")


admin.site.register(OTPVerification)

