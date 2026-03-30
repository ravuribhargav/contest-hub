from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import pre_save
from django.dispatch import receiver


@receiver(pre_save, sender=User)
def lowercase_username(sender, instance, **kwargs):
    if instance.username:
        instance.username = instance.username.lower()

BRANCH_CHOICES = [
    ('CSE', 'CSE'), ('CSD', 'CSD'), ('CSM', 'CSM'),
    ('CSO', 'CSO'), ('CSBS', 'CSBS'), ('IT', 'IT'),
]
YEAR_CHOICES = [(1, '1st Year'), (2, '2nd Year'), (3, '3rd Year'), (4, '4th Year')]


class UserProfile(models.Model):
    ROLE_CHOICES = [('admin', 'Admin'), ('student', 'Student')]
    ENTRY_CHOICES = [('Regular', 'Regular'), ('Lateral', 'Lateral')]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    reg_no = models.CharField(max_length=20, unique=True, null=True, blank=True)
    entry_type = models.CharField(max_length=10, choices=ENTRY_CHOICES, default='Regular')
    section = models.CharField(max_length=5, blank=True, null=True)
    profile_completed = models.BooleanField(default=False)
    
    profile_picture = models.ImageField(upload_to="profile_pics/", blank=True, null=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='student')
    branch = models.CharField(max_length=10, choices=BRANCH_CHOICES, blank=True)
    year = models.IntegerField(choices=YEAR_CHOICES, null=True, blank=True)
    phone = models.CharField(max_length=15, blank=True)
    department = models.CharField(max_length=100, blank=True)
    bio = models.TextField(blank=True)

    def __str__(self):
        return self.user.username

    def is_complete(self):
        return bool(
            self.user.email and 
            self.phone and 
            self.section and 
            self.branch and 
            self.year
        )

    def initials(self):
        name = self.user.get_full_name() or self.user.username
        parts = name.split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[-1][0]).upper()
        return name[:2].upper()

# Add role property to User model for convenience
@property
def user_role(self):
    return self.profile.role if hasattr(self, 'profile') else ('admin' if self.is_staff else 'student')

User.role = user_role


@property
def user_is_admin(self):
    if self.is_staff:
        return True
    if hasattr(self, 'profile'):
        return self.profile.role == 'admin'
    return False


User.is_admin = user_is_admin
