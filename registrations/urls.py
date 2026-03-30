from django.urls import path
from . import views
app_name = 'registrations'
urlpatterns = [
    path('', views.my_registrations, name='my_registrations'),
    path('register/<int:contest_id>/', views.register_solo, name='register_solo'),
    path('unregister/<int:registration_id>/', views.unregister_contest, name='unregister_contest'),
]
