from django.http.request import HttpRequest
from django.shortcuts import render, redirect
from .models import *
from . import forms

def index(request: HttpRequest):
    """Renders the homepage."""
    
    context = {
        'operations': []
    }
    
    if request.user.is_authenticated:
        context['operations'] = Operation.objects.filter(account=request.user.account)
    

    return render(request, "budget/index.html", context)
