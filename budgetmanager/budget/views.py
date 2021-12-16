from django.http.request import HttpRequest
from django.shortcuts import render, redirect
from .models import *
from . import forms

def index(request: HttpRequest):
    """Renders the homepage."""
    return render(request, "budget/index.html")

def show_homes(request):
    """View rendering the Homes page."""

    context = {
        'form': forms.CreateHome,
        'homes': Home.objects.all()[:10:-1]
    }
    return render(request, 'budget/homes.html', context)

def add_home(request: HttpRequest):
    """View creating a new Home. Returns a redirect to the homepage if the Home cannot be created."""

    if request.method == "POST":
        form = forms.CreateHome(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            home = Home.create_home(data.get('home_name'), data.get('admin_name'))
            if home is not None:
                return redirect('/homes')

    return redirect('')

def remove_home(request: HttpRequest):
    """Removes a home and all accounts bound to it. Returns a redirect to the homepage if the Home cannot be removed."""

    if request.method == "POST":
        home_id = request.POST.get('home_id')
        home = Home.objects.filter(id=home_id)
        home.delete()

        return redirect('/homes')
    
    return redirect('')

def show_users(request: HttpRequest):
    """Renders the Users page."""

    context = {
        'form': forms.CreateAccount,
        'accounts': Account.objects.all()[:10:-1]
    }
    return render(request, 'budget/users.html', context)

def add_user(request: HttpRequest):
    """Creates a new Account and binds it to a Home. Returns a redirect to the homepage if the Account cannot be created."""

    if request.method == "POST":
        form = forms.CreateAccount(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            data.get('home').add_account(data.get('user_name'))

            return redirect('/users')

    return redirect('')

def remove_user(request: HttpRequest):
    """Removes an Account. Returns a redirect to the homepage if the Account cannot be removed."""

    if request.method == 'POST':
        account_id = request.POST.get('account_id')
        account = Account.objects.filter(id=account_id)
        account.delete()

        return redirect('/users')
    
    return redirect('')