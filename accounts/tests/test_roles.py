from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from django.test import RequestFactory, TestCase

from accounts.decorators import role_required

User = get_user_model()


class UserRolePropertyTests(TestCase):
    def test_admin_role(self):
        user = User.objects.create_user(username="admin_user", is_superuser=True)
        self.assertEqual(str(user.get_user_role), "Admin")

    def test_student_role(self):
        user = User.objects.create_user(username="student_user", is_student=True)
        self.assertEqual(str(user.get_user_role), "Student")

    def test_lecturer_role(self):
        user = User.objects.create_user(username="lecturer_user", is_lecturer=True)
        self.assertEqual(str(user.get_user_role), "Lecturer")

    def test_parent_role(self):
        user = User.objects.create_user(username="parent_user", is_parent=True)
        self.assertEqual(str(user.get_user_role), "Parent")

    def test_department_head_role(self):
        user = User.objects.create_user(username="dep_head_user", is_dep_head=True)
        self.assertEqual(str(user.get_user_role), "Department Head")

    def test_unknown_role(self):
        user = User.objects.create_user(username="no_role_user")
        self.assertEqual(str(user.get_user_role), "Unknown")


class RoleRequiredDecoratorTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.student = User.objects.create_user(
            username="student", password="password", is_student=True
        )
        self.lecturer = User.objects.create_user(
            username="lecturer", password="password", is_lecturer=True
        )
        self.parent = User.objects.create_user(
            username="parent", password="password", is_parent=True
        )
        self.admin = User.objects.create_superuser(
            username="admin", password="password", email="admin@example.com"
        )
        self.no_role = User.objects.create_user(username="plain", password="password")

    def _view(self, request):
        return HttpResponse("ok")

    def test_role_required_allows_matching_role(self):
        decorated = role_required(["student", "lecturer"])(self._view)

        request = self.factory.get("/role-protected")
        request.user = self.student
        response = decorated(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"ok")

    def test_role_required_redirects_non_matching_user(self):
        decorated = role_required(["student", "lecturer"])(self._view)

        request = self.factory.get("/role-protected")
        request.user = self.parent
        response = decorated(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/")

    def test_role_required_allows_superuser(self):
        decorated = role_required(["student"])(self._view)

        request = self.factory.get("/role-protected")
        request.user = self.admin
        response = decorated(request)

        self.assertEqual(response.status_code, 200)

    def test_role_required_redirects_anonymous_user(self):
        decorated = role_required(["student"])(self._view)

        request = self.factory.get("/role-protected")
        request.user = AnonymousUser()
        response = decorated(request)

        self.assertEqual(response.status_code, 302)

    def test_role_required_raises_on_invalid_role(self):
        with self.assertRaises(ValueError):
            role_required(["invalid-role"])(self._view)

    def test_role_required_custom_redirect(self):
        decorated = role_required(["lecturer"], redirect_to="/login/")(self._view)

        request = self.factory.get("/role-protected")
        request.user = self.no_role
        response = decorated(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/login/")
