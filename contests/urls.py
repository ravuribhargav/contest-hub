from django.urls import path
from . import views
app_name = 'contests'
urlpatterns = [
    path('', views.home, name='home'),
    path('contests/', views.contest_list, name='list'),
    path('contests/<int:pk>/', views.contest_detail, name='detail'),
    path('archive/', views.archive, name='archive'),
]
