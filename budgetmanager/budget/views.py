from django.http.request import HttpRequest
from django.shortcuts import render, redirect
from .models import *
from . import forms

def index(request: HttpRequest):
    """Renders the homepage."""
    return render(request, "budget/index.html")
    