from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Q, Count
from .models import Contest
from registrations.models import Registration
from accounts.models import UserProfile
from accounts.decorators import is_profile_complete
from teams.models import TeamMember


def _derive_contest_status(contest, now):
    status_str = contest.get_status() # "Completed", "Ongoing", "Registration Open", "Registration Closed"
    return status_str.upper().replace(' ', '_')


def _decorate_contest_ui(contest, now):
    status = _derive_contest_status(contest, now)
    contest.ui_status = status
    contest.ui_status_badge = status.replace('_', ' ').title()
    contest.ui_countdown_target = None
    contest.ui_countdown_label = ''

    if status == 'REGISTRATION_OPEN':
        if contest.is_registration_enabled and now > contest.registration_deadline:
            contest.ui_countdown_label = 'Spot Registration Open'
            contest.ui_countdown_target = None
        else:
            contest.ui_countdown_label = 'Registration Ends In'
            contest.ui_countdown_target = contest.registration_deadline
    elif status == 'REGISTRATION_CLOSED':
        contest.ui_countdown_label = 'Contest Starts In'
        contest.ui_countdown_target = contest.start_date
    elif status == 'ONGOING':
        contest.ui_countdown_label = 'Contest Ends In'
        contest.ui_countdown_target = contest.end_date

    return contest


def _next_relevant_contest(contests):
    active = [c for c in contests if c.ui_status != 'COMPLETED']
    if not active:
        return None

    def _milestone(contest):
        if contest.ui_status == 'REGISTRATION_OPEN':
            return contest.registration_deadline
        if contest.ui_status == 'REGISTRATION_CLOSED':
            return contest.start_date
        if contest.ui_status == 'ONGOING':
            return contest.end_date
        return contest.end_date

    return sorted(active, key=_milestone)[0]


def _contest_total_participants(contest):
    """Return participant total with team contests counted by team members, not team count."""
    if contest.participation_type == 'solo':
        return Registration.objects.filter(contest=contest, team__isnull=True).count()

    # For team contests, count all members in teams that are actually registered.
    return TeamMember.objects.filter(
        team__contest=contest,
        team__registrations__contest=contest,
    ).values('id').distinct().count()


def _global_total_participants():
    """Global participants across contest entries.

    Solo contests contribute by registration rows.
    Team contests contribute by total members in registered teams.
    """
    solo_total = Registration.objects.filter(team__isnull=True).count()
    team_total = TeamMember.objects.filter(team__registrations__isnull=False).values('id').distinct().count()
    return solo_total + team_total

def home(request):
    now = timezone.now()
    qs = Contest.objects.annotate(
        participant_count=Count('registrations__user', distinct=True),
        team_count=Count('teams', distinct=True)
    )

    active_contests = [_decorate_contest_ui(c, now) for c in qs.filter(end_date__gte=now)]
    recent_completed = [_decorate_contest_ui(c, now) for c in qs.filter(end_date__lt=now).order_by('-end_date')[:3]]

    # Primary selection priority:
    # 1) spot registration enabled and contest not ended
    # 2) next upcoming by start date
    # 3) most recent active/ended fallback
    primary_contest = qs.filter(is_registration_enabled=True, end_date__gt=now).order_by('start_date').first()
    if not primary_contest:
        primary_contest = qs.filter(start_date__gt=now).order_by('start_date').first()
    if not primary_contest:
        primary_contest = qs.filter(end_date__gte=now).order_by('start_date').first()
    if not primary_contest:
        primary_contest = qs.order_by('-end_date').first()
    if primary_contest:
        _decorate_contest_ui(primary_contest, now)
    primary_total_participants = _contest_total_participants(primary_contest) if primary_contest else 0

    primary_registration_open = bool(primary_contest and primary_contest.is_registration_open(now))
    is_spot_registration_active = bool(
        primary_contest
        and primary_contest.is_registration_enabled
        and now > primary_contest.registration_deadline
        and now < primary_contest.end_date
    )
    is_late_entry_active = bool(
        primary_contest
        and primary_contest.is_registration_enabled
        and now >= primary_contest.start_date
        and now < primary_contest.end_date
    )
    registration_deadline = (
        primary_contest.registration_deadline
        if primary_contest and primary_registration_open and not is_spot_registration_active
        else None
    )

    featured = [c for c in active_contests if c.is_featured][:6]
    ongoing = [c for c in active_contests if c.ui_status == 'ONGOING'][:6]
    upcoming = [c for c in active_contests if c.ui_status in ('REGISTRATION_OPEN', 'REGISTRATION_CLOSED')][:6]

    from teams.models import Team
    active_contests_count = Contest.objects.filter(
        Q(start_date__gt=now) | Q(start_date__lte=now, end_date__gte=now)
    ).count()

    context = {
        'primary_contest': primary_contest,
        'primary_total_participants': primary_total_participants,
        'primary_registration_open': primary_registration_open,
        'is_spot_registration_active': is_spot_registration_active,
        'is_late_entry_active': is_late_entry_active,
        'registration_deadline': registration_deadline,
        'featured': featured,
        'ongoing': ongoing,
        'upcoming': upcoming,
        'recent_completed': recent_completed,
        'total_contests': Contest.objects.count(),
        'total_participants': _global_total_participants(),
        'total_teams_participated': Team.objects.filter(registrations__isnull=False).distinct().count(),
        'active_contests': active_contests_count,
        'now': now,
    }
    return render(request, 'home/index.html', context)


