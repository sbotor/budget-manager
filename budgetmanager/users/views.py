from django.http.request import HttpRequest
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from .forms import HomeCreationForm
from django.contrib import messages

def add_home(request: HttpRequest):
    if request.method == 'POST':
        form = HomeCreationForm(request.POST)
        if form.is_valid():
            form.save()
            home_name = form.cleaned_data.get('home_name')
            messages.success(request, f'Home "{home_name}" was successfully created')
            return redirect('/')
        else:
            return render(request, 'users/register.html', {'form': form})
    
    form = HomeCreationForm()
    return render(request, 'users/register.html', {'form': form})
