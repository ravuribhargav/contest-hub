import csv
import io
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import HttpResponse
from django.utils import timezone
from django.db.models import Q, Count
from django.urls import reverse
from urllib.parse import urlencode
from contests.models import Contest, ALL_BRANCHES, ALL_YEARS, ORGANIZING_BRANCH_CHOICES
from registrations.models import Registration
from teams.models import Team, TeamMember
from accounts.models import UserProfile, BRANCH_CHOICES, YEAR_CHOICES
from announcements.models import Announcement
from datetime import datetime
from django.utils.timezone import make_aware


def is_admin(user):
    return user.is_authenticated and user.is_staff


@login_required
@user_passes_test(is_admin)
def contest_list(request):
    contests = Contest.objects.annotate(reg_count=Count('registrations', distinct=True)).order_by('-created_at')
    return render(request, 'admin_panel/contests.html', {'contests': contests})


def _parse_dt(s):
    return make_aware(datetime.strptime(s, '%Y-%m-%dT%H:%M'))


def _save_contest_from_post(request, contest=None):
    d = request.POST
    try:
        participation_type = d.get('participation_type', 'solo')
        if participation_type not in ('solo', 'team'):
            participation_type = 'team' if participation_type == 'both' else 'solo'

        if participation_type == 'team':
            team_size_min = int(d.get('team_size_min', 2))
            team_size_max = int(d.get('team_size_max', 5))
            if team_size_min < 2:
                raise ValueError('Min team size must be at least 2 for team contests.')
            if team_size_max < team_size_min:
                raise ValueError('Max team size must be greater than or equal to min team size.')
        else:
            team_size_min = 1
            team_size_max = 1

        kwargs = {
            'title': d['title'],
            'description': d['description'],
            'category': d['category'],
            'venue': d['venue'],
            'participation_type': participation_type,
            'team_size_min': team_size_min,
            'team_size_max': team_size_max,
            'start_date': _parse_dt(d['start_date']),
            'end_date': _parse_dt(d['end_date']),
            'registration_deadline': _parse_dt(d['registration_deadline']),
            'is_registration_enabled': 'is_registration_enabled' in d,
            'is_featured': 'is_featured' in d,
            'allow_mixed_branches': 'allow_mixed_branches' in d,
            'eligible_branches': request.POST.getlist('eligible_branches') or ALL_BRANCHES,
            'eligible_years': [int(y) for y in request.POST.getlist('eligible_years')] or ALL_YEARS,
            'organizing_branches': request.POST.getlist('organizing_branches') or None,
        }

        if kwargs['end_date'] <= kwargs['start_date']:
            raise ValueError('End date must be greater than Start date.')

        if kwargs['registration_deadline'] > kwargs['start_date']:
            raise ValueError('Registration deadline must be less than or equal to Start date.')

        if contest is None:
            contest = Contest(**kwargs)
        else:
            for k, v in kwargs.items():
                setattr(contest, k, v)
        if 'banner' in request.FILES:
            contest.banner = request.FILES['banner']
        contest.save()
        raw_organizers = d.get('organizers', '').strip()
        if raw_organizers:
            organizer_ids = [int(oid) for oid in raw_organizers.split(',') if oid.strip().isdigit()]
        else:
            organizer_ids = [int(oid) for oid in request.POST.getlist('organizers') if str(oid).isdigit()]
        contest.organizers.set(User.objects.filter(is_staff=False, id__in=organizer_ids))
        return contest
    except Exception as e:
        messages.error(request, f'Error saving contest: {e}')
        return None


@login_required
@user_passes_test(is_admin)
def contest_create(request):
    if request.method == 'POST':
        c = _save_contest_from_post(request)
        if c:
            success_msg = 'Contest created.'
            messages.success(request, success_msg)
            target = reverse('admin_panel:contests')
            query = urlencode({'success_action': 'admin_contest_create', 'success_msg': success_msg, 'contest_id': c.pk})
            return redirect(f'{target}?{query}')
    return render(request, 'admin_panel/contest_form.html', {
        'action': 'Create',
        'branches': ALL_BRANCHES,
        'years': ALL_YEARS,
        'organizing_branch_choices': ORGANIZING_BRANCH_CHOICES,
        'organizer_users': User.objects.filter(is_staff=False).order_by('username'),
    })


@login_required
@user_passes_test(is_admin)
def contest_edit(request, pk):
    contest = get_object_or_404(Contest, pk=pk)
    if request.method == 'POST':
        c = _save_contest_from_post(request, contest)
        if c:
            messages.success(request, 'Contest updated.')
            return redirect('admin_panel:contests')
    return render(request, 'admin_panel/contest_form.html', {
        'action': 'Edit',
        'contest': contest,
        'branches': ALL_BRANCHES,
        'years': ALL_YEARS,
        'organizing_branch_choices': ORGANIZING_BRANCH_CHOICES,
        'organizer_users': User.objects.filter(is_staff=False).order_by('username'),
    })


