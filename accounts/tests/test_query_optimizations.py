from django.test import TestCase

from accounts.models import Student, User
from accounts.views import StudentListView
from course.models import Program


class StudentListQueryOptimizationTests(TestCase):
    def setUp(self):
        program = Program.objects.create(title="Information Technology")
        for idx in range(5):
            user = User.objects.create_user(username=f"student_{idx}", is_student=True)
            Student.objects.create(
                student=user,
                level="Bachelor",
                program=program,
            )

    def test_student_list_queryset_uses_select_related(self):
        queryset = StudentListView.queryset

        with self.assertNumQueries(1):
            rows = [(obj.student.username, obj.program.title) for obj in queryset]

        self.assertEqual(len(rows), 5)
