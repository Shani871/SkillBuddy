from .models import NewsAndEvents


def latest_announcement(request):
    """Expose the newest published item to admin, student, and lecturer pages."""
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {}
    if not (user.is_superuser or user.is_student or user.is_lecturer):
        return {}
    return {
        "latest_announcement": NewsAndEvents.objects.order_by(
            "-upload_time", "-pk"
        ).first()
    }
