from django.db import models
from django.contrib.auth.models import User
from contests.models import Contest
from teams.models import Team


class Registration(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='registrations')
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE, related_name='registrations')
    team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True, related_name='registrations')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'contest')
        constraints = [
            models.UniqueConstraint(
                fields=['team', 'contest'],
                condition=models.Q(team__isnull=False),
                name='uniq_team_contest_registration',
            ),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.contest.title}"

    def participation_type(self):
        return 'Team' if self.team else 'Solo'
