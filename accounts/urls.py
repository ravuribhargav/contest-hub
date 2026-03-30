from django.urls import path
from . import views
from registrations.views import my_registrations

app_name = 'accounts'
urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('change-password/', views.change_password, name='change_password'),
    path('dashboard/', views.student_dashboard, name='student_dashboard'),
    path('my-contests/', my_registrations, name='my_contests'),
]
