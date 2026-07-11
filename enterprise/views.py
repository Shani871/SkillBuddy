from datetime import timedelta
import csv

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.sessions.models import Session
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.db.models.deletion import ProtectedError
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import User
from .access import MANAGER_ROLES, PLACEMENT_ROLES, REPORT_ROLES, role_required
from .forms import CollegeForm, CustomRoleForm, EnterpriseUserForm, PlacementCompanyForm, PlacementDriveForm, SupportTicketForm, TenantSettingsForm
from .models import AuditEvent, College, CustomRole, PlacementApplication, PlacementCompany, PlacementDrive, SupportTicket


def _audit(request, action, target, description, college=None):
    AuditEvent.objects.create(
        actor=request.user, college=college or getattr(target, "college", None), action=action,
        target_type=target.__class__.__name__, target_id=str(target.pk), description=description,
        ip_address=request.META.get("REMOTE_ADDR"),
    )


def _tenant_college(request, requested_id=None):
    if request.user.effective_role == User.ROLE_SUPER_ADMIN:
        college_id = requested_id or request.GET.get("college") or request.POST.get("college")
        return get_object_or_404(College, pk=college_id) if college_id else College.objects.first()
    if not request.user.college_id:
        raise PermissionDenied("Your account is not assigned to a college.")
    return request.user.college


@login_required
@role_required(User.ROLE_SUPER_ADMIN)
def college_list(request):
    query = request.GET.get("q", "").strip()
    colleges = College.objects.annotate(user_count=Count("users"))
    if query:
        colleges = colleges.filter(Q(name__icontains=query) | Q(code__icontains=query) | Q(domain__icontains=query))
    totals = colleges.aggregate(revenue=Sum("monthly_price"), users=Sum("user_count"))
    return render(request, "enterprise/college_list.html", {"colleges": colleges, "query": query, "totals": totals})


@login_required
@role_required(User.ROLE_SUPER_ADMIN)
def college_create(request):
    form = CollegeForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        college = form.save()
        _audit(request, "college.create", college, f"Created college {college.name}", college)
        messages.success(request, f"{college.name} was created.")
        return redirect("enterprise:college_list")
    return render(request, "enterprise/form.html", {"form": form, "title": "Add college", "subtitle": "Create a tenant with its own domain, plan, storage, and branding."})


@login_required
@role_required(User.ROLE_SUPER_ADMIN)
def college_edit(request, pk):
    college = get_object_or_404(College, pk=pk)
    form = CollegeForm(request.POST or None, request.FILES or None, instance=college)
    if request.method == "POST" and form.is_valid():
        form.save()
        _audit(request, "college.update", college, f"Updated college {college.name}", college)
        messages.success(request, "College settings saved.")
        return redirect("enterprise:college_list")
    return render(request, "enterprise/form.html", {"form": form, "title": f"Edit {college.name}", "subtitle": "Changes apply immediately to this tenant."})


@login_required
@require_POST
@role_required(User.ROLE_SUPER_ADMIN)
def college_action(request, pk, action):
    college = get_object_or_404(College, pk=pk)
    if action in {"activate", "suspend", "trial"}:
        college.status = {"activate": "active", "suspend": "suspended", "trial": "trial"}[action]
    elif action == "extend":
        try:
            days = max(1, min(int(request.POST.get("days", 30)), 1095))
        except ValueError:
            return HttpResponseBadRequest("Invalid extension period")
        baseline = max(college.subscription_ends_on or timezone.localdate(), timezone.localdate())
        college.subscription_ends_on = baseline + timedelta(days=days)
    elif action == "delete":
        try:
            name = college.name
            college.delete()
            messages.success(request, f"{name} was deleted.")
            return redirect("enterprise:college_list")
        except ProtectedError:
            messages.error(request, "Move or remove the college users before deleting this tenant.")
            return redirect("enterprise:college_list")
    else:
        return HttpResponseBadRequest("Unknown action")
    college.save()
    _audit(request, f"college.{action}", college, f"{action.title()} action applied to {college.name}", college)
    messages.success(request, f"{college.name} was updated.")
    return redirect("enterprise:college_list")


@login_required
@role_required(*MANAGER_ROLES)
def user_list(request):
    users = User.objects.select_related("college").exclude(pk=request.user.pk)
    if request.user.effective_role != User.ROLE_SUPER_ADMIN:
        users = users.filter(college=request.user.college).exclude(role=User.ROLE_SUPER_ADMIN)
    query = request.GET.get("q", "").strip()
    if query:
        users = users.filter(Q(username__icontains=query) | Q(first_name__icontains=query) | Q(last_name__icontains=query) | Q(email__icontains=query))
    page = Paginator(users, 20).get_page(request.GET.get("page"))
    return render(request, "enterprise/user_list.html", {"page_obj": page, "query": query})


