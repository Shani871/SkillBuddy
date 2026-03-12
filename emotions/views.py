import json
import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render

from accounts.decorators import role_required
from accounts.models import Parent, Student

from .models import EmotionAlert, EmotionRecord
from .services import EmotionAnalysisService

logger = logging.getLogger(__name__)


@login_required
def capture_emotion(request):
    """Receive webcam image data from authenticated users and record emotion."""
    if request.method != "POST":
        return JsonResponse(
            {"status": "error", "message": "Method not allowed"}, status=405
        )

    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse(
            {"status": "error", "message": "Invalid JSON payload"}, status=400
        )

    image_data = data.get("image")
    if not image_data:
        return JsonResponse(
            {"status": "error", "message": "Image is required"}, status=400
        )

    student = Student.objects.filter(student=request.user).first()
    if not student:
        return JsonResponse(
            {"status": "error", "message": "Only students can submit emotions"},
            status=403,
        )

    try:
        if getattr(settings, "USE_CELERY_EMOTION_ANALYSIS", False):
            try:
                from .tasks import analyze_and_store_emotion_task

                task_result = analyze_and_store_emotion_task.delay(student.id, image_data)
                return JsonResponse(
                    {
                        "status": "success",
                        "analysis": "queued",
                        "task_id": str(getattr(task_result, "id", "")),
                        "emotion": "Neutral",
                        "confidence": 0.0,
                    },
                    status=202,
                )
            except Exception as exc:
                logger.warning(
                    "Could not queue emotion analysis task for user %s: %s. Falling back to sync mode.",
                    request.user.id,
                    exc,
                )

        record = EmotionAnalysisService.analyze_and_store_emotion(student, image_data)
        return JsonResponse(
            {
                "status": "success",
                "analysis": "sync",
                "emotion": record.emotion,
                "confidence": record.confidence,
            }
        )
    except Exception as exc:
        logger.exception("Emotion capture failed for user %s: %s", request.user.id, exc)
        return JsonResponse(
            {"status": "error", "message": "Unable to process emotion data"},
            status=500,
        )


@login_required
@role_required(["lecturer"])
def teacher_dashboard(request):
    """View for teachers to see emotional trends of their students."""
    recent_records = EmotionRecord.objects.select_related("student__student").all()[:50]
    alerts = EmotionAlert.objects.select_related("student__student").filter(
        is_for_teacher=True, is_read=False
    )[:10]

    return render(
        request,
        "emotions/teacher_dashboard.html",
        {
            "recent_records": recent_records,
            "alerts": alerts,
        },
    )


@login_required
@role_required(["parent"])
def parent_dashboard(request):
    """View for parents to see emotional summary of their child."""
    parent = (
        Parent.objects.select_related("student__student")
        .filter(user=request.user)
        .first()
    )
    if not parent or not parent.student:
        return JsonResponse(
            {"status": "error", "message": "Parent profile not found"}, status=403
        )

    student = parent.student

    latest_record = EmotionRecord.objects.select_related("student__student").filter(
        student=student
    ).first()
    alerts = EmotionAlert.objects.select_related("student__student").filter(
        student=student,
        is_for_parent=True,
        is_read=False,
    )

    return render(
        request,
        "emotions/parent_dashboard.html",
        {
            "student": student,
            "latest_record": latest_record,
            "alerts": alerts,
        },
    )
