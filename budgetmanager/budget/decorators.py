from contextlib import redirect_stderr
from django.contrib.auth.decorators import user_passes_test, login_required

def home_required(redirect_url: str = None):
    """TODO"""

    return user_passes_test(
        lambda u: u.is_authenticated and hasattr(u, 'account') and hasattr(u.account, 'home'),
        login_url=redirect_url,
        redirect_field_name='')

    