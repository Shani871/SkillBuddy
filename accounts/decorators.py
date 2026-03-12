from functools import wraps

from django.shortcuts import redirect


ROLE_FLAG_MAP = {
    "admin": "is_superuser",
    "student": "is_student",
    "lecturer": "is_lecturer",
    "parent": "is_parent",
    "dep_head": "is_dep_head",
}


def admin_required(function=None, redirect_to="/"):
    """Allow only active superusers."""

    def test_func(user):
        return user.is_active and user.is_superuser

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if test_func(request.user):
                return view_func(request, *args, **kwargs)
            return redirect(redirect_to)

        return wrapper

    if function and callable(function):
        return decorator(function)
    return decorator


def lecturer_required(function=None, redirect_to="/"):
    """Allow active lecturers and superusers."""

    def test_func(user):
        return user.is_active and (user.is_lecturer or user.is_superuser)

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if test_func(request.user):
                return view_func(request, *args, **kwargs)
            return redirect(redirect_to)

        return wrapper

    if function and callable(function):
        return decorator(function)
    return decorator


def student_required(function=None, redirect_to="/"):
    """Allow active students and superusers."""

    def test_func(user):
        return user.is_active and (user.is_student or user.is_superuser)

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if test_func(request.user):
                return view_func(request, *args, **kwargs)
            return redirect(redirect_to)

        return wrapper

    if function and callable(function):
        return decorator(function)
    return decorator


def role_required(allowed_roles, redirect_to="/"):
    """Allow access only to users matching any allowed role.

    Example:
        @role_required(["student", "lecturer"])
    """

    normalized_roles = {role.strip().lower() for role in allowed_roles}
    invalid_roles = normalized_roles - set(ROLE_FLAG_MAP.keys())
    if invalid_roles:
        raise ValueError(f"Invalid role(s) in role_required: {sorted(invalid_roles)}")

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            user = request.user
            if not user.is_authenticated or not user.is_active:
                return redirect(redirect_to)

            if user.is_superuser:
                return view_func(request, *args, **kwargs)

            for role in normalized_roles:
                if getattr(user, ROLE_FLAG_MAP[role], False):
                    return view_func(request, *args, **kwargs)

            return redirect(redirect_to)

        return wrapper

    return decorator
