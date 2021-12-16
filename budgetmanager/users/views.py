from django.http.request import HttpRequest
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from .forms import HomeCreationForm
from django.contrib import messages

from budget.models import Home

def add_home(request: HttpRequest):
    if request.method == 'POST':
        form = HomeCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('/')
        else:
            return render(request, 'users/register.html', {'form': form})
    
    form = HomeCreationForm()
    return render(request, 'users/register.html', {'form': form})
