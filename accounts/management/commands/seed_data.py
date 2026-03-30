from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from accounts.models import UserProfile
from contests.models import Contest
from announcements.models import Announcement


class Command(BaseCommand):
    help = 'Seed development data'

    def handle(self, *args, **options):
        if not User.objects.filter(username='admin').exists():
            admin = User.objects.create_superuser('admin', 'admin@rvrjc.ac.in', 'admin123')
            UserProfile.objects.get_or_create(user=admin)
            self.stdout.write(self.style.SUCCESS('Created: admin / admin123'))

        students = [
            ('alice', 'Alice', 'Johnson', 'CSE', 2),
            ('bob', 'Bob', 'Smith', 'CSD', 3),
            ('carol', 'Carol', 'Davis', 'IT', 1),
            ('dave', 'Dave', 'Wilson', 'CSM', 4),
        ]
        for uname, fn, ln, branch, year in students:
            if not User.objects.filter(username=uname).exists():
                u = User.objects.create_user(uname, f'{uname}@rvrjc.ac.in', 'student123', first_name=fn, last_name=ln)
                UserProfile.objects.create(user=u, branch=branch, year=year)
                self.stdout.write(f'Created: {uname} / student123')

        if not Announcement.objects.exists():
            Announcement.objects.create(
                text='Hackathon 2026 registrations are now open! Register before the deadline.',
                is_active=True
            )

        now = timezone.now()
        contests = [
            dict(title='InnoHack 2026', description='The flagship 24-hour hackathon of RVR & JC College. Build innovative solutions to real-world problems. Open to all branches.', category='Hackathon', venue='Main Auditorium, Block A', participation_type='team', team_size_min=3, team_size_max=5, start_date=now+timedelta(days=15), end_date=now+timedelta(days=16), registration_deadline=now+timedelta(days=10), is_featured=True, eligible_branches=['CSE','CSD','CSM','CSO','CSBS','IT'], eligible_years=[1,2,3,4], allow_mixed_branches=True),
            dict(title='Code Sprint 2026', description='A competitive programming marathon. Solve algorithmic challenges across multiple difficulty levels. Solo participants only.', category='Coding Contest', venue='CS Lab Complex', participation_type='solo', team_size_min=1, team_size_max=1, start_date=now+timedelta(days=5), end_date=now+timedelta(days=5, hours=6), registration_deadline=now+timedelta(days=3), is_featured=True, eligible_branches=['CSE','CSD','IT'], eligible_years=[2,3,4], allow_mixed_branches=True),
            dict(title='AI/ML Workshop', description='A hands-on workshop on Machine Learning, deep learning, and practical applications. Bring your laptops!', category='Workshop', venue='Seminar Hall 2', participation_type='solo', team_size_min=1, team_size_max=1, start_date=now+timedelta(days=8), end_date=now+timedelta(days=8, hours=8), registration_deadline=now+timedelta(days=6), is_featured=True, eligible_branches=['CSE','CSD','CSM'], eligible_years=[2,3,4], allow_mixed_branches=True),
            dict(title='HackFest 2025', description='The 2025 edition of our annual hackathon - archived.', category='Hackathon', venue='Main Auditorium', participation_type='team', team_size_min=2, team_size_max=4, start_date=now-timedelta(days=120), end_date=now-timedelta(days=119), registration_deadline=now-timedelta(days=125), is_featured=False, eligible_branches=['CSE','CSD','IT'], eligible_years=[1,2,3,4], allow_mixed_branches=True),
        ]
        for cd in contests:
            if not Contest.objects.filter(title=cd['title']).exists():
                Contest.objects.create(**cd)
                self.stdout.write(f'Contest: {cd["title"]}')

        self.stdout.write(self.style.SUCCESS('\nSeed complete!'))
        self.stdout.write('  http://127.0.0.1:8000/')
        self.stdout.write('  Admin: admin / admin123')
