from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from accounts.models import User
from enterprise.models import College, PlacementCompany, PlacementDrive, SupportTicket


class Command(BaseCommand):
    help = "Create one local demo login for every SkillBuddy role."

    def handle(self, *args, **options):
        college, _ = College.objects.update_or_create(
            code="skillbuddy-demo",
            defaults={
                "name": "SkillBuddy Demo College", "domain": "demo.skillbuddy.local",
                "contact_email": "principal@skillbuddy.local", "status": "active",
                "plan": "professional", "subscription_ends_on": timezone.localdate() + timedelta(days=365),
                "monthly_price": 24999, "storage_limit_gb": 100,
            },
        )
        roles = [
            ("superadmin", User.ROLE_SUPER_ADMIN, "Super", "Admin"),
            ("principal", User.ROLE_COLLEGE_ADMIN, "College", "Principal"),
            ("hod", User.ROLE_HOD, "Department", "Head"),
            ("faculty", User.ROLE_FACULTY, "Demo", "Faculty"),
            ("student", User.ROLE_STUDENT, "Demo", "Student"),
            ("placement", User.ROLE_PLACEMENT, "Placement", "Officer"),
        ]
        for username, role, first_name, last_name in roles:
            user, _ = User.objects.get_or_create(username=username)
            user.role, user.first_name, user.last_name = role, first_name, last_name
            user.email = f"{username}@skillbuddy.local"
            user.college_name, user.department_name = "SkillBuddy Demo College", "Computer Science"
            user.college = None if role == User.ROLE_SUPER_ADMIN else college
            user.is_superuser = user.is_staff = role == User.ROLE_SUPER_ADMIN
            user.is_student = role == User.ROLE_STUDENT
            user.is_lecturer = role == User.ROLE_FACULTY
            user.is_dep_head = role == User.ROLE_HOD
            user.is_active = True
            user.set_password("Demo@123")
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Ready: {username} ({user.get_user_role})"))
        company, _ = PlacementCompany.objects.get_or_create(
            college=college, name="Acme Technologies",
            defaults={"website": "https://example.com", "contact_name": "Campus Hiring", "contact_email": "careers@example.com"},
        )
        PlacementDrive.objects.get_or_create(
            college=college, company=company, role_title="Graduate Software Engineer",
            defaults={"title": "2026 Graduate Hiring", "minimum_cgpa": 7.0, "salary_package": 850000, "application_deadline": timezone.localdate() + timedelta(days=30), "status": "open"},
        )
        SupportTicket.objects.get_or_create(
            college=college, subject="Welcome to enterprise support",
            defaults={"created_by": User.objects.get(username="principal"), "description": "Your tenant is configured and ready for production setup."},
        )
        self.stdout.write("Demo password for every account: Demo@123")
