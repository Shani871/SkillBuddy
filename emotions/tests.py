import json
from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.conf import settings
from django.core import mail
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import Parent, Student, User
from course.models import Course, CourseAllocation, Program
from result.models import TakenCourse

from .models import EmotionAlert, EmotionRecord
from .tasks import send_emotion_alert_emails
from .services import EmotionAnalysisService


@override_settings(
    STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage",
    LANGUAGE_CODE="en",
    USE_CELERY_EMAIL_NOTIFICATIONS=False,
)
class EmotionViewsAndServiceTests(TestCase):
    def setUp(self):
        self.program = Program.objects.create(title="Computer Science")

        self.student_user = User.objects.create_user(
            username="emotion_student",
            password="password",
            is_student=True,
        )
        self.student = Student.objects.create(
            student=self.student_user,
            level=settings.BACHELOR_DEGREE,
            program=self.program,
        )

        self.lecturer = User.objects.create_user(
            username="emotion_lecturer",
            password="password",
            is_lecturer=True,
            email="lecturer@example.com",
        )
        self.parent_user = User.objects.create_user(
            username="emotion_parent",
            password="password",
            is_parent=True,
            email="parent_user@example.com",
        )
        self.parent = Parent.objects.create(
            user=self.parent_user,
            student=self.student,
            first_name="Parent",
            last_name="One",
            relation_ship="Father",
            email="parent@example.com",
        )
        self.course = Course.objects.create(
            title="Data Structures",
            code="CSC301",
            credit=3,
            summary="Data structures",
            program=self.program,
            level=settings.BACHELOR_DEGREE,
            year=3,
            semester=settings.FIRST,
        )
        allocation = CourseAllocation.objects.create(lecturer=self.lecturer)
        allocation.courses.add(self.course)
        TakenCourse.objects.create(student=self.student, course=self.course)

    def test_capture_emotion_rejects_non_post(self):
        self.client.force_login(self.student_user)
        response = self.client.get(reverse("capture_emotion"))

        self.assertEqual(response.status_code, 405)

    def test_capture_emotion_rejects_non_student_user(self):
        self.client.force_login(self.lecturer)
        response = self.client.post(
            reverse("capture_emotion"),
            data=json.dumps({"image": "data:image/png;base64,abc"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["message"], "Only students can submit emotions")

    @patch("emotions.views.EmotionAnalysisService.create_alerts_if_needed")
    @patch(
        "emotions.views.EmotionAnalysisService.detect_face_emotion",
        return_value=("Happy", 0.91),
    )
    def test_capture_emotion_creates_record_for_student(
        self,
        _mock_detect,
        mock_create_alerts,
    ):
        self.client.force_login(self.student_user)
        response = self.client.post(
            reverse("capture_emotion"),
            data=json.dumps({"image": "data:image/png;base64,abc"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["emotion"], "Happy")
        self.assertEqual(EmotionRecord.objects.filter(student=self.student).count(), 1)
        mock_create_alerts.assert_called_once_with(self.student)

    def test_create_alerts_if_needed_does_not_duplicate_existing_alert(self):
        EmotionRecord.objects.create(student=self.student, emotion="Stressed", confidence=0.8)
        EmotionRecord.objects.create(student=self.student, emotion="Sad", confidence=0.7)
        EmotionRecord.objects.create(student=self.student, emotion="Anxious", confidence=0.9)

        EmotionAnalysisService.create_alerts_if_needed(self.student)
        EmotionAnalysisService.create_alerts_if_needed(self.student)

        self.assertEqual(EmotionAlert.objects.filter(student=self.student).count(), 1)

    def test_teacher_dashboard_allows_lecturer(self):
        EmotionRecord.objects.create(student=self.student, emotion="Neutral", confidence=0.6)
        self.client.force_login(self.lecturer)

        response = self.client.get(reverse("teacher_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "emotions/teacher_dashboard.html")

    def test_parent_dashboard_returns_403_without_parent_profile(self):
        orphan_parent = User.objects.create_user(
            username="no_parent_profile",
            password="password",
            is_parent=True,
        )
        self.client.force_login(orphan_parent)

        response = self.client.get(reverse("parent_dashboard"))

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["message"], "Parent profile not found")

    def test_parent_dashboard_shows_latest_record_for_linked_parent(self):
        EmotionRecord.objects.create(student=self.student, emotion="Tired", confidence=0.55)
        EmotionAlert.objects.create(
            student=self.student,
            message="Check in with your child.",
            is_for_parent=True,
            is_for_teacher=False,
        )
        self.client.force_login(self.parent_user)

        response = self.client.get(reverse("parent_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "emotions/parent_dashboard.html")
        self.assertEqual(response.context["student"], self.student)
        self.assertEqual(response.context["latest_record"].emotion, "Tired")

    def test_deepface_mapping_for_angry_high_confidence_returns_frustrated(self):
        emotion, confidence = EmotionAnalysisService._map_deepface_emotion("angry", 90)
        self.assertEqual(emotion, "Frustrated")
        self.assertEqual(confidence, 0.9)

    def test_deepface_mapping_for_neutral_low_confidence_returns_tired(self):
        emotion, confidence = EmotionAnalysisService._map_deepface_emotion("neutral", 0.3)
        self.assertEqual(emotion, "Tired")
        self.assertEqual(confidence, 0.3)

    @patch(
        "emotions.services.EmotionAnalysisService.detect_face_emotion",
        return_value=("Neutral", 0.0),
    )
    def test_analyze_and_store_emotion_always_persists_record(self, _mock_detect):
        record = EmotionAnalysisService.analyze_and_store_emotion(
            self.student,
            "data:image/png;base64,abc",
        )
        self.assertIsNotNone(record.id)
        self.assertEqual(record.emotion, "Neutral")
        self.assertEqual(record.confidence, 0.0)

    def test_create_alerts_if_needed_sends_teacher_and_parent_emails(self):
        EmotionRecord.objects.create(student=self.student, emotion="Stressed", confidence=0.9)
        EmotionRecord.objects.create(student=self.student, emotion="Sad", confidence=0.8)
        EmotionRecord.objects.create(student=self.student, emotion="Anxious", confidence=0.85)

        EmotionAnalysisService.create_alerts_if_needed(self.student)

        self.assertEqual(EmotionAlert.objects.filter(student=self.student).count(), 1)
        self.assertEqual(len(mail.outbox), 2)
        recipients = [tuple(msg.to) for msg in mail.outbox]
        self.assertIn(("lecturer@example.com",), recipients)
        self.assertIn(("parent@example.com",), recipients)

    def test_send_emotion_alert_emails_task_sends_notifications(self):
        alert = EmotionAlert.objects.create(
            student=self.student,
            message="Student may need support.",
            is_for_teacher=True,
            is_for_parent=True,
        )

        result = send_emotion_alert_emails(alert.id)

        self.assertEqual(result["status"], "ok")
        self.assertEqual(len(mail.outbox), 2)

    def test_resend_unread_alerts_command_sends_only_old_unread(self):
        old_alert = EmotionAlert.objects.create(
            student=self.student,
            message="Old alert",
            is_for_teacher=True,
            is_for_parent=True,
            is_read=False,
        )
        EmotionAlert.objects.filter(pk=old_alert.pk).update(
            timestamp=timezone.now() - timedelta(hours=25)
        )

        EmotionAlert.objects.create(
            student=self.student,
            message="Recent alert",
            is_for_teacher=True,
            is_for_parent=True,
            is_read=False,
        )

        out = StringIO()
        call_command("resend_unread_alerts", stdout=out)

        # Old alert sends two emails (teacher + parent), recent alert is skipped.
        self.assertEqual(len(mail.outbox), 2)
        output = out.getvalue()
        self.assertIn("Processed 1 alert(s).", output)
        self.assertIn("Found 1 unread alert(s) older than 24 hour(s).", output)

    def test_resend_unread_alerts_dry_run_does_not_send(self):
        alert = EmotionAlert.objects.create(
            student=self.student,
            message="Old alert",
            is_for_teacher=True,
            is_for_parent=True,
            is_read=False,
        )
        EmotionAlert.objects.filter(pk=alert.pk).update(
            timestamp=timezone.now() - timedelta(hours=25)
        )

        out = StringIO()
        call_command("resend_unread_alerts", "--dry-run", stdout=out)

        self.assertEqual(len(mail.outbox), 0)
        output = out.getvalue()
        self.assertIn("[DRY RUN] Would resend alert", output)
