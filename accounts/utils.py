import logging
from datetime import datetime
from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags


logger = logging.getLogger(__name__)


def generate_password():
    return get_user_model().objects.make_random_password()


def generate_student_id():
    registered_year = datetime.now().strftime("%Y")
    prefix = f"{settings.STUDENT_ID_PREFIX}-{registered_year}-"
    return _next_available_username(prefix)


def generate_lecturer_id():
    registered_year = datetime.now().strftime("%Y")
    prefix = f"{settings.LECTURER_ID_PREFIX}-{registered_year}-"
    return _next_available_username(prefix)


def _next_available_username(prefix):
    """Return the first unused numeric ID, even when earlier users were deleted."""
    usernames = get_user_model().objects.filter(
        username__startswith=prefix
    ).values_list("username", flat=True)
    used_numbers = set()
    for username in usernames:
        suffix = username.removeprefix(prefix)
        if suffix.isdigit():
            used_numbers.add(int(suffix))

    number = 0
    while number in used_numbers:
        number += 1
    return f"{prefix}{number}"


def generate_student_credentials():
    return generate_student_id(), generate_password()


def generate_lecturer_credentials():
    return generate_lecturer_id(), generate_password()


def send_new_account_email(user, password, login_url):
    """Send the one-time credential message after an account has been saved.

    The raw password is used only to render this message. It is never persisted;
    Django stores only the password hash on ``user``.
    """
    if user.is_student:
        template_name = "accounts/email/new_student_account_confirmation.html"
    else:
        template_name = "accounts/email/new_lecturer_account_confirmation.html"

    context = {"user": user, "password": password, "login_url": login_url}
    html_body = render_to_string(template_name, context)
    message = EmailMultiAlternatives(
        subject="Your Account Login Credentials",
        body=strip_tags(html_body),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )
    message.attach_alternative(html_body, "text/html")

    try:
        message.send(fail_silently=False)
    except Exception:
        logger.exception(
            "Failed to send initial login credentials for user_id=%s", user.pk
        )
        raise
