from datetime import time, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Student
from course.models import AcademicEvent, ClassSchedule, Course, Program
from result.models import CourseAttendance, TakenCourse


User = get_user_model()


class StudentAcademicDashboardTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="student-dashboard", password="password", is_student=True
        )
        self.student = Student.objects.create(
            student=self.user, level="Bachelor", program=Program.objects.create(title="MCA")
        )
        self.faculty = User.objects.create_user(
            username="faculty-dashboard", is_lecturer=True
        )
        self.course = Course.objects.create(
            title="Algorithms", code="ALG-101", program=self.student.program,
            level="Bachelor", semester="First", year=1,
        )
        self.other_course = Course.objects.create(
            title="Private Course", code="PVT-101", program=self.student.program,
            level="Bachelor", semester="First", year=1,
        )
        self.enrollment = TakenCourse.objects.create(
            student=self.student, course=self.course
        )
        CourseAttendance.objects.create(
            enrollment=self.enrollment, total_classes=20, classes_attended=14
        )
        ClassSchedule.objects.create(
            course=self.course, faculty=self.faculty, day_of_week=0,
            start_time=time(9), end_time=time(10), classroom="Room 12",
        )
        ClassSchedule.objects.create(
            course=self.other_course, faculty=self.faculty, day_of_week=0,
            start_time=time(11), end_time=time(12), classroom="Hidden Room",
        )
        AcademicEvent.objects.create(
            title="Algorithms Exam", event_type=AcademicEvent.EXAM,
            start_at=timezone.now() + timedelta(days=1), course=self.course,
        )
        AcademicEvent.objects.create(
            title="Private Exam", event_type=AcademicEvent.EXAM,
            start_at=timezone.now() + timedelta(days=1), course=self.other_course,
        )
        self.client.force_login(self.user)

    def test_schedule_only_contains_enrolled_courses(self):
        response = self.client.get(reverse("student_schedule"), {"view": "week"})
        self.assertContains(response, "Algorithms")
        self.assertNotContains(response, "Private Course")

    def test_attendance_displays_counts_and_warning(self):
        response = self.client.get(reverse("student_attendance"))
        self.assertContains(response, "70.0%")
        self.assertContains(response, "below the required percentage")

    def test_calendar_only_contains_relevant_events(self):
        event_date = (timezone.localdate() + timedelta(days=1)).isoformat()
        response = self.client.get(
            reverse("student_calendar"), {"view": "day", "date": event_date}
        )
        self.assertContains(response, "Algorithms Exam")
        self.assertNotContains(response, "Private Exam")

    def test_non_student_is_redirected(self):
        self.client.force_login(self.faculty)
        response = self.client.get(reverse("student_attendance"))
        self.assertEqual(response.status_code, 302)

# Create your tests here.
