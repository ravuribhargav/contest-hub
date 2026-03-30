from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import IntegrityError
from django.db.models import Q
from django.utils import timezone
from django.urls import reverse
from urllib.parse import urlencode
from .models import Team, TeamMember
from .forms import TeamCreateForm
from contests.models import Contest
from registrations.models import Registration
from accounts.decorators import profile_required, is_profile_complete


def _team_is_registered(team):
    return Registration.objects.filter(team=team, contest=team.contest).exists()


@login_required
def my_teams(request):
    memberships = list(TeamMember.objects.filter(user=request.user).select_related('team__contest', 'team__leader'))
    team_ids = [m.team_id for m in memberships]
    registered_team_ids = set(Registration.objects.filter(team_id__in=team_ids).values_list('team_id', flat=True))
    for membership in memberships:
        membership.team_is_registered = membership.team_id in registered_team_ids
    return render(request, 'teams/my_teams.html', {
        'memberships': memberships,
        'now': timezone.now(),
    })


@login_required
@profile_required
def create_team(request, contest_id):
    contest = get_object_or_404(Contest, pk=contest_id)
    if request.user.is_staff:
        return HttpResponseForbidden("Admins cannot participate")
    if contest.participation_type not in ('team', 'both'):
        messages.error(request, 'This contest supports solo registration only.')
        return redirect('contests:detail', pk=contest_id)
    if not contest.is_registration_open():
        messages.error(request, 'Registration is closed.')
        return redirect('contests:detail', pk=contest_id)
    if Registration.objects.filter(user=request.user, contest=contest).exists():
        messages.warning(request, 'You are already registered for this contest.')
        return redirect('contests:detail', pk=contest_id)
    if TeamMember.objects.filter(user=request.user, team__contest=contest).exists():
        messages.warning(request, 'You already have a team for this contest.')
        return redirect('teams:my_teams')
    if request.method == 'POST':
        form = TeamCreateForm(request.POST, contest=contest)
        if form.is_valid():
            team = form.save(commit=False)
            team.contest = contest
            team.leader = request.user
            try:
                team.save()
            except IntegrityError:
                form.add_error('name', 'Team name already exists in this contest.')
            else:
                TeamMember.objects.create(team=team, user=request.user)
                success_msg = f'Team created! Code: {team.team_code}'
                messages.success(request, success_msg)
                target = reverse('teams:detail', kwargs={'pk': team.pk})
                query = urlencode({
                    'success_action': 'team_creation',
                    'success_msg': success_msg,
                    'contest_id': contest.pk,
                    'team_id': team.pk,
                })
                return redirect(f'{target}?{query}')
        messages.error(request, 'Please fix the errors below.')
    else:
        form = TeamCreateForm(contest=contest)

    return render(request, 'teams/create.html', {'contest': contest, 'form': form})


@login_required
@profile_required
def join_team(request):
    if request.user.is_staff:
        return HttpResponseForbidden("Admins cannot participate")
    if request.method == 'POST':
        code = request.POST.get('code', '').strip().upper()
        try:
            team = Team.objects.get(team_code=code)
        except Team.DoesNotExist:
            messages.error(request, 'Invalid team code.')
            return redirect('teams:join')

        if _team_is_registered(team):
            messages.error(request, 'This team is already registered and locked')
            return redirect('contests:detail', pk=team.contest.pk)
        if TeamMember.objects.filter(team=team, user=request.user).exists():
            messages.error(request, 'You are already in this team')
            return redirect('contests:detail', pk=team.contest.pk)
        if team.member_count() >= team.contest.team_size_max:
            messages.error(request, 'Team is full')
            return redirect('contests:detail', pk=team.contest.pk)
        if not team.contest.is_registration_open():
            messages.error(request, 'Registration is closed.')
            return redirect('contests:detail', pk=team.contest.pk)
        if team.contest.participation_type not in ('team', 'both'):
            messages.error(request, 'This contest does not allow team registration.')
            return redirect('contests:detail', pk=team.contest.pk)
        if Registration.objects.filter(user=request.user, contest=team.contest).exists():
            messages.warning(request, 'You are already registered for this contest.')
            return redirect('contests:detail', pk=team.contest.pk)
        if TeamMember.objects.filter(user=request.user, team__contest=team.contest).exists():
            messages.warning(request, 'You already belong to a team for this contest.')
            return redirect('teams:my_teams')
        TeamMember.objects.create(team=team, user=request.user)
        success_msg = f'Joined team "{team.name}"!'
        messages.success(request, success_msg)
        target = reverse('teams:detail', kwargs={'pk': team.pk})
        query = urlencode({
            'success_action': 'join_team',
            'success_msg': success_msg,
            'contest_id': team.contest.pk,
            'team_id': team.pk,
        })
        return redirect(f'{target}?{query}')
    return render(request, 'teams/join.html')


@login_required
def team_detail(request, pk):
    team = get_object_or_404(Team, pk=pk)
    is_leader = team.leader == request.user
    is_member = TeamMember.objects.filter(team=team, user=request.user).exists()
    if not is_member and not is_leader:
        messages.error(request, 'You do not have access to this team.')
        return redirect('teams:my_teams')
    is_registered = _team_is_registered(team)
    print("Team:", team.id)
    print("Is Registered:", is_registered)
    profile_complete = is_profile_complete(request.user)
    now = timezone.now()
    can_register_team = is_leader and profile_complete and not is_registered and team.contest.is_registration_open()
    can_unregister_team = is_leader and is_registered and now < team.contest.start_date

    return render(request, 'teams/detail.html', {
        'team': team, 'members': team.members(),
        'is_leader': is_leader, 'is_member': is_member,
        'is_registered': is_registered,
        'profile_complete': profile_complete,
        'can_register_team': can_register_team,
        'can_unregister_team': can_unregister_team,
        'now': now,
    })


