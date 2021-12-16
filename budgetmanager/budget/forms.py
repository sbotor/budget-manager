from django import forms
from . import models

class CreateHome(forms.Form):
    """Form for new Home creation."""

    home_name = forms.CharField(max_length=20, label='Home name')
    """Home name. Does not have to be unique."""

    admin_name = forms.CharField(max_length = 20, label='Administrator username')
    """Admin user name. Has to be unique. This is the user name for the starter Account."""

class CreateAccount(forms.Form):
    """Form for new Account creation."""

    user_name = forms.CharField(max_length=20, label='User name')
    """User name. Has to be unique."""

    home = forms.ModelChoiceField(models.Home.objects.all(), to_field_name="name", label="Home")
    """Home to which the user should belong."""