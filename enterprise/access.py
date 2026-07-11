from functools import wraps
import hashlib

from django.contrib.auth import logout
from django.contrib.auth.backends import ModelBackend
from django.http import HttpResponseForbidden
from django.core.cache import cache

from accounts.models import User


def role_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return HttpResponseForbidden("Authentication required")
            if request.user.effective_role not in roles:
                return HttpResponseForbidden("Your role does not have permission for this operation.")
            return view(request, *args, **kwargs)
        return wrapped
    return decorator


class TenantAwareAuthBackend(ModelBackend):
    max_failures = 5
    lockout_seconds = 15 * 60

    def authenticate(self, request, username=None, password=None, **kwargs):
        login_name = username or kwargs.get(User.USERNAME_FIELD)
        if not login_name:
            return super().authenticate(request, username=username, password=password, **kwargs)
        digest = hashlib.sha256(str(login_name).strip().lower().encode()).hexdigest()
        key = f"skillbuddy:auth-failures:{digest}"
        failures = cache.get(key, 0)
        if failures >= self.max_failures:
            return None
        user = super().authenticate(request, username=username, password=password, **kwargs)
        if user:
            cache.delete(key)
        else:
            cache.set(key, failures + 1, self.lockout_seconds)
        return user

    def user_can_authenticate(self, user):
        if not super().user_can_authenticate(user) or user.login_disabled:
            return False
        return not user.college_id or user.college.status != "suspended"


class TenantAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user and user.is_authenticated and (
            user.login_disabled
            or (user.college_id and user.college.status == "suspended")
        ):
            logout(request)
        return self.get_response(request)


MANAGER_ROLES = (User.ROLE_SUPER_ADMIN, User.ROLE_COLLEGE_ADMIN)
PLACEMENT_ROLES = (User.ROLE_SUPER_ADMIN, User.ROLE_COLLEGE_ADMIN, User.ROLE_PLACEMENT)
REPORT_ROLES = (*MANAGER_ROLES, User.ROLE_PLACEMENT, User.ROLE_HOD)
