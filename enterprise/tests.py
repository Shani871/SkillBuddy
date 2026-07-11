from datetime import timedelta

from django.test import TestCase
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from .models import AuditEvent, College, CustomRole, PlacementApplication, PlacementCompany, PlacementDrive, SupportTicket


class EnterpriseWorkflowTests(TestCase):
    def setUp(self):
        cache.clear()
        self.a = College.objects.create(name="Alpha College", code="alpha", domain="alpha.test", contact_email="a@test.com", status="active")
        self.b = College.objects.create(name="Beta College", code="beta", domain="beta.test", contact_email="b@test.com", status="active")
        self.superadmin = User.objects.create_superuser(username="root-admin", password="StrongTest!123", email="root@test.com", role="super_admin")
        self.principal = User.objects.create_user(username="alpha-admin", password="StrongTest!123", role="college_admin", college=self.a)
        self.student = User.objects.create_user(username="alpha-student", password="StrongTest!123", email="student@alpha.test", role="student", college=self.a, is_student=True)
        self.other_student = User.objects.create_user(username="beta-student", password="StrongTest!123", role="student", college=self.b, is_student=True)

    def test_only_superadmin_can_manage_colleges(self):
        self.client.force_login(self.principal)
        self.assertEqual(self.client.get(reverse("enterprise:college_list")).status_code, 403)
        self.client.force_login(self.superadmin)
        response = self.client.post(reverse("enterprise:college_action", args=[self.a.pk, "suspend"]))
        self.assertRedirects(response, reverse("enterprise:college_list"))
        self.a.refresh_from_db()
        self.assertEqual(self.a.status, "suspended")
        self.assertTrue(AuditEvent.objects.filter(action="college.suspend", college=self.a).exists())

    def test_college_admin_cannot_mutate_another_tenant_user(self):
        self.client.force_login(self.principal)
        response = self.client.post(reverse("enterprise:user_action", args=[self.other_student.pk, "lock"]))
        self.assertEqual(response.status_code, 403)
        self.other_student.refresh_from_db()
        self.assertTrue(self.other_student.is_active)

    def test_login_disabled_is_enforced_by_auth_backend(self):
        self.student.login_disabled = True
        self.student.save()
        self.assertFalse(self.client.login(username="alpha-student", password="StrongTest!123"))

    def test_student_can_apply_once_to_own_college_drive(self):
        company = PlacementCompany.objects.create(college=self.a, name="Example Corp")
        drive = PlacementDrive.objects.create(
            college=self.a, company=company, title="Graduate Hiring", role_title="Engineer",
            application_deadline=timezone.localdate() + timedelta(days=7), status="open",
        )
        self.client.force_login(self.student)
        url = reverse("enterprise:apply_to_drive", args=[drive.pk])
        self.client.post(url)
        self.client.post(url)
        self.assertEqual(PlacementApplication.objects.filter(drive=drive, student=self.student).count(), 1)

    def test_user_lock_and_force_logout_are_audited(self):
        self.client.force_login(self.principal)
        response = self.client.post(reverse("enterprise:user_action", args=[self.student.pk, "lock"]))
        self.assertEqual(response.status_code, 302)
        self.student.refresh_from_db()
        self.assertFalse(self.student.is_active)
        self.assertTrue(AuditEvent.objects.filter(action="user.lock", target_id=str(self.student.pk)).exists())

    def test_college_admin_creates_tenant_scoped_custom_role(self):
        self.client.force_login(self.principal)
        response = self.client.post(reverse("enterprise:role_create"), {
            "college": self.a.pk, "name": "Academic Reviewer", "slug": "academic-reviewer",
            "description": "Reviews results", "permissions": ["department-analytics", "reports"],
            "is_active": "on",
        })
        self.assertEqual(response.status_code, 302)
        role = CustomRole.objects.get(slug="academic-reviewer")
        self.assertEqual(role.college, self.a)
        self.assertIn("reports", role.permissions)

    def test_support_ticket_is_visible_only_inside_tenant(self):
        SupportTicket.objects.create(college=self.a, created_by=self.principal, subject="Alpha issue", description="A")
        SupportTicket.objects.create(college=self.b, created_by=self.other_student, subject="Beta issue", description="B")
        self.client.force_login(self.principal)
        response = self.client.get(reverse("enterprise:ticket_list"))
        self.assertContains(response, "Alpha issue")
        self.assertNotContains(response, "Beta issue")

    def test_repeated_failed_logins_trigger_temporary_lockout(self):
        for _ in range(5):
            self.assertFalse(self.client.login(username="alpha-student", password="wrong-password"))
        self.assertFalse(self.client.login(username="alpha-student", password="StrongTest!123"))
        cache.clear()
        self.assertTrue(self.client.login(username="alpha-student", password="StrongTest!123"))

    def test_tenant_report_export_does_not_leak_other_college(self):
        self.client.force_login(self.principal)
        response = self.client.get(reverse("enterprise:export_report", args=["users"]))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("alpha-student", content)
        self.assertNotIn("beta-student", content)

    def test_password_reset_sends_link_instead_of_exposing_password(self):
        from django.core import mail
        self.client.force_login(self.principal)
        response = self.client.post(reverse("enterprise:user_action", args=[self.student.pk, "reset-password"]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("password", mail.outbox[0].subject.lower())
