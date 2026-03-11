import json
import logging
import uuid

import gopay
import stripe
from gopay.enums import (
    BankSwiftCode,
    Currency,
    Language,
    PaymentInstrument,
    Recurrence,
)

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST
from django.views.generic.base import TemplateView

from .models import Invoice

logger = logging.getLogger(__name__)


def payment_paypal(request):
    return render(request, "payments/paypal.html", context={})


def payment_stripe(request):
    return render(request, "payments/stripe.html", context={})


def payment_coinbase(request):
    return render(request, "payments/coinbase.html", context={})


def payment_paylike(request):
    return render(request, "payments/paylike.html", context={})


def payment_succeed(request):
    return render(request, "payments/payment_succeed.html", context={})


@method_decorator(login_required, name="dispatch")
class PaymentGetwaysView(TemplateView):
    template_name = "payments/payment_gateways.html"

    def get_context_data(self, **kwargs):
        context = super(PaymentGetwaysView, self).get_context_data(**kwargs)
        invoice_code = self.request.session.get("invoice_session")
        invoice = Invoice.objects.filter(
            invoice_code=invoice_code,
            user=self.request.user,
        ).first()

        amount_cents = 0
        if invoice and invoice.amount:
            amount_cents = int(round(float(invoice.amount) * 100))

        context["key"] = settings.STRIPE_PUBLISHABLE_KEY
        context["amount"] = amount_cents
        context["description"] = (
            f"SkillBuddy Invoice {invoice.invoice_code}" if invoice else "Stripe Payment"
        )
        context["invoice_session"] = invoice_code
        return context


@login_required
@require_POST
def stripe_charge(request):
    stripe.api_key = settings.STRIPE_SECRET_KEY

    invoice_code = request.session.get("invoice_session")
    if not invoice_code:
        messages.error(request, "No active invoice found in session.")
        return redirect("create_invoice")

    invoice = get_object_or_404(Invoice, invoice_code=invoice_code, user=request.user)

    amount_cents = int(round((invoice.amount or 0) * 100))
    if amount_cents <= 0:
        messages.error(request, "Invoice amount must be greater than zero.")
        return redirect("payment_gateways")

    stripe_token = request.POST.get("stripeToken")
    if not stripe_token:
        messages.error(request, "Missing Stripe payment token.")
        return redirect("payment_gateways")

    try:
        stripe.Charge.create(
            amount=amount_cents,
            currency="eur",
            description=f"SkillBuddy Invoice {invoice.invoice_code}",
            source=stripe_token,
        )
    except stripe.error.StripeError as exc:
        logger.warning("Stripe charge failed for invoice %s: %s", invoice.invoice_code, exc)
        messages.error(request, "Payment was not completed. Please try again.")
        return redirect("payment_gateways")
    except Exception as exc:
        logger.exception(
            "Unexpected Stripe error for invoice %s: %s", invoice.invoice_code, exc
        )
        messages.error(request, "Unexpected payment error. Please try again.")
        return redirect("payment_gateways")

    invoice.payment_complete = True
    invoice.save(update_fields=["payment_complete"])
    return redirect("payment-succeed")


@login_required
def gopay_charge(request):
    if request.method != "POST":
        return JsonResponse({"message": "GET requested"})

    required_values = [
        settings.GOPAY_GOID,
        settings.GOPAY_CLIENT_ID,
        settings.GOPAY_CLIENT_SECRET,
    ]
    if not all(required_values):
        return JsonResponse(
            {"message": "GoPay credentials are not configured."}, status=500
        )

    user = request.user

    payments = gopay.payments(
        {
            "goid": settings.GOPAY_GOID,
            "clientId": settings.GOPAY_CLIENT_ID,
            "clientSecret": settings.GOPAY_CLIENT_SECRET,
            "isProductionMode": settings.GOPAY_IS_PRODUCTION,
            "scope": gopay.TokenScope.ALL,
            "language": gopay.Language.ENGLISH,
            "timeout": 30,
        }
    )

    # recurrent payment must have field ''
    recurrentPayment = {
        "recurrence": {
            "recurrence_cycle": Recurrence.DAILY,
            "recurrence_period": "7",
            "recurrence_date_to": "2015-12-31",
        }
    }

    # pre-authorized payment must have field 'preauthorization'
    preauthorizedPayment = {"preauthorization": True}

    response = payments.create_payment(
        {
            "payer": {
                "default_payment_instrument": PaymentInstrument.BANK_ACCOUNT,
                "allowed_payment_instruments": [PaymentInstrument.BANK_ACCOUNT],
                "default_swift": BankSwiftCode.FIO_BANKA,
                "allowed_swifts": [BankSwiftCode.FIO_BANKA, BankSwiftCode.MBANK],
                "contact": {
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "email": user.email,
                    "phone_number": user.phone,
                    "city": "example city",
                    "street": "Plana 67",
                    "postal_code": "373 01",
                    "country_code": "CZE",
                },
            },
            "amount": 150,
            "currency": Currency.CZECH_CROWNS,
            "order_number": "001",
            "order_description": "pojisteni01",
            "items": [
                {"name": "item01", "amount": 50},
                {"name": "item02", "amount": 100},
            ],
            "additional_params": [{"name": "invoicenumber", "value": "2015001003"}],
            "callback": {
                "return_url": "http://www.your-url.tld/return",
                "notification_url": "http://www.your-url.tld/notify",
            },
            "lang": Language.CZECH,
        }
    )

    if response.has_succeed():
        logger.info("GoPay payment succeeded for user %s", user.pk)
    else:
        logger.warning(
            "GoPay payment failed for user %s: %s %s",
            user.pk,
            response.status_code,
            response,
        )

    return JsonResponse({"message": str(response)})


@login_required
def paymentComplete(request):
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    if not is_ajax and request.method != "POST":
        return JsonResponse({"message": "Method not allowed"}, status=405)

    invoice_code = request.session.get("invoice_session")
    if not invoice_code:
        return JsonResponse({"message": "No active invoice found."}, status=400)

    invoice = get_object_or_404(Invoice, invoice_code=invoice_code, user=request.user)
    invoice.payment_complete = True
    invoice.save(update_fields=["payment_complete"])

    if request.body:
        try:
            json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"message": "Invalid JSON payload."}, status=400)

    return JsonResponse(
        {
            "message": "Payment completed!",
            "invoice_code": invoice.invoice_code,
            "payment_complete": invoice.payment_complete,
        }
    )


@login_required
def create_invoice(request):
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    if request.method == "POST":
        amount_raw = request.POST.get("amount")
        try:
            amount = float(amount_raw)
        except (TypeError, ValueError):
            amount = 0

        if amount <= 0:
            if is_ajax:
                return JsonResponse(
                    {"message": "Amount must be greater than zero."}, status=400
                )
            messages.error(request, "Amount must be greater than zero.")
            return redirect("create_invoice")

        invoice = Invoice.objects.create(
            user=request.user,
            amount=amount,
            total=26,
            invoice_code=str(uuid.uuid4()),
        )
        request.session["invoice_session"] = invoice.invoice_code

        if is_ajax:
            return JsonResponse(
                {
                    "invoice_code": invoice.invoice_code,
                    "amount": invoice.amount,
                    "payment_complete": invoice.payment_complete,
                },
                status=201,
            )

        return redirect("payment_gateways")

    return render(
        request,
        "invoices.html",
        context={"invoices": Invoice.objects.filter(user=request.user)},
    )


@login_required
def invoice_detail(request, slug):
    invoice = get_object_or_404(Invoice, invoice_code=slug, user=request.user)
    return render(request, "invoice_detail.html", context={"invoice": invoice})
