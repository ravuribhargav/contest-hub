from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib import messages
from django.urls import reverse
from urllib.parse import urlencode
from .models import UserProfile, BRANCH_CHOICES, YEAR_CHOICES


def login_view(request):
    if request.user.is_authenticated:
        return redirect('contests:home')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username', '').lower()
            password = form.cleaned_data.get('password')
            from django.contrib.auth import authenticate
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                if not user.is_active:
                    messages.error(request, 'Your account has been deactivated.')
                    return render(request, 'accounts/login.html', {'form': form})
                login(request, user)
                prof, _ = UserProfile.objects.get_or_create(user=user)
                
                # Role-based redirect logic
                next_url = request.GET.get('next')
                if next_url:
                    return redirect(next_url)
                
                if user.is_staff or prof.role == 'admin':
                    return redirect('contests:home')
                
                if not prof.is_complete():
                    messages.info(request, "Please complete your profile details.")
                    return redirect('accounts:profile')
                
                return redirect('accounts:student_dashboard')
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = AuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('contests:home')


@login_required
def profile(request):
    prof, _ = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        if 'remove_profile_picture' in request.POST:
            if prof.profile_picture:
                prof.profile_picture.delete(save=True)
                prof.profile_picture = None
                prof.save()
                messages.success(request, 'Profile picture removed successfully.')
            target = reverse('accounts:profile')
            query = urlencode({'success_action': 'profile_update', 'success_msg': 'Profile picture removed successfully.'})
            return redirect(f'{target}?{query}')
            
        request.user.first_name = request.POST.get('first_name', '')
        request.user.last_name = request.POST.get('last_name', '')
        email = request.POST.get('email', '')
        request.user.email = email
        request.user.save()
        
        if request.user.is_staff:
            prof.department = request.POST.get('department', '')
            prof.bio = request.POST.get('bio', '')
        else:
            prof.branch = request.POST.get('branch', '')
            y = request.POST.get('year', '')
            prof.year = int(y) if y else None
            
        if 'profile_picture' in request.FILES:
            prof.profile_picture = request.FILES['profile_picture']
            
        phone = request.POST.get('phone', '')
        section = request.POST.get('section', '')
        prof.phone = phone
        prof.section = section.upper() if section else ''
        
        # Check for completion using the model method
        if not (request.user.is_staff or prof.role == 'admin'):
            if prof.is_complete():
                if not prof.profile_completed:
                    prof.profile_completed = True
                    messages.success(request, "Profile completed! You can now participate in contests.")
                else:
                    messages.success(request, 'Profile updated.')
            else:
                prof.profile_completed = False
                messages.warning(request, "Please complete your profile to participate in contests.")
        else:
            # Admins don't need completion check
            messages.success(request, 'Profile updated.')
            
        prof.save()
        target = reverse('accounts:profile')
        return redirect(target)

    return render(request, 'accounts/profile.html', {
        'profile': prof, 'branches': BRANCH_CHOICES, 'years': YEAR_CHOICES
    })


@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            update_session_auth_hash(request, form.save())
            messages.success(request, 'Password changed.')
            return redirect('accounts:profile')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'accounts/change_password.html', {'form': form})


@login_required
def student_dashboard(request):
    if request.user.is_staff:
        return redirect('admin_panel:contests')
    
    from django.utils import timezone
    from contests.models import Contest
    from registrations.models import Registration
    from teams.models import Team
    from announcements.models import Announcement
    
    now = timezone.now()
    upcoming_contest = Contest.objects.filter(start_date__gt=now).order_by('start_date').first()
    
    # Deduplicate registrations and teams by contest (Option C logic)
    unique_contests = {}
    
    # 1. Start with solo registrations
    solo_regs = Registration.objects.filter(user=request.user).select_related('contest')
    for r in solo_regs:
        unique_contests[r.contest_id] = {
            'is_team': False,
            'contest': r.contest,
            'created_at': r.created_at,
            'id': r.id
        }
    
    # 2. Layer team memberships (prioritize team over solo)
    user_teams = Team.objects.filter(team_members__user=request.user).select_related('contest')
    for t in user_teams:
        unique_contests[t.contest_id] = {
            'is_team': True,
            'contest': t.contest,
            'created_at': t.created_at,
            'team_name': t.name,
            'id': t.id
        }
    
    # Convert to sorted list
    combined_regs = sorted(unique_contests.values(), key=lambda x: x['created_at'], reverse=True)
    registration_count = len(combined_regs)
    
    organized_events = request.user.organized_contests.all().order_by('-start_date')
    announcements = Announcement.objects.filter(is_active=True).order_by('-created_at')[:5]
    
    return render(request, 'accounts/dashboard.html', {
        'now': now,
        'upcoming_contest': upcoming_contest,
        'registrations': combined_regs,
        'registration_count': registration_count,
        'teams': user_teams,
        'team_count': user_teams.count(),
        'organized_events': organized_events,
        'announcements': announcements,
    })


