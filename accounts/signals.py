from .utils import (
    generate_student_credentials,
    generate_lecturer_credentials,
    send_new_account_email,
)


def post_save_account_receiver(instance=None, created=False, *args, **kwargs):
    """
    Send email notification
    """
    if created:
        password = None
        if instance.is_student and (not instance.username or instance.username.startswith('ugr-')):
            username, password = generate_student_credentials()
            instance.username = username
            instance.set_password(password)
            instance.save(update_fields=['username', 'password'])
            # Send email with the generated credentials
            send_new_account_email(instance, password)

        elif instance.is_lecturer and (not instance.username or instance.username.startswith('lec-')):
            username, password = generate_lecturer_credentials()
            instance.username = username
            instance.set_password(password)
            instance.save(update_fields=['username', 'password'])
            # Send email with the generated credentials
            send_new_account_email(instance, password)
