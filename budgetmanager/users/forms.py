from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from budget.models import Home

class HomeCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'home_name', 'password1', 'password2']

    home_name = forms.CharField(
        max_length=50,
        label='Home name',
        help_text='Your home\'s name. Maximum length is 50 characters.')

    def save(self, commit: bool = True):
        user = super().save(commit=True)
        home = Home.create_home(self.cleaned_data.get('home_name'), user)
        
        if home is None:
            user.delete()
        
        return home