@login_required
@user_passes_test(is_admin)
def contest_delete(request, pk):
    contest = get_object_or_404(Contest, pk=pk)
    if request.method == 'POST':
        title = contest.title
        contest.delete()
        messages.success(request, f'Contest "{title}" deleted.')
        return redirect('admin_panel:contests')
    return render(request, 'admin_panel/contest_confirm_delete.html', {'contest': contest})


@login_required
@user_passes_test(is_admin)
def contest_participants(request, pk):
    contest = get_object_or_404(Contest, pk=pk)
    branch_f = request.GET.get('branch', '')
    year_f = request.GET.get('year', '')
    participant_count = 0
    team_count = 0
    if contest.participation_type == 'solo':
        regs = Registration.objects.filter(contest=contest, team__isnull=True).select_related('user__profile')
        if branch_f:
            regs = regs.filter(user__profile__branch=branch_f)
        if year_f:
            regs = regs.filter(user__profile__year=year_f)
        teams = None
        participant_count = regs.count()
    else:
        teams = Team.objects.filter(contest=contest).prefetch_related('team_members__user__profile')
        regs = None
        team_count = teams.count()
        participant_count = sum(team.team_members.count() for team in teams)
    if 'export' in request.GET:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{contest.title}_participants.csv"'
        writer = csv.writer(response)
        writer.writerow(['Username', 'Full Name', 'Branch', 'Year', 'Team', 'Contest'])
        if regs:
            for r in regs:
                p = getattr(r.user, 'profile', None)
                writer.writerow([r.user.username, r.user.get_full_name(), getattr(p,'branch',''), getattr(p,'year',''), '', contest.title])
        if teams:
            for team in teams:
                for m in team.team_members.all():
                    p = getattr(m.user, 'profile', None)
                    writer.writerow([m.user.username, m.user.get_full_name(), getattr(p,'branch',''), getattr(p,'year',''), team.name, contest.title])
        return response
    return render(request, 'admin_panel/participants.html', {
        'contest': contest, 'regs': regs, 'teams': teams,
        'participant_count': participant_count,
        'team_count': team_count,
        'branches': ALL_BRANCHES, 'years': ALL_YEARS,
        'branch_f': branch_f, 'year_f': year_f,
    })


@login_required
@user_passes_test(is_admin)
def users_list(request):
    users = User.objects.all().select_related('profile').order_by('username')

    role_f = request.GET.get('role', '')
    # Support both old (student/admin) and new (students/admins) role values.
    role_value = {'student': 'students', 'admin': 'admins'}.get(role_f, role_f)
    branch_f = request.GET.get('branch', '')
    year_f = request.GET.get('year', '')
    search = request.GET.get('q', '')

    section_f = request.GET.get('section', '')
    
    if role_value == 'students':
        users = users.filter(is_staff=False)
    elif role_value == 'admins':
        users = users.filter(is_staff=True)

    if branch_f:
        users = users.filter(profile__branch=branch_f)
    if year_f:
        users = users.filter(profile__year=year_f)
    if section_f:
        users = users.filter(profile__section__iexact=section_f)
    if search:
        users = users.filter(Q(username__icontains=search) | Q(first_name__icontains=search))

    total_users = users.count()
    if role_value == 'students':
        count_label = f'Showing {total_users} Students'
    elif role_value == 'admins':
        count_label = f'Showing {total_users} Admins'
    else:
        count_label = f'Showing {total_users} Users'

    from django.core.paginator import Paginator
    page = Paginator(users, 25).get_page(request.GET.get('page', 1))

    return render(request, 'admin_panel/users.html', {
        'users': page, 'branches': ALL_BRANCHES, 'years': ALL_YEARS,
        'role_f': role_value, 'branch_f': branch_f, 'year_f': year_f, 
        'section_f': section_f, 'search': search,
        'total_users': total_users, 'count_label': count_label,
    })


@login_required
@user_passes_test(is_admin)
def toggle_user(request):
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        user = get_object_or_404(User, pk=user_id)
        if user == request.user:
            messages.error(request, 'You cannot deactivate your own account.')
        else:
            user.is_active = not user.is_active
            user.save()
            status = "activated" if user.is_active else "deactivated"
            messages.success(request, f'User {user.username} has been {status}.')
    return redirect('admin_panel:users')


@login_required
@user_passes_test(is_admin)
def delete_user(request):
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        user_to_delete = get_object_or_404(User, pk=user_id)
        
        # Safety Rules
        if user_to_delete == request.user:
            messages.error(request, "You cannot delete your own account.")
            return redirect('admin_panel:users')
            
        if user_to_delete.is_staff:
            messages.error(request, "Admin users cannot be deleted for safety.")
            return redirect('admin_panel:users')
            
        username = user_to_delete.username
        user_to_delete.delete()
        messages.success(request, f"User @{username} has been permanently deleted.")
        
    return redirect('admin_panel:users')


