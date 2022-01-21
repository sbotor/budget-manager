from django.contrib.auth.decorators import user_passes_test

def home_required(redirect_url: str = None):
    """A decorator checking if the user is authenticated and has an Account and a Home."""

    redirect_url = redirect_url or '/'
    
    return user_passes_test(
        lambda u: u.is_authenticated and hasattr(u, 'account') and hasattr(u.account, 'home'),
        login_url=redirect_url,
        redirect_field_name='')
