from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import User

from .models import Invoice


@override_settings(
    STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage",
    LANGUAGE_CODE="en",
)
class PaymentFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="payment_student",
            password="password",
            is_student=True,
        )
        self.client.force_login(self.user)

    def test_create_invoice_creates_invoice_and_session(self):
        response = self.client.post(reverse("create_invoice"), {"amount": "99.50"})

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("payment_gateways"))

        invoice = Invoice.objects.get(user=self.user)
        self.assertEqual(invoice.amount, 99.50)
        self.assertFalse(invoice.payment_complete)
        self.assertEqual(self.client.session.get("invoice_session"), invoice.invoice_code)

    def test_create_invoice_ajax_rejects_non_positive_amount(self):
        response = self.client.post(
            reverse("create_invoice"),
            {"amount": "0"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["message"],
            "Amount must be greater than zero.",
        )

    def test_payment_complete_marks_invoice_as_paid(self):
        invoice = Invoice.objects.create(
            user=self.user,
            amount=10.0,
            total=26,
            invoice_code="INV-COMPLETE-1",
        )
        session = self.client.session
        session["invoice_session"] = invoice.invoice_code
        session.save()

        response = self.client.post(
            reverse("complete"),
            data="{}",
            content_type="application/json",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        invoice.refresh_from_db()
        self.assertTrue(invoice.payment_complete)
        self.assertEqual(response.json()["invoice_code"], invoice.invoice_code)

    @patch("payments.views.stripe.Charge.create")
    def test_stripe_charge_uses_invoice_amount_and_marks_complete(self, stripe_create):
        invoice = Invoice.objects.create(
            user=self.user,
            amount=12.34,
            total=26,
            invoice_code="INV-STRIPE-1",
        )
        session = self.client.session
        session["invoice_session"] = invoice.invoice_code
        session.save()

        response = self.client.post(
            reverse("stripe_charge"),
            data={"stripeToken": "tok_test"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("payment-succeed"))
        stripe_create.assert_called_once_with(
            amount=1234,
            currency="eur",
            description=f"SkillBuddy Invoice {invoice.invoice_code}",
            source="tok_test",
        )

        invoice.refresh_from_db()
        self.assertTrue(invoice.payment_complete)