@login_required
def remove_member(request, pk, user_id):
    team = get_object_or_404(Team, pk=pk)
    if request.method != 'POST':
        return redirect('teams:detail', pk=pk)
    if request.user != team.leader:
        messages.error(request, 'Only leader can remove members.')
        return redirect('teams:detail', pk=pk)
    if _team_is_registered(team):
        messages.error(request, 'Locked teams cannot be modified.')
        return redirect('teams:detail', pk=pk)

    member = get_object_or_404(TeamMember, team=team, user_id=user_id)
    if member.user_id == team.leader_id:
        messages.error(request, 'Leader cannot remove self')
        return redirect('teams:detail', pk=pk)

    member.delete()
    messages.success(request, 'Member removed successfully.')
    return redirect('teams:detail', pk=pk)


@login_required
def unregister_team(request, pk):
    if request.user.is_staff:
        return HttpResponseForbidden("Admins cannot participate")
    team = get_object_or_404(Team, pk=pk)
    contest = team.contest
    now = timezone.now()

    if request.user != team.leader:
        messages.error(request, 'Only leader can unregister team.')
        return redirect('teams:my_teams')
    if now > contest.start_date:
        messages.error(request, 'Cannot unregister after contest starts.')
        return redirect('teams:my_teams')

    if not _team_is_registered(team):
        messages.warning(request, 'Team is already unregistered.')
        return redirect('teams:my_teams')

    Registration.objects.filter(team=team, contest=contest).delete()
    team.is_locked = False
    team.save(update_fields=['is_locked'])

    messages.success(request, 'Team unregistered successfully.')
    return redirect('teams:my_teams')


@login_required
def leave_team(request, pk):
    if request.user.is_staff:
        return HttpResponseForbidden("Admins cannot participate")
    team = get_object_or_404(Team, pk=pk)
    if team.leader == request.user:
        messages.error(request, 'Leader cannot leave. Delete the team instead.')
        return redirect('teams:detail', pk=pk)
    if _team_is_registered(team):
        messages.error(request, 'Locked teams cannot be modified.')
        return redirect('teams:detail', pk=pk)

    if not team.contest.is_registration_open():
        messages.error(request, 'Registration period has ended.')
        return redirect('teams:detail', pk=pk)
    
    if request.method == 'GET':
        return render(request, 'teams/leave_confirm.html', {'team': team})
    
    TeamMember.objects.filter(team=team, user=request.user).delete()
    messages.success(request, 'You have left the team.')
    return redirect('teams:my_teams')


@login_required
def delete_team(request, pk):
    if request.user.is_staff:
        return HttpResponseForbidden("Admins cannot participate")
    team = get_object_or_404(Team, pk=pk, leader=request.user)
    if _team_is_registered(team):
        messages.error(request, 'Locked teams cannot be deleted.')
        return redirect('teams:detail', pk=pk)

    if not team.contest.is_registration_open():
        messages.error(request, 'Registration period has ended.')
        return redirect('teams:detail', pk=pk)
    
    if request.method == 'GET':
        return render(request, 'teams/delete_confirm.html', {'team': team})
    
    # Delete all registrations associated with this team
    Registration.objects.filter(team=team).delete()
    team.delete()
    messages.success(request, 'Team deleted.')
    return redirect('teams:my_teams')


@login_required
@profile_required
def register_team(request, pk):
    if request.user.is_staff:
        return HttpResponseForbidden("Admins cannot participate")
    team = get_object_or_404(Team, pk=pk)
    if request.user != team.leader:
        messages.error(request, 'Only the team leader can register the team.')
        return redirect('teams:detail', pk=team.pk)
    if team.contest.participation_type not in ('team', 'both'):
        messages.error(request, 'This contest does not allow team registration.')
        return redirect('contests:detail', pk=team.contest.pk)
    if not team.contest.is_registration_open():
        messages.error(request, 'Registration period has ended.')
        return redirect('teams:detail', pk=pk)
    if _team_is_registered(team):
        messages.warning(request, 'Your team is already registered for this contest.')
        return redirect('teams:detail', pk=pk)
    member_ids = TeamMember.objects.filter(team=team).values_list('user_id', flat=True)
    if Registration.objects.filter(contest=team.contest, user_id__in=member_ids, team__isnull=True).exists():
        messages.error(request, 'One or more team members already have a solo registration for this contest.')
        return redirect('teams:detail', pk=pk)
    if not team.can_register():
        messages.error(request, f'Need at least {team.contest.team_size_min} members.')
        return redirect('teams:detail', pk=pk)

    # Team contests use a single team-linked registration record.
    registration, created = Registration.objects.get_or_create(
        contest=team.contest,
        team=team,
        defaults={'user': team.leader},
    )
    if not team.is_locked:
        team.is_locked = True
        team.save(update_fields=['is_locked'])
    if created:
        messages.success(request, f'Team registered for {team.contest.title}!')
    else:
        messages.warning(request, 'Your team is already registered for this contest.')
    return redirect('teams:detail', pk=pk)
