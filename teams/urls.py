from django.urls import path
from . import views
app_name = 'teams'
urlpatterns = [
    path('', views.my_teams, name='my_teams'),
    path('create/<int:contest_id>/', views.create_team, name='create'),
    path('join/', views.join_team, name='join'),
    path('<int:pk>/', views.team_detail, name='detail'),
    path('<int:pk>/remove-member/<int:user_id>/', views.remove_member, name='remove_member'),
    path('<int:pk>/unregister/', views.unregister_team, name='unregister'),
    path('<int:pk>/leave/', views.leave_team, name='leave'),
    path('<int:pk>/delete/', views.delete_team, name='delete'),
    path('<int:pk>/register/', views.register_team, name='register'),
]
