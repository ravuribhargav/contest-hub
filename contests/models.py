from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

CATEGORY_CHOICES = [
    ('Hackathon', 'Hackathon'),
    ('Coding Contest', 'Coding Contest'),
    ('Workshop', 'Workshop'),
]
PARTICIPATION_CHOICES = [
    ('solo', 'Solo'), ('team', 'Team'),
]
ALL_BRANCHES = ['CSE', 'CSD', 'CSM', 'CSO', 'CSBS', 'IT']
ALL_YEARS = [1, 2, 3, 4]
ORGANIZING_BRANCH_CHOICES = [
    ('CSE', 'CSE'),
    ('CSD', 'CSD'),
    ('CSM', 'CSM'),
    ('CSO', 'CSO'),
    ('CSBS', 'CSBS'),
    ('IT', 'IT'),
]


class Contest(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    venue = models.CharField(max_length=200)
    banner = models.ImageField(upload_to='banners/', blank=True, null=True)
    participation_type = models.CharField(max_length=10, choices=PARTICIPATION_CHOICES, default='solo')
    team_size_min = models.IntegerField(default=2)
    team_size_max = models.IntegerField(default=5)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    registration_deadline = models.DateTimeField()
    is_registration_enabled = models.BooleanField(
        default=False,
        help_text="Enable to allow registrations anytime (spot registration)",
    )
    is_featured = models.BooleanField(default=False)
    eligible_branches = models.JSONField(default=list)
    eligible_years = models.JSONField(default=list)
    organizing_branches = models.JSONField(blank=True, null=True)
    allow_mixed_branches = models.BooleanField(default=True)
    organizers = models.ManyToManyField(User, blank=True, related_name='organized_contests')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def get_status(self):
        now = timezone.now()
        if now > self.end_date:
            return "Completed"
        if self.start_date <= now <= self.end_date:
            return "Ongoing"

        # Before registration deadline, registration is open.
        if now < self.registration_deadline:
            return "Registration Open"

        # After deadline and before start, only spot-enabled contests remain open.
        if now < self.start_date:
            return "Registration Open" if self.is_registration_enabled else "Registration Closed"

        # Between start and end is handled above; this fallback keeps state explicit.
        if self.is_registration_enabled and now < self.end_date:
            return "Registration Open"

        return "Registration Closed"

    def has_ended(self):
        return timezone.now() >= self.end_date

    def is_registration_open(self, now=None):
        if now is None:
            now = timezone.now()
        if now >= self.end_date:
            return False
        if self.is_registration_enabled:
            return True
        return now <= self.registration_deadline

    def get_user_team(self, user):
        if not user or not user.is_authenticated:
            return None
        from teams.models import Team
        return Team.objects.filter(contest=self, team_members__user=user).first()

    def is_completed(self):
        return timezone.now() > self.end_date

    def participant_count(self):
        return self.registrations.count()

    def is_student_eligible(self, profile):
        if not profile or not profile.branch or not profile.year:
            return False
        branches = self.eligible_branches or ALL_BRANCHES
        years = self.eligible_years or ALL_YEARS
        return profile.branch in branches and profile.year in years
