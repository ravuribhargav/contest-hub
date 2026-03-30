from django.urls import path
from . import views
app_name = 'admin_panel'
urlpatterns = [
    path('contests/', views.contest_list, name='contests'),
    path('contest/create/', views.contest_create, name='contest_create'),
    path('contest/<int:pk>/edit/', views.contest_edit, name='contest_edit'),
    path('contest/<int:pk>/delete/', views.contest_delete, name='contest_delete'),
    path('contests/<int:pk>/', views.contest_participants, name='participants'),
    path('users/', views.users_list, name='users'),
    path('users/<int:user_id>/profile/', views.student_profile, name='student_profile'),
    path('users/reset-password/', views.reset_student_password, name='reset_student_password'),
    path('users/add-admin/', views.add_admin, name='add_admin'),
    path('users/upload/', views.users_upload, name='users_upload'),
    path('users/toggle/', views.toggle_user, name='toggle_user'),
    path('users/delete/', views.delete_user, name='delete_user'),
    path('teams/', views.teams_list, name='teams'),
    path('announcements/', views.announcements_view, name='announcements'),
]
