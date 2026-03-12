import base64
import logging

import numpy as np
import cv2
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from accounts.models import Parent, User
from result.models import TakenCourse

from .models import EmotionRecord, EmotionAlert

logger = logging.getLogger(__name__)


class EmotionAnalysisService:
    @staticmethod
    def _send_template_email(subject, text_template, html_template, context, recipients):
        """
        Send email with both plaintext and HTML versions.
        """
        if not recipients:
            return 0

        text_body = render_to_string(text_template, context)
        html_body = render_to_string(html_template, context)
        from_email = settings.EMAIL_FROM_ADDRESS or settings.EMAIL_HOST_USER or None

        message = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=from_email,
            to=recipients,
        )
        message.attach_alternative(html_body, "text/html")
        sent = message.send()
        return int(sent or 0)

    @staticmethod
    def _get_teacher_emails_for_student(student):
        """
        Find lecturers assigned to the student's registered courses.
        """
        course_ids = list(
            TakenCourse.objects.filter(student=student)
            .values_list("course_id", flat=True)
            .distinct()
        )
        if not course_ids:
            return []

        lecturer_emails = (
            User.objects.filter(
                is_lecturer=True,
                allocated_lecturer__courses__in=course_ids,
            )
            .exclude(email__isnull=True)
            .exclude(email__exact="")
            .values_list("email", flat=True)
            .distinct()
        )
        return list(lecturer_emails)

    @staticmethod
    def _get_parent_email_for_student(student):
        parent = Parent.objects.select_related("user").filter(student=student).first()
        if not parent:
            return None

        if parent.email:
            return parent.email
        if parent.user and parent.user.email:
            return parent.user.email
        return None

    @staticmethod
    def send_alert_emails(alert):
        """
        Send teacher and/or parent notifications for an emotion alert.
        """
        student = alert.student
        student_name = student.student.get_full_name
        latest_record = EmotionRecord.objects.filter(student=student).first()

        context = {
            "alert": alert,
            "student": student,
            "student_name": student_name,
            "latest_record": latest_record,
            "app_name": "SkillBuddy",
        }

        teacher_sent = 0
        parent_sent = 0

        if alert.is_for_teacher:
            teacher_emails = EmotionAnalysisService._get_teacher_emails_for_student(student)
            if teacher_emails:
                subject = f"[SkillBuddy] Emotional Alert: {student_name}"
                teacher_sent = EmotionAnalysisService._send_template_email(
                    subject=subject,
                    text_template="emails/emotions/teacher_alert.txt",
                    html_template="emails/emotions/teacher_alert.html",
                    context=context,
                    recipients=teacher_emails,
                )
            else:
                logger.info(
                    "No lecturer recipients found for emotion alert %s", alert.id
                )

        if alert.is_for_parent:
            parent_email = EmotionAnalysisService._get_parent_email_for_student(student)
            if parent_email:
                subject = f"[SkillBuddy] Child Well-being Update: {student_name}"
                parent_sent = EmotionAnalysisService._send_template_email(
                    subject=subject,
                    text_template="emails/emotions/parent_alert.txt",
                    html_template="emails/emotions/parent_alert.html",
                    context=context,
                    recipients=[parent_email],
                )
            else:
                logger.info("No parent recipient found for emotion alert %s", alert.id)

        return {
            "teacher_sent": teacher_sent,
            "parent_sent": parent_sent,
        }

    @staticmethod
    def dispatch_alert_notifications(alert_id):
        """
        Queue email notifications with Celery when enabled; otherwise send inline.
        """
        if getattr(settings, "USE_CELERY_EMAIL_NOTIFICATIONS", False):
            try:
                from .tasks import send_emotion_alert_emails

                task_result = send_emotion_alert_emails.delay(alert_id)
                return {"dispatched": "queued", "task_id": str(getattr(task_result, "id", ""))}
            except Exception as exc:
                logger.warning(
                    "Failed to queue emotion email task for alert %s: %s. Falling back to sync send.",
                    alert_id,
                    exc,
                )

        try:
            alert = EmotionAlert.objects.select_related("student__student").get(pk=alert_id)
        except EmotionAlert.DoesNotExist:
            logger.warning("Cannot dispatch emails; alert %s does not exist", alert_id)
            return {"dispatched": "missing_alert"}

        result = EmotionAnalysisService.send_alert_emails(alert)
        return {"dispatched": "sync", **result}

    @staticmethod
    def _normalize_confidence(score):
        """
        Normalize confidence into 0..1 range.
        DeepFace emotion scores are typically percentages (0..100).
        """
        try:
            value = float(score or 0.0)
        except (TypeError, ValueError):
            return 0.0

        if value > 1:
            value = value / 100.0
        return max(0.0, min(1.0, value))

    @classmethod
    def _map_deepface_emotion(cls, dominant_emotion, confidence):
        """
        Map DeepFace labels to EmotionRecord choices.
        """
        emotion = (dominant_emotion or "").strip().lower()
        normalized_confidence = cls._normalize_confidence(confidence)

        if emotion == "happy":
            return "Happy", normalized_confidence
        if emotion == "sad":
            return "Sad", normalized_confidence
        if emotion == "angry":
            if normalized_confidence >= 0.75:
                return "Frustrated", normalized_confidence
            return "Stressed", normalized_confidence
        if emotion == "fear":
            if normalized_confidence >= 0.75:
                return "Anxious", normalized_confidence
            return "Stressed", normalized_confidence
        if emotion == "disgust":
            return "Stressed", normalized_confidence
        if emotion == "neutral":
            if normalized_confidence < 0.45:
                return "Tired", normalized_confidence
            return "Neutral", normalized_confidence

        # Fallback for labels like surprise, unknown, etc.
        return "Neutral", normalized_confidence

    @staticmethod
    def _decode_base64_image(image_data_base64):
        """
        Convert base64-encoded image string to OpenCV image matrix.
        """
        if not image_data_base64:
            raise ValueError("Missing image payload")

        if ";base64," in image_data_base64:
            _, encoded = image_data_base64.split(";base64,", 1)
        else:
            encoded = image_data_base64

        data = base64.b64decode(encoded)
        nparr = np.frombuffer(data, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("Invalid image payload")
        return image

    @staticmethod
    def detect_face_emotion(image_data_base64):
        """
        Analyzes facial expression from base64 image data.
        Returns (emotion_label, confidence)
        """
        try:
            image = EmotionAnalysisService._decode_base64_image(image_data_base64)
        except Exception as exc:
            logger.warning("Image decode failed for emotion detection: %s", exc)
            return "Neutral", 0.0

        try:
            from deepface import DeepFace
        except ImportError:
            logger.info("DeepFace is not installed. Falling back to neutral emotion.")
            return "Neutral", 0.0

        try:
            analysis = DeepFace.analyze(
                img_path=image,
                actions=["emotion"],
                enforce_detection=False,
                detector_backend="opencv",
            )
            if isinstance(analysis, list):
                analysis = analysis[0]

            dominant_emotion = analysis.get("dominant_emotion", "neutral")
            scores = analysis.get("emotion", {}) or {}
            dominant_score = scores.get(dominant_emotion, 0.0)

            mapped_emotion, mapped_confidence = EmotionAnalysisService._map_deepface_emotion(
                dominant_emotion,
                dominant_score,
            )
            return mapped_emotion, mapped_confidence
        except Exception as exc:
            logger.error("Face emotion detection failed: %s", exc)
            return "Neutral", 0.0

    @staticmethod
    def analyze_and_store_emotion(student, image_data_base64):
        """
        Analyze an image and persist an EmotionRecord.
        Ensures a fallback record is still stored if model inference fails.
        """
        emotion_label, confidence = EmotionAnalysisService.detect_face_emotion(
            image_data_base64
        )

        record = EmotionRecord.objects.create(
            student=student,
            emotion=emotion_label,
            confidence=confidence,
            source="face",
        )
        EmotionAnalysisService.create_alerts_if_needed(student)
        return record

    @staticmethod
    def detect_text_sentiment(text):
        """
        Analyzes sentiment from text input.
        Returns (emotion_label, confidence)
        """
        # Placeholder for NLP sentiment analysis
        return "Neutral", 1.0

    @staticmethod
    def calculate_fused_emotion(face_data=None, text_data=None, voice_data=None):
        """
        Weighted fusion of different emotion sources.
        """
        # Weights: Face (60%), Text (20%), Voice (20%)
        # Current implementation only uses face data for login
        if face_data:
            return face_data[0], face_data[1]
        return "Neutral", 1.0

    @staticmethod
    def create_alerts_if_needed(student):
        """
        Checks recent emotion history and generates alerts for teachers/parents
        if negative trends are detected (e.g., 3 days of stress).
        """
        recent_records = EmotionRecord.objects.filter(student=student)[:3]
        if len(recent_records) >= 3:
            stressed_count = sum(
                1
                for r in recent_records
                if r.emotion in ["Stressed", "Sad", "Anxious", "Frustrated"]
            )
            if stressed_count >= 3:
                alert, created = EmotionAlert.objects.get_or_create(
                    student=student,
                    message=f"Student {student} has appeared stressed for 3 consecutive logins. Consider checking in.",
                    is_for_teacher=True,
                    is_for_parent=True,
                    is_read=False,
                )
                if created:
                    EmotionAnalysisService.dispatch_alert_notifications(alert.id)
