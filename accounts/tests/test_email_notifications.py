from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.urls import reverse

from course.models import Program

User = get_user_model()


class EmailNotificationTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="admin", password="password", email="admin@example.com"
        )
        self.program = Program.objects.create(title="Computer Science")
        self.client.login(username="admin", password="password")

    def test_student_add_sends_email(self):
        self.assertEqual(len(mail.outbox), 0)

        url = reverse("add_student")
        data = {
            "username": "new_student",
            "first_name": "John",
            "last_name": "Doe",
            "email": "student@example.com",
            "gender": "M",
            "address": "123 Street",
            "phone": "1234567890",
            "level": "Bachelor",
            "program": self.program.id,
            "password1": "studentpass123",
            "password2": "studentpass123",
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.subject, "Your SkillBuddy Account Credentials")
        self.assertEqual(email.to, ["student@example.com"])
        self.assertIn("Username/User ID: new_student", email.body)
        self.assertIn("Password: studentpass123", email.body)

    def test_lecturer_add_sends_email(self):
        self.assertEqual(len(mail.outbox), 0)

        url = reverse("add_lecturer")
        data = {
            "username": "new_lecturer",
            "first_name": "Jane",
            "last_name": "Smith",
            "email": "lecturer@example.com",
            "gender": "F",
            "address": "456 Avenue",
            "phone": "0987654321",
            "password1": "lecturerpass123",
            "password2": "lecturerpass123",
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.subject, "Your SkillBuddy Teacher Account Credentials")
        self.assertEqual(email.to, ["lecturer@example.com"])
        self.assertIn("Username/User ID: new_lecturer", email.body)
        self.assertIn("Password: lecturerpass123", email.body)
