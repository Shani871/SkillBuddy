from decimal import Decimal

from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import Student, User
from core.models import Semester, Session
from course.models import Course, CourseAllocation, Program
from result.models import FAIL, TakenCourse


@override_settings(
    STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage",
    LANGUAGE_CODE="en",
)
class ResultLogicTests(TestCase):
    def setUp(self):
        self.program = Program.objects.create(title="Computer Science")
        self.session = Session.objects.create(
            session="2025/2026",
            is_current_session=True,
        )
        self.semester = Semester.objects.create(
            semester=settings.FIRST,
            is_current_semester=True,
            session=self.session,
        )

        self.lecturer = User.objects.create_user(
            username="lecturer1",
            password="password",
            is_lecturer=True,
        )
        self.student_user = User.objects.create_user(
            username="student1",
            password="password",
            is_student=True,
        )
        self.student = Student.objects.create(
            student=self.student_user,
            level=settings.BACHELOR_DEGREE,
            program=self.program,
        )

        self.other_student_user = User.objects.create_user(
            username="student2",
            password="password",
            is_student=True,
        )
        self.other_student = Student.objects.create(
            student=self.other_student_user,
            level=settings.BACHELOR_DEGREE,
            program=self.program,
        )

        self.course_one = Course.objects.create(
            title="Algorithms",
            code="CSC201",
            credit=3,
            summary="Algorithms",
            program=self.program,
            level=settings.BACHELOR_DEGREE,
            year=2,
            semester=settings.FIRST,
        )
        self.course_two = Course.objects.create(
            title="Databases",
            code="CSC202",
            credit=2,
            summary="Databases",
            program=self.program,
            level=settings.BACHELOR_DEGREE,
            year=2,
            semester=settings.FIRST,
        )

        allocation = CourseAllocation.objects.create(lecturer=self.lecturer)
        allocation.courses.add(self.course_one, self.course_two)

    def test_student_with_passing_grades_gets_correct_gpa(self):
        tc1 = TakenCourse.objects.create(
            student=self.student,
            course=self.course_one,
            assignment=Decimal("20"),
            mid_exam=Decimal("20"),
            quiz=Decimal("15"),
            attendance=Decimal("10"),
            final_exam=Decimal("30"),
        )
        TakenCourse.objects.create(
            student=self.student,
            course=self.course_two,
            assignment=Decimal("15"),
            mid_exam=Decimal("15"),
            quiz=Decimal("10"),
            attendance=Decimal("10"),
            final_exam=Decimal("20"),
        )

        gpa = tc1.calculate_gpa()
        self.assertEqual(gpa, Decimal("3.60"))

    def test_failing_grade_sets_fail_comment(self):
        taken = TakenCourse.objects.create(
            student=self.student,
            course=self.course_one,
            assignment=Decimal("5"),
            mid_exam=Decimal("5"),
            quiz=Decimal("5"),
            attendance=Decimal("3"),
            final_exam=Decimal("10"),
        )

        self.assertEqual(taken.comment, FAIL)

    def test_gpa_and_cgpa_handle_zero_courses_gracefully(self):
        temp_record = TakenCourse(student=self.other_student, course=self.course_one)

        self.assertEqual(temp_record.calculate_gpa(), Decimal("0.00"))
        self.assertEqual(temp_record.calculate_cgpa(), Decimal("0.00"))

    def test_add_score_for_view_excludes_students_not_enrolled_in_course(self):
        TakenCourse.objects.create(student=self.student, course=self.course_one)
        TakenCourse.objects.create(student=self.other_student, course=self.course_two)

        self.client.force_login(self.lecturer)
        response = self.client.get(
            reverse("add_score_for", kwargs={"id": self.course_one.id})
        )

        self.assertEqual(response.status_code, 200)
        students_in_context = list(response.context["students"])
        self.assertEqual(len(students_in_context), 1)
        self.assertEqual(students_in_context[0].student_id, self.student.id)

    def test_result_pdf_view_returns_pdf_response(self):
        TakenCourse.objects.create(student=self.student, course=self.course_one)

        self.client.force_login(self.lecturer)
        response = self.client.get(
            reverse("result_sheet_pdf_view", kwargs={"id": self.course_one.id})
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
