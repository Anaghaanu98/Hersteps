
from django.contrib.auth.decorators import user_passes_test

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