from .models import Announcement

def active_announcement(request):
    ann = Announcement.objects.filter(is_active=True).first()
    return {'active_announcement': ann}
