from django.utils import timezone

def today():
    """Returns timezone-aware present date."""

    return timezone.now().date()

def now():
    """Returns timezone-aware present datetime."""

    return timezone.now()