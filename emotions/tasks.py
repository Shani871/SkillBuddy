import logging

try:
    from celery import shared_task
except ImportError:  # pragma: no cover
    def shared_task(func=None, *args, **kwargs):
        def decorator(f):
            f.delay = f
            return f

        if func is not None and callable(func):
            return decorator(func)
        return decorator

from accounts.models import Student
from .models import EmotionAlert
from .services import EmotionAnalysisService

logger = logging.getLogger(__name__)


@shared_task
def analyze_and_store_emotion_task(student_id, image_data_base64):
    """
    Background task for facial emotion analysis and record storage.
    """
    try:
        student = Student.objects.select_related("student").get(pk=student_id)
    except Student.DoesNotExist:
        logger.warning("Emotion analysis task received invalid student id: %s", student_id)
        return {"status": "error", "message": "student_not_found"}

    record = EmotionAnalysisService.analyze_and_store_emotion(
        student,
        image_data_base64,
    )
    return {
        "status": "ok",
        "record_id": record.id,
        "emotion": record.emotion,
        "confidence": float(record.confidence),
    }


@shared_task
def send_emotion_alert_emails(alert_id):
    """
    Background task for sending emotion alert notifications.
    """
    try:
        alert = EmotionAlert.objects.select_related("student__student").get(pk=alert_id)
    except EmotionAlert.DoesNotExist:
        logger.warning("Email task received invalid alert id: %s", alert_id)
        return {"status": "error", "message": "alert_not_found"}

    result = EmotionAnalysisService.send_alert_emails(alert)
    return {"status": "ok", **result}