@login_required
@role_required(*MANAGER_ROLES)
def user_create(request):
    form = EnterpriseUserForm(request.POST or None, actor=request.user)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        _audit(request, "user.create", user, f"Created {user.get_user_role} account {user.username}", user.college)
        messages.success(request, f"Account {user.username} was created.")
        return redirect("enterprise:user_list")
    return render(request, "enterprise/form.html", {"form": form, "title": "Create user", "subtitle": "Assign a tenant, department, role, and secure initial password."})


def _managed_user(request, pk):
    user = get_object_or_404(User.objects.select_related("college"), pk=pk)
    if user.pk == request.user.pk:
        raise PermissionDenied("Use your profile settings to change your own account.")
    if request.user.effective_role != User.ROLE_SUPER_ADMIN and (user.college_id != request.user.college_id or user.effective_role == User.ROLE_SUPER_ADMIN):
        raise PermissionDenied("This user is outside your tenant scope.")
    return user


@login_required
@role_required(*MANAGER_ROLES)
def user_edit(request, pk):
    user = _managed_user(request, pk)
    form = EnterpriseUserForm(request.POST or None, instance=user, actor=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        _audit(request, "user.update", user, f"Updated account {user.username}", user.college)
        messages.success(request, "User account saved.")
        return redirect("enterprise:user_list")
    return render(request, "enterprise/form.html", {"form": form, "title": f"Edit {user.get_full_name}", "subtitle": "Role and tenant changes take effect immediately."})


@login_required
@require_POST
@role_required(*MANAGER_ROLES)
def user_action(request, pk, action):
    user = _managed_user(request, pk)
    if action == "lock": user.is_active = False
    elif action == "unlock": user.is_active = True
    elif action == "disable": user.login_disabled = True
    elif action == "enable": user.login_disabled = False
    elif action == "verify": user.email_verified_at = timezone.now()
    elif action == "reset-password":
        if not user.email:
            messages.error(request, "Add a verified email address before sending a password reset.")
            return redirect("enterprise:user_list")
        reset_form = PasswordResetForm({"email": user.email})
        if not reset_form.is_valid():
            messages.error(request, "The password-reset request could not be prepared.")
            return redirect("enterprise:user_list")
        reset_form.save(
            request=request, use_https=request.is_secure(),
            email_template_name="registration/password_reset_email.html",
            subject_template_name="registration/password_reset_subject.txt",
        )
        messages.success(request, f"A secure password-reset link was sent to {user.email}.")
    elif action == "force-logout":
        for session in Session.objects.all():
            if session.get_decoded().get("_auth_user_id") == str(user.pk):
                session.delete()
    else: return HttpResponseBadRequest("Unknown action")
    user.save()
    _audit(request, f"user.{action}", user, f"{action.replace('-', ' ').title()} for {user.username}", user.college)
    if action != "reset-password": messages.success(request, f"{action.replace('-', ' ').title()} completed.")
    return redirect("enterprise:user_list")


@login_required
@role_required(*PLACEMENT_ROLES, User.ROLE_STUDENT)
def placement_dashboard(request):
    college = _tenant_college(request)
    drives = PlacementDrive.objects.select_related("company").filter(college=college)
    applications = PlacementApplication.objects.select_related("drive", "student").filter(drive__college=college)
    if request.user.effective_role == User.ROLE_STUDENT:
        applications = applications.filter(student=request.user)
    stats = {
        "companies": PlacementCompany.objects.filter(college=college, is_active=True).count(),
        "open_drives": drives.filter(status="open").count(),
        "applications": applications.count(),
        "offers": applications.filter(status__in=("offered", "accepted")).count(),
        "placed": applications.filter(status="accepted").values("student_id").distinct().count(),
    }
    return render(request, "enterprise/placement_dashboard.html", {
        "college": college, "drives": drives[:20], "applications": applications[:20], "stats": stats,
        "can_manage": request.user.effective_role in PLACEMENT_ROLES,
    })


@login_required
@role_required(*PLACEMENT_ROLES)
def company_create(request):
    college = _tenant_college(request)
    form = PlacementCompanyForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        company = form.save(commit=False)
        company.college = college
        company.save()
        _audit(request, "placement.company.create", company, f"Added placement company {company.name}", college)
        messages.success(request, "Company added to the placement pipeline.")
        return redirect("enterprise:placement_dashboard")
    return render(request, "enterprise/form.html", {"form": form, "title": "Add company", "subtitle": f"Placement partner for {college}."})


@login_required
@role_required(*PLACEMENT_ROLES)
def drive_create(request):
    college = _tenant_college(request)
    form = PlacementDriveForm(request.POST or None, college=college)
    if request.method == "POST" and form.is_valid():
        drive = form.save(commit=False)
        drive.college = college
        drive.save()
        _audit(request, "placement.drive.create", drive, f"Created drive {drive}", college)
        messages.success(request, "Placement drive created.")
        return redirect("enterprise:placement_dashboard")
    return render(request, "enterprise/form.html", {"form": form, "title": "Create placement drive", "subtitle": "Publish eligibility, compensation, deadline, and interview details."})


@login_required
@require_POST
@role_required(User.ROLE_STUDENT)
def apply_to_drive(request, pk):
    college = _tenant_college(request)
    drive = get_object_or_404(PlacementDrive, pk=pk, college=college, status="open", application_deadline__gte=timezone.localdate())
    application, created = PlacementApplication.objects.get_or_create(drive=drive, student=request.user)
    if created:
        _audit(request, "placement.apply", application, f"Applied to {drive}", college)
        messages.success(request, "Application submitted.")
    else:
        messages.info(request, "You already applied for this drive.")
    return redirect("enterprise:placement_dashboard")


@login_required
@require_POST
@role_required(*PLACEMENT_ROLES)
def application_status(request, pk):
    college = _tenant_college(request)
    application = get_object_or_404(PlacementApplication, pk=pk, drive__college=college)
    status = request.POST.get("status")
    valid = {choice[0] for choice in PlacementApplication.STATUS_CHOICES}
    if status not in valid:
        return HttpResponseBadRequest("Invalid application status")
    application.status = status
    application.notes = request.POST.get("notes", application.notes)
    application.save()
    _audit(request, "placement.application.status", application, f"Set {application.student} to {status}", college)
    messages.success(request, "Candidate status updated.")
    return redirect("enterprise:placement_dashboard")


@login_required
def audit_log(request):
    if request.user.effective_role == User.ROLE_SUPER_ADMIN:
        events = AuditEvent.objects.select_related("actor", "college")
    elif request.user.effective_role == User.ROLE_COLLEGE_ADMIN:
        events = AuditEvent.objects.select_related("actor", "college").filter(college=request.user.college)
    else:
        raise PermissionDenied
    return render(request, "enterprise/audit_log.html", {"events": Paginator(events, 50).get_page(request.GET.get("page"))})


@login_required
@role_required(User.ROLE_SUPER_ADMIN, User.ROLE_COLLEGE_ADMIN)
def tenant_settings(request, pk=None):
    college = _tenant_college(request, pk)
    if not college:
        messages.info(request, "Create a college before configuring tenant settings.")
        return redirect("enterprise:college_create")
    form = TenantSettingsForm(request.POST or None, request.FILES or None, instance=college)
    if request.method == "POST" and form.is_valid():
        form.save()
        _audit(request, "tenant.settings.update", college, f"Updated tenant settings for {college}", college)
        messages.success(request, "Tenant branding and service settings saved.")
        return redirect("role_dashboard")
    return render(request, "enterprise/form.html", {"form": form, "title": f"{college} settings", "subtitle": "Branding, communication, AI limits, and payments for this tenant."})


@login_required
def ticket_list(request):
    if request.user.effective_role == User.ROLE_SUPER_ADMIN:
        tickets = SupportTicket.objects.select_related("college", "created_by")
    elif request.user.college_id:
        tickets = SupportTicket.objects.select_related("college", "created_by").filter(college=request.user.college)
    else:
        tickets = SupportTicket.objects.none()
    return render(request, "enterprise/ticket_list.html", {"tickets": tickets, "can_manage": request.user.effective_role in MANAGER_ROLES})


@login_required
def ticket_create(request):
    form = SupportTicketForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        ticket = form.save(commit=False)
        ticket.college = request.user.college
        ticket.created_by = request.user
        ticket.save()
        _audit(request, "support.ticket.create", ticket, f"Opened ticket: {ticket.subject}", ticket.college)
        messages.success(request, "Support ticket opened. The company team can now track it.")
        return redirect("enterprise:ticket_list")
    return render(request, "enterprise/form.html", {"form": form, "title": "Open support ticket", "subtitle": "Describe the problem and its business impact."})


@login_required
@require_POST
@role_required(*MANAGER_ROLES)
def ticket_status(request, pk):
    ticket = get_object_or_404(SupportTicket, pk=pk)
    if request.user.effective_role != User.ROLE_SUPER_ADMIN and ticket.college_id != request.user.college_id:
        raise PermissionDenied
    status = request.POST.get("status")
    if status not in {choice[0] for choice in SupportTicket.STATUS_CHOICES}:
        return HttpResponseBadRequest("Invalid ticket status")
    ticket.status = status
    ticket.save()
    _audit(request, "support.ticket.status", ticket, f"Set ticket #{ticket.pk} to {status}", ticket.college)
    messages.success(request, "Ticket status updated.")
    return redirect("enterprise:ticket_list")


@login_required
@role_required(*MANAGER_ROLES)
def role_list(request):
    roles = CustomRole.objects.select_related("college").annotate(user_count=Count("users"))
    if request.user.effective_role != User.ROLE_SUPER_ADMIN:
        roles = roles.filter(college=request.user.college)
    return render(request, "enterprise/role_list.html", {"roles": roles})


@login_required
@role_required(*MANAGER_ROLES)
def role_create(request):
    form = CustomRoleForm(request.POST or None, actor=request.user)
    if request.method == "POST" and form.is_valid():
        role = form.save()
        _audit(request, "role.create", role, f"Created custom role {role.name}", role.college)
        messages.success(request, "Custom role created and ready to assign.")
        return redirect("enterprise:role_list")
    return render(request, "enterprise/form.html", {"form": form, "title": "Create role", "subtitle": "Choose the exact workspace permissions this role receives."})


def _managed_role(request, pk):
    role = get_object_or_404(CustomRole, pk=pk)
    if request.user.effective_role != User.ROLE_SUPER_ADMIN and role.college_id != request.user.college_id:
        raise PermissionDenied
    return role


@login_required
@role_required(*MANAGER_ROLES)
def role_edit(request, pk):
    role = _managed_role(request, pk)
    form = CustomRoleForm(request.POST or None, instance=role, actor=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        _audit(request, "role.update", role, f"Updated custom role {role.name}", role.college)
        messages.success(request, "Role permission matrix saved.")
        return redirect("enterprise:role_list")
    return render(request, "enterprise/form.html", {"form": form, "title": f"Edit {role.name}", "subtitle": "Permission changes apply to every assigned user."})


@login_required
@require_POST
@role_required(*MANAGER_ROLES)
def role_delete(request, pk):
    role = _managed_role(request, pk)
    name, college = role.name, role.college
    role.delete()
    _audit(request, "role.delete", role, f"Deleted custom role {name}", college)
    messages.success(request, "Custom role deleted; assigned users retain their primary role.")
    return redirect("enterprise:role_list")


@login_required
@role_required(*REPORT_ROLES)
def reports_dashboard(request):
    is_company = request.user.effective_role == User.ROLE_SUPER_ADMIN
    users = User.objects.select_related("college") if is_company else User.objects.filter(college=request.user.college)
    colleges = College.objects.all() if is_company else College.objects.filter(pk=request.user.college_id)
    applications = PlacementApplication.objects.filter(drive__college__in=colleges)
    tickets = SupportTicket.objects.filter(college__in=colleges)
    role_counts = users.values("role").annotate(total=Count("id")).order_by("role")
    context = {
        "college_count": colleges.count(),
        "active_users": users.filter(is_active=True, login_disabled=False).count(),
        "monthly_revenue": colleges.filter(status="active").aggregate(total=Sum("monthly_price"))["total"] or 0,
        "open_tickets": tickets.exclude(status="resolved").count(),
        "applications": applications.count(),
        "offers": applications.filter(status__in=("offered", "accepted")).count(),
        "role_counts": role_counts,
    }
    return render(request, "enterprise/reports.html", context)


@login_required
@role_required(*REPORT_ROLES)
def export_report(request, report_type):
    is_company = request.user.effective_role == User.ROLE_SUPER_ADMIN
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="skillbuddy-{report_type}-{timezone.localdate()}.csv"'
    writer = csv.writer(response)
    if report_type == "users":
        rows = User.objects.select_related("college")
        if not is_company: rows = rows.filter(college=request.user.college)
        writer.writerow(["Username", "Name", "Email", "Role", "College", "Department", "Active", "Login disabled"])
        for user in rows.iterator():
            writer.writerow([user.username, user.get_full_name, user.email, user.get_user_role, user.college or "Company", user.department_name, user.is_active, user.login_disabled])
    elif report_type == "colleges" and is_company:
        writer.writerow(["Code", "College", "Domain", "Status", "Plan", "Monthly price", "Subscription ends", "Storage limit GB"])
        for college in College.objects.all().iterator():
            writer.writerow([college.code, college.name, college.domain, college.status, college.plan, college.monthly_price, college.subscription_ends_on, college.storage_limit_gb])
    elif report_type == "placements":
        rows = PlacementApplication.objects.select_related("student", "drive__company", "drive__college")
        if not is_company: rows = rows.filter(drive__college=request.user.college)
        writer.writerow(["College", "Student", "Company", "Role", "Status", "Applied at"])
        for item in rows.iterator():
            writer.writerow([item.drive.college, item.student.get_full_name, item.drive.company, item.drive.role_title, item.status, item.applied_at.isoformat()])
    else:
        return HttpResponseBadRequest("Unknown or unauthorized report type")
    _audit(request, "report.export", request.user, f"Exported {report_type} report", request.user.college)
    return response
