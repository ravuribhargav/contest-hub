from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from django.urls import reverse
from urllib.parse import urlencode
from .models import Registration
from contests.models import Contest
from accounts.models import UserProfile
from accounts.decorators import profile_required


@login_required
def my_registrations(request):
    # Get all potential registrations (solo or via team)
    regs_qs = Registration.objects.filter(
        Q(user=request.user) | Q(team__team_members__user=request.user)
    ).select_related('contest', 'team', 'team__leader').distinct().order_by('-created_at')

    # Deduplicate by contest, prioritizing team registrations
    unique_regs = {}
    for r in regs_qs:
        cid = r.contest_id
        if cid not in unique_regs:
            unique_regs[cid] = r
        else:
            # If current is team and existing is solo, replace
            if r.team and not unique_regs[cid].team:
                unique_regs[cid] = r

    # Convert back to list and sort
    final_regs = sorted(unique_regs.values(), key=lambda x: x.created_at, reverse=True)

    return render(request, 'registrations/my_registrations.html', {
        'registrations': final_regs,
        'now': timezone.now(),
    })


@login_required
@profile_required
def register_solo(request, contest_id):
    contest = get_object_or_404(Contest, pk=contest_id)
    now = timezone.now()
    if request.user.is_staff:
        return HttpResponseForbidden("Admins cannot participate")
    if not contest.is_registration_open(now):
        messages.error(request, 'Registration is closed.')
        return redirect('contests:detail', pk=contest_id)
    if contest.participation_type in ('team', 'both'):
        messages.info(request, 'This is a team contest.')
        return redirect('teams:create', contest_id=contest_id)
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        messages.error(request, 'Complete your profile first.')
        return redirect('accounts:profile')
    if not contest.is_student_eligible(profile):
        messages.error(request, 'You are not eligible for this contest.')
        return redirect('contests:detail', pk=contest_id)
    if Registration.objects.filter(
        Q(user=request.user, contest=contest) | Q(team__team_members__user=request.user, contest=contest)
    ).exists():
        messages.warning(request, 'Already registered.')
        return redirect('contests:detail', pk=contest_id)
    Registration.objects.create(user=request.user, contest=contest)
    success_msg = f'Registered for {contest.title}!'
    messages.success(request, success_msg)
    target = reverse('registrations:my_registrations')
    query = urlencode({'success_action': 'registration', 'success_msg': success_msg})
    return redirect(f'{target}?{query}')


@login_required
def unregister_contest(request, registration_id):
    registration = get_object_or_404(
        Registration,
        id=registration_id,
        user=request.user
    )

    if registration.team:
        messages.info(request, 'Team contest registrations can only be managed from the team page.')
        return redirect("registrations:my_registrations")

    if request.user.is_staff:
        return HttpResponseForbidden("Admins cannot participate")

    if not registration.contest.is_registration_open(timezone.now()):
        messages.error(request, 'Registration period has ended.')
        return redirect("registrations:my_registrations")

    if request.method == 'POST':
        registration.delete()
        messages.success(request, 'Successfully unregistered from the contest.')
        return redirect("registrations:my_registrations")

    return render(request, 'registrations/unregister_confirm.html', {'registration': registration})
