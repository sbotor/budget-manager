from django.shortcuts import render

# Create your views here.

# Testing view
def index(request):
    return render(request, "budget/base.html")
