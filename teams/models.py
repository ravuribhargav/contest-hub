import uuid
import re
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from contests.models import Contest


class Team(models.Model):
    name = models.CharField(max_length=100)
    name_normalized = models.CharField(max_length=120, editable=False)
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE, related_name='teams')
    leader = models.ForeignKey(User, on_delete=models.CASCADE, related_name='led_teams')
    team_code = models.CharField(max_length=10, unique=True, blank=True)
    is_locked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['contest', 'name_normalized'],
                name='uniq_team_name_normalized_per_contest',
            ),
        ]

    @staticmethod
    def normalize_name(name):
        collapsed = re.sub(r'\s+', ' ', (name or '').strip())
        return collapsed.lower()

    def clean(self):
        display_name = re.sub(r'\s+', ' ', (self.name or '').strip())
        if not display_name:
            raise ValidationError({'name': 'Team name is required.'})

        normalized = self.normalize_name(display_name)
        if self.contest_id:
            duplicate_qs = Team.objects.filter(contest_id=self.contest_id, name_normalized=normalized)
            if self.pk:
                duplicate_qs = duplicate_qs.exclude(pk=self.pk)
            if duplicate_qs.exists():
                raise ValidationError({'name': 'Team name already exists in this contest.'})

        # Keep user-facing formatting while normalizing inner spaces.
        self.name = display_name
        self.name_normalized = normalized

    def save(self, *args, **kwargs):
        self.name = re.sub(r'\s+', ' ', (self.name or '').strip())
        self.name_normalized = self.normalize_name(self.name)
        if not self.team_code:
            self.team_code = uuid.uuid4().hex[:8].upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def members(self):
        return TeamMember.objects.filter(team=self).select_related('user__profile')

    def member_count(self):
        return TeamMember.objects.filter(team=self).count()

    def is_full(self):
        return self.member_count() >= self.contest.team_size_max

    def can_register(self):
        from registrations.models import Registration
        already_registered = Registration.objects.filter(team=self, contest=self.contest).exists()
        return (
            not already_registered
            and self.member_count() >= self.contest.team_size_min
            and self.contest.is_registration_open()
        )


class TeamMember(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='team_members')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='team_memberships')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('team', 'user')


