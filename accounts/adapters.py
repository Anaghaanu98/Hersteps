from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.core.exceptions import ImmediateHttpResponse
from django.contrib import messages
from django.shortcuts import redirect


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):

    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)

        if sociallogin.account.provider == "google":
            extra_data = sociallogin.account.extra_data

            # Populate the full name
            fullname = (
                extra_data.get("name")
                or " ".join(
                    part for part in (
                        extra_data.get("given_name", ""),
                        extra_data.get("family_name", ""),
                    )
                    if part
                )
            )

            if fullname:
                user.fullname = fullname

            # Generate a username if Google signup did not provide one
            if not user.username:
                email = data.get("email") or extra_data.get("email", "")
                username = email.split("@")[0] if email else "google_user"

                user.username = username

        return user

    def save_user(self, request, sociallogin, form=None):
        if sociallogin.account.provider == "google":
            user = sociallogin.user
            user.is_google_user = True

        return super().save_user(request, sociallogin, form)

    def pre_social_login(self, request, sociallogin):
        user = sociallogin.user

        if (
            sociallogin.account.provider == "google"
            and user.pk is not None
            and user.is_blocked
        ):
            messages.error(
                request,
                "Your account has been blocked. Please contact support."
            )
            raise ImmediateHttpResponse(redirect("login"))

        # Preserve your existing Google-user logic
        if (
            sociallogin.account.provider == "google"
            and user.pk is not None
            and not user.is_google_user
        ):
            user.is_google_user = True
            user.save(update_fields=["is_google_user"])