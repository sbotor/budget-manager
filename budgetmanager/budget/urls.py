from django.urls import path
from . import views

urlpatterns = [
    path('',  views.index, name='index'),
    path('user', views.UserView.as_view(), name='user_page'),
    path('user/history', views.OpHistoryView.as_view(), name='user_history'),
    path('user/labels', views.UserLabelsView.as_view(), name='user_labels'),
    path('user/planned', views.CyclicOperationsView.as_view(), name='planned_operations'),
    
    path('home', views.HomeView.as_view(), name='user_home'),
    path('home/<str:username>', views.AccountView.as_view(), name='manage_user'),
    path('view_as', views.ViewAsView.as_view(), name='view_as'),

    path('new/', views.AddHomeView.as_view(), name='new_home'),
]