from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps

def is_profile_complete(user):
    """
    Helper to check if a student user's profile is complete.
    Admins are always considered complete.
    """
    if not user or not user.is_authenticated:
        return False
    profile = getattr(user, 'profile', None)
    if user.is_staff or getattr(profile, 'role', 'student') == 'admin':
        return True
    if not profile:
        return False

    # Centralized profile-completion gate for participation actions.
    return all([
        bool(user.email),
        bool(profile.phone),
        bool(profile.branch),
        bool(profile.year),
        bool(profile.section),
    ])

def profile_required(view_func):
    """
    Decorator for views that require a complete profile (students only).
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not is_profile_complete(request.user):
            messages.warning(request, "You must complete your profile before participating in contests.")
            return redirect('accounts:profile')
        return view_func(request, *args, **kwargs)
    return _wrapped_view
