import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render

from accounts.models import Student

from .models import EmotionAlert, EmotionRecord
from .services import EmotionAnalysisService


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
        emotion_label, confidence = EmotionAnalysisService.detect_face_emotion(image_data)

        EmotionRecord.objects.create(
            student=student,
            emotion=emotion_label,
            confidence=confidence,
            source="face",
        )

        EmotionAnalysisService.create_alerts_if_needed(student)

        return JsonResponse(
            {
                "status": "success",
                "emotion": emotion_label,
                "confidence": confidence,
            }
        )
    except Exception:
        return JsonResponse(
            {"status": "error", "message": "Unable to process emotion data"},
            status=500,
        )


@login_required
def teacher_dashboard(request):
    """View for teachers to see emotional trends of their students."""
    if not request.user.is_lecturer and not request.user.is_superuser:
        return JsonResponse({"status": "error", "message": "Access denied"}, status=403)

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
def parent_dashboard(request):
    """View for parents to see emotional summary of their child."""
    if not request.user.is_parent:
        return JsonResponse({"status": "error", "message": "Access denied"}, status=403)

    parent = getattr(request.user, "parent", None)
    if not parent:
        return JsonResponse(
            {"status": "error", "message": "Parent profile not found"}, status=403
        )

    student = parent.student

    latest_record = EmotionRecord.objects.filter(student=student).first()
    alerts = EmotionAlert.objects.filter(
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
