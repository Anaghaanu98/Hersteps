from django.contrib import messages
from django.contrib.auth import SESSION_KEY, logout
from django.contrib.auth import get_user_model
from django.shortcuts import redirect

User = get_user_model()


class BlockedUserMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user_id = request.session.get(SESSION_KEY)

        if user_id:
            is_blocked = User.objects.filter(
                pk=user_id,
                is_blocked=True
            ).exists()

            if is_blocked:
                logout(request)

                messages.error(
                    request,
                    "Your account has been blocked. "
                    "Please contact support."
                )

                return redirect("login")

        return self.get_response(request)