def contest_list(request):
    now = timezone.now()
    contests_qs = Contest.objects.annotate(
        participant_count=Count('registrations__user', distinct=True),
        team_count=Count('teams', distinct=True)
    ).filter(end_date__gte=now)
    q = request.GET.get('q', '')
    category = request.GET.get('category', '')
    ptype = request.GET.get('ptype', '')
    if q:
        contests_qs = contests_qs.filter(Q(title__icontains=q) | Q(category__icontains=q) | Q(venue__icontains=q))
    if category:
        contests_qs = contests_qs.filter(category=category)
    if ptype:
        contests_qs = contests_qs.filter(participation_type=ptype)

    contests = [_decorate_contest_ui(c, now) for c in contests_qs]

    user_reg_ids = []
    if request.user.is_authenticated:
        user_reg_ids = list(Registration.objects.filter(user=request.user).values_list('contest_id', flat=True))
    return render(request, 'contests/list.html', {
        'contests': contests, 'q': q, 'category': category, 'ptype': ptype,
        'user_reg_ids': user_reg_ids,
        'categories': ['Hackathon', 'Coding Contest', 'Workshop'],
    })


def contest_detail(request, pk):
    now = timezone.now()
    contest = get_object_or_404(Contest, pk=pk)
    _decorate_contest_ui(contest, now)

    contest_mode = 'team' if contest.participation_type in ('team', 'both') else 'solo'
    is_registered = False
    is_eligible = False
    user_team = contest.get_user_team(request.user)
    is_team_leader = bool(user_team and user_team.leader_id == request.user.id)
    can_register = contest.is_registration_open()
    profile_complete = False
    profile = None

    if request.user.is_authenticated:
        profile_complete = is_profile_complete(request.user)
        if contest_mode == 'team':
            is_registered = Registration.objects.filter(
                team__team_members__user=request.user,
                contest=contest,
            ).exists()
        else:
            is_registered = Registration.objects.filter(
                user=request.user,
                contest=contest,
                team__isnull=True,
            ).exists()
        try:
            profile = request.user.profile
            is_eligible = contest.is_student_eligible(profile)
        except Exception:
            pass

    return render(request, 'contests/detail.html', {
        'contest': contest, 'is_registered': is_registered,
        'contest_mode': contest_mode,
        'is_eligible': is_eligible, 'user_team': user_team,
        'is_leader': is_team_leader,
        'can_register': can_register,
        'profile_complete': profile_complete,
        'has_ended': contest.has_ended(),
        'profile': profile, 'now': now,
    })


def archive(request):
    now = timezone.now()
    completed = Contest.objects.filter(end_date__lt=now).order_by('-end_date')
    grouped = {}
    for c in completed:
        yr = c.end_date.year
        grouped.setdefault(yr, []).append(c)
    grouped_sorted = sorted(grouped.items(), key=lambda x: x[0], reverse=True)
    return render(request, 'archive/index.html', {'grouped': grouped_sorted, 'total': completed.count()})
