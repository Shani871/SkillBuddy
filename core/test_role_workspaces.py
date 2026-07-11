from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from enterprise.models import College


class RoleWorkspaceTests(TestCase):
    def setUp(self):
        college = College.objects.create(
            name="Role Test College", code="role-test", domain="role.test",
            contact_email="admin@role.test", status="active",
        )
        self.faculty = User.objects.create_user(
            username="role-faculty", password="test-pass-123", role="faculty", college=college
        )

    def test_dashboard_is_specific_to_role(self):
        self.client.force_login(self.faculty)
        response = self.client.get(reverse("role_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Faculty Copilot")
        self.assertNotContains(response, "Manage Colleges")

    def test_disallowed_module_returns_403(self):
        self.client.force_login(self.faculty)
        response = self.client.get(reverse("role_module", args=["add-college"]))
        self.assertEqual(response.status_code, 403)

    def test_allowed_module_is_available(self):
        self.client.force_login(self.faculty)
        response = self.client.get(reverse("role_module", args=["assignments"]))
        self.assertEqual(response.status_code, 200)
