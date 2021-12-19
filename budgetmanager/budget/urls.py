from django.urls import path
from . import views

urlpatterns = [
    path('',  views.index, name='index'),
    path('user', views.UserView.as_view(), name='user_page'),
    path('user/history', views.OpHistoryView.as_view(), name='user_history'),
    path('user/labels', views.UserLabelsView.as_view(), name="user_labels")
]