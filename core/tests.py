from datetime import time, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Student
from course.models import AcademicEvent, ClassSchedule, Course, Program
from core.models import NewsAndEvents
from result.models import CourseAttendance, TakenCourse


User = get_user_model()


class AdminDashboardTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="dashboard-admin", password="password"
        )
        self.client.force_login(self.admin)

    def test_dashboard_exposes_structured_management_modules(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        for heading in ("People", "Academics", "Planning", "Learning Platform"):
            self.assertContains(response, heading)
        self.assertContains(response, "Student course enrollments")
        self.assertContains(response, "Class schedules")
        self.assertContains(response, "Course attendance")

    def test_old_admin_panel_redirects_to_dashboard(self):
        response = self.client.get(reverse("admin_panel"))
        self.assertRedirects(response, reverse("dashboard"))

    def test_announcement_popup_gives_admin_an_edit_action(self):
        announcement = NewsAndEvents.objects.create(
            title="Admin Notice", summary="For learners.", posted_as="News"
        )
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, 'id="announcementModal"')
        self.assertContains(response, reverse("edit_post", args=[announcement.pk]))
        self.assertContains(response, "Edit announcement")


class LecturerAnnouncementTests(TestCase):
    def test_latest_announcement_is_available_to_lecturers(self):
        lecturer = User.objects.create_user(
            username="announcement-lecturer", password="password", is_lecturer=True
        )
        NewsAndEvents.objects.create(
            title="Faculty Briefing", summary="Briefing starts at ten.", posted_as="Event"
        )
        self.client.force_login(lecturer)
        response = self.client.get(reverse("profile"))
        self.assertContains(response, 'id="announcementModal"')
        self.assertContains(response, "Faculty Briefing")


class NewsAndEventsPageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="news-reader", password="password")
        self.client.force_login(self.user)
        self.news = NewsAndEvents.objects.create(
            title="Library Reopens",
            summary="The renovated library is ready.",
            content="Full opening hours and borrowing information.",
            posted_as="News",
        )
        self.event = NewsAndEvents.objects.create(
            title="Science Fair",
            summary="Student projects on display.",
            content="Visit the main hall for the complete programme.",
            posted_as="Event",
        )

    def test_list_displays_all_posts_and_detail_links(self):
        response = self.client.get(reverse("news_event"))
        self.assertContains(response, self.news.title)
        self.assertContains(response, self.event.title)
        self.assertContains(response, reverse("news_event_detail", args=[self.news.pk]))

    def test_search_and_category_filter(self):
        response = self.client.get(reverse("news_event"), {"q": "library", "category": "News"})
        self.assertContains(response, self.news.title)
        self.assertNotContains(response, self.event.title)

    def test_detail_displays_full_content(self):
        response = self.client.get(reverse("news_event_detail", args=[self.event.pk]))
        self.assertContains(response, self.event.title)
        self.assertContains(response, self.event.content)

    def test_list_is_paginated(self):
        for index in range(10):
            NewsAndEvents.objects.create(title=f"Post {index}", posted_as="News")
        response = self.client.get(reverse("news_event"))
        self.assertEqual(len(response.context["items"]), 9)
        self.assertTrue(response.context["page_obj"].has_next())


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

    def test_latest_announcement_is_available_to_students(self):
        announcement = NewsAndEvents.objects.create(
            title="Campus Festival", summary="Join us on Friday.", posted_as="Event"
        )
        response = self.client.get(reverse("student_calendar"))
        self.assertContains(response, 'id="announcementModal"')
        self.assertContains(response, announcement.title)
        self.assertContains(response, announcement.summary)

# Create your tests here.
