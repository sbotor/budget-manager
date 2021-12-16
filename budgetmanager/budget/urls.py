from django.urls import path
from . import views

urlpatterns = [
    path('',  views.index),

    path('homes', views.show_homes),
    path('homes/add', views.add_home),
    path('homes/remove', views.remove_home),

    path('users', views.show_users),
    path('users/add', views.add_user),
    path('users/remove', views.remove_user)
]