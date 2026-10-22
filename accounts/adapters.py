from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def _mark_google_user(self, sociallogin):
        user = sociallogin.user
        user.is_google_user = True

        extra_data = sociallogin.account.extra_data
        fullname = extra_data.get("name") or " ".join(
            part
            for part in (
                extra_data.get("given_name", ""),
                extra_data.get("family_name", ""),
            )
            if part
        )
        if fullname:
            user.fullname = fullname

    def save_user(self, request, sociallogin, form=None):
        if sociallogin.account.provider == "google":
            self._mark_google_user(sociallogin)
        return super().save_user(request, sociallogin, form)

    def pre_social_login(self, request, sociallogin):
        if (
            sociallogin.account.provider == "google"
            and sociallogin.user.pk is not None
            and not sociallogin.user.is_google_user
        ):
            sociallogin.user.is_google_user = True
            sociallogin.user.save(update_fields=["is_google_user"])
