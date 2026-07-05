from django.contrib.auth import get_user_model
from django.core import mail
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch

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
        self.assertEqual(email.subject, "Your Account Login Credentials")
        self.assertEqual(email.to, ["student@example.com"])
        self.assertIn("Username: new_student", email.body)
        self.assertIn("Password: studentpass123", email.body)
        self.assertIn("Login URL: http://testserver/", email.body)
        student = User.objects.get(username="new_student")
        self.assertNotEqual(student.password, "studentpass123")
        self.assertTrue(student.check_password("studentpass123"))

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
        self.assertEqual(email.subject, "Your Account Login Credentials")
        self.assertEqual(email.to, ["lecturer@example.com"])
        self.assertIn("Username: new_lecturer", email.body)
        self.assertIn("Password: lecturerpass123", email.body)

    def test_blank_credentials_are_generated_and_emailed(self):
        response = self.client.post(
            reverse("add_lecturer"),
            {
                "username": "",
                "first_name": "Generated",
                "last_name": "User",
                "email": "generated@example.com",
                "gender": "F",
                "address": "456 Avenue",
                "phone": "0987654321",
                "password1": "",
                "password2": "",
            },
        )

        self.assertEqual(response.status_code, 302)
        lecturer = User.objects.get(email="generated@example.com")
        self.assertTrue(lecturer.username)
        self.assertTrue(lecturer.has_usable_password())
        self.assertIn(f"Username: {lecturer.username}", mail.outbox[0].body)
        self.assertNotIn(lecturer.password, mail.outbox[0].body)

    @patch("accounts.utils.EmailMultiAlternatives.send", side_effect=OSError("SMTP down"))
    def test_email_failure_is_reported_but_saved_account_remains(self, _send):
        response = self.client.post(
            reverse("add_lecturer"),
            {
                "username": "saved_lecturer",
                "first_name": "Sam",
                "last_name": "Lee",
                "email": "sam@example.com",
                "gender": "M",
                "address": "456 Avenue",
                "phone": "0987654321",
                "password1": "lecturerpass123",
                "password2": "lecturerpass123",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(username="saved_lecturer").exists())
        messages = [str(message) for message in get_messages(response.wsgi_request)]
        self.assertTrue(any("could not be sent" in message for message in messages))
