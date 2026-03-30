from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('django-admin/', admin.site.urls),
    path('', include('contests.urls')),
    path('accounts/', include('accounts.urls')),
    path('teams/', include('teams.urls')),
    path('registrations/', include('registrations.urls')),
    path('admin/', include('admin_panel.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