@login_required
@user_passes_test(is_admin)
def users_upload(request):
    results = None
    if request.method == 'POST' and request.FILES.get('csv_file'):
        from accounts.utils import parse_reg_no
        f = request.FILES['csv_file']
        try:
            decoded = f.read().decode('utf-8-sig')
            reader = csv.DictReader(io.StringIO(decoded))
            created, skipped, errors = [], [], []
            for i, row in enumerate(reader, start=2):
                reg_no_raw = (row.get('reg_no') or row.get('username') or '').strip()
                if not reg_no_raw:
                    errors.append(f'Row {i}: missing reg_no')
                    continue
                
                try:
                    data = parse_reg_no(reg_no_raw)
                    username = data['reg_no'] # Use normalized reg_no as username
                except ValueError as e:
                    errors.append(f'Row {i}: {e}')
                    continue

                if User.objects.filter(username=username).exists():
                    skipped.append(username)
                    continue

                # Passwords must be lowercase ONLY while creating
                user = User.objects.create_user(username=username, password=username.lower())
                prof, _ = UserProfile.objects.get_or_create(user=user)
                prof.reg_no = username
                prof.entry_type = data['entry_type']
                prof.branch = data['branch']
                prof.year = data['year']
                prof.department = data['department']
                prof.profile_completed = False
                prof.save()
                created.append(username)
                
            results = {'created': created, 'skipped': skipped, 'errors': errors}
            if created:
                messages.success(request, f'Uploaded: {len(created)} user(s) created.')
            if skipped:
                messages.warning(request, f'{len(skipped)} user(s) already exist and were skipped.')
            if errors:
                for e in errors:
                    messages.error(request, e)
        except Exception as ex:
            messages.error(request, f'Error reading CSV: {ex}')
    return render(request, 'admin_panel/users_upload.html', {'results': results})


@login_required
@user_passes_test(is_admin)
def teams_list(request):
    contest_f = request.GET.get('contest', '')
    teams = Team.objects.select_related('contest', 'leader').annotate(mc=Count('team_members'))
    contests = Contest.objects.all()
    if contest_f:
        teams = teams.filter(contest_id=contest_f)
    return render(request, 'admin_panel/teams.html', {
        'teams': teams, 'contests': contests, 'contest_f': contest_f
    })


@login_required
@user_passes_test(is_admin)
def announcements_view(request):
    items = Announcement.objects.all()
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create':
            text = request.POST.get('text', '').strip()
            if text:
                Announcement.objects.filter(is_active=True).update(is_active=False)
                Announcement.objects.create(text=text, is_active=True)
                messages.success(request, 'Announcement published.')
        elif action == 'toggle':
            ann = get_object_or_404(Announcement, pk=request.POST.get('id'))
            ann.is_active = not ann.is_active
            ann.save()
        elif action == 'delete':
            Announcement.objects.filter(pk=request.POST.get('id')).delete()
        return redirect('admin_panel:announcements')
    return render(request, 'admin_panel/announcements.html', {'items': items})


@login_required
@user_passes_test(is_admin)
def add_admin(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '')
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        phone = request.POST.get('phone', '')
        department = request.POST.get('department', '')
        bio = request.POST.get('bio', '')

        if not username or not password:
            messages.error(request, 'Username and Password are required.')
            return render(request, 'admin_panel/add_admin.html')
        
        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'admin_panel/add_admin.html')
            
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return render(request, 'admin_panel/add_admin.html')

        user = User.objects.create_user(
            username=username, 
            password=password, 
            email=email, 
            first_name=first_name, 
            last_name=last_name
        )
        user.is_staff = True
        user.is_superuser = False
        user.save()

        prof, _ = UserProfile.objects.get_or_create(user=user)
        prof.department = department
        prof.bio = bio
        prof.save()

        messages.success(request, 'Admin account created successfully.')
        return redirect('admin_panel:users')

    return render(request, 'admin_panel/add_admin.html', {'branch_choices': BRANCH_CHOICES})


@login_required
@user_passes_test(is_admin)
def student_profile(request, user_id):
    student = get_object_or_404(User, pk=user_id)
    if student.is_staff:
        messages.info(request, 'Admin profiles are not available on the student profile page.')
        return redirect('admin_panel:users')
    prof = getattr(student, 'profile', None)
    now = timezone.now()
    
    regs = Registration.objects.filter(user=student).select_related('contest').order_by('-created_at')
    teams = TeamMember.objects.filter(user=student).select_related('team', 'team__contest').order_by('-joined_at')
    organized_events = Contest.objects.filter(organizers=student).order_by('-start_date')
    
    return render(request, 'admin_panel/student_profile.html', {
        'student': student,
        'profile': prof,
        'now': now,
        'regs': regs,
        'teams': teams,
        'organized_events': organized_events,
    })


@login_required
@user_passes_test(is_admin)
def reset_student_password(request):
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        student = get_object_or_404(User, pk=user_id)
        new_pw = request.POST.get('new_password', '')
        confirm_pw = request.POST.get('confirm_password', '')
        
        if not new_pw or new_pw != confirm_pw:
            messages.error(request, 'Passwords do not match or are empty.')
        else:
            student.set_password(new_pw)
            student.save()
            messages.success(request, 'Password updated successfully.')
            
    return redirect('admin_panel:users')
