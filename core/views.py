from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from datetime import datetime, timedelta

from django.db.models import Avg, Count, Q, Sum
from django.utils import timezone

from accounts.decorators import admin_required, lecturer_required, student_required
from accounts.models import User, Student
from result.models import CourseAttendance, Result, TakenCourse
from course.models import AcademicEvent, ClassSchedule, Course, CourseAllocation, Program
from .forms import SessionForm, SemesterForm, NewsAndEventsForm
from .models import NewsAndEvents, ActivityLog, Session, Semester
from .role_workspaces import ROLE_WORKSPACES, allowed_features, feature_label, feature_slug
from enterprise.models import College, PlacementApplication, PlacementCompany, PlacementDrive, SupportTicket


def _student_enrollments(request):
    return TakenCourse.objects.select_related("course", "student__student").filter(
        student__student=request.user
    )


def _student_events(request):
    course_ids = _student_enrollments(request).values_list("course_id", flat=True)
    return AcademicEvent.objects.select_related("course").filter(
        Q(course__isnull=True) | Q(course_id__in=course_ids)
    )


@login_required
@student_required
def student_schedule(request):
    now = timezone.localtime()
    selected_day = request.GET.get("day")
    try:
        selected_day = int(selected_day) if selected_day is not None else now.weekday()
    except (TypeError, ValueError):
        selected_day = now.weekday()
    if selected_day not in range(7):
        selected_day = now.weekday()

    mode = request.GET.get("view", "day")
    course_ids = _student_enrollments(request).values_list("course_id", flat=True)
    schedule_query = ClassSchedule.objects.select_related("course", "faculty").filter(
        course_id__in=course_ids
    )
    if mode == "day":
        schedule_query = schedule_query.filter(day_of_week=selected_day)
    else:
        mode = "week"
    schedules = list(schedule_query)
    for item in schedules:
        item.is_current = (
            item.day_of_week == now.weekday()
            and item.start_time <= now.time() <= item.end_time
        )
        item.is_upcoming = False
    if not any(item.is_current for item in schedules):
        upcoming_today = [
            item
            for item in schedules
            if item.day_of_week == now.weekday() and item.start_time > now.time()
        ]
        if upcoming_today:
            min(upcoming_today, key=lambda item: item.start_time).is_upcoming = True

    return render(
        request,
        "student/schedule.html",
        {
            "title": "Schedule",
            "schedules": schedules,
            "selected_day": selected_day,
            "mode": mode,
            "weekdays": ClassSchedule.WEEKDAYS,
            "today": now.weekday(),
        },
    )


@login_required
@student_required
def student_attendance(request):
    rows = []
    for enrollment in _student_enrollments(request):
        summary = getattr(enrollment, "attendance_summary", None)
        total = summary.total_classes if summary else 0
        attended = summary.classes_attended if summary else 0
        required = summary.required_percentage if summary else 75
        percentage = summary.percentage if summary else 0
        rows.append(
            {
                "course": enrollment.course,
                "total": total,
                "attended": attended,
                "required": required,
                "percentage": percentage,
                "below_required": percentage < required,
            }
        )
    return render(
        request,
        "student/attendance.html",
        {"title": "Attendance", "attendance_rows": rows},
    )


@login_required
@student_required
def student_calendar(request):
    today = timezone.localdate()
    try:
        focus_date = datetime.strptime(request.GET.get("date", ""), "%Y-%m-%d").date()
    except ValueError:
        focus_date = today
    mode = request.GET.get("view", "month")
    if mode == "day":
        range_start, range_end = focus_date, focus_date
    elif mode == "week":
        range_start = focus_date - timedelta(days=focus_date.weekday())
        range_end = range_start + timedelta(days=6)
    else:
        mode = "month"
        range_start = focus_date.replace(day=1)
        next_month = (range_start.replace(day=28) + timedelta(days=4)).replace(day=1)
        range_end = next_month - timedelta(days=1)
    events = _student_events(request).filter(
        start_at__date__gte=range_start, start_at__date__lte=range_end
    )
    course_ids = _student_enrollments(request).values_list("course_id", flat=True)
    weekly_classes = list(
        ClassSchedule.objects.select_related("course", "faculty").filter(
            course_id__in=course_ids
        )
    )
    class_occurrences = []
    date_cursor = range_start
    while date_cursor <= range_end:
        for class_schedule in weekly_classes:
            if class_schedule.day_of_week == date_cursor.weekday():
                class_occurrences.append(
                    {"date": date_cursor, "schedule": class_schedule}
                )
        date_cursor += timedelta(days=1)
    return render(
        request,
        "student/calendar.html",
        {
            "title": "Calendar",
            "events": events,
            "class_occurrences": class_occurrences,
            "mode": mode,
            "focus_date": focus_date,
            "range_start": range_start,
            "range_end": range_end,
            "previous_date": range_start - timedelta(days=1),
            "next_date": range_end + timedelta(days=1),
        },
    )


@login_required
@student_required
def academic_calendar(request):
    events = _student_events(request)
    event_groups = [
        (label, events.filter(event_type=value))
        for value, label in AcademicEvent.EVENT_TYPES
    ]
    return render(
        request,
        "student/academic_calendar.html",
        {"title": "Academic Calendar", "event_groups": event_groups},
    )


# ########################################################
# News & Events
# ########################################################
@login_required
def home_view(request):
    if request.user.effective_role in ROLE_WORKSPACES:
        return redirect("role_dashboard")
    if request.user.is_superuser:
        return redirect("dashboard")
    if request.user.is_lecturer:
        return redirect("teacher_dashboard")
    if request.user.is_student:
        return redirect("user_course_list")
    return redirect("profile")


def _workspace_metric_values(request):
    user_scope = User.objects.all()
    tenant = None if request.user.effective_role == User.ROLE_SUPER_ADMIN else request.user.college
    if tenant:
        user_scope = user_scope.filter(college=tenant)
    elif request.user.effective_role != User.ROLE_SUPER_ADMIN:
        user_scope = user_scope.filter(pk=request.user.pk)
    students = user_scope.filter(Q(is_student=True) | Q(role="student")).distinct().count()
    faculty = user_scope.filter(Q(is_lecturer=True) | Q(role="faculty")).distinct().count()
    users = user_scope.filter(is_active=True, login_disabled=False).count()
    colleges = College.objects.count()
    revenue = College.objects.filter(status="active").aggregate(total=Sum("monthly_price"))["total"] or 0
    company_scope = request.user.effective_role == User.ROLE_SUPER_ADMIN
    courses = Course.objects.count() if company_scope else 0
    placement_companies = PlacementCompany.objects.filter(is_active=True)
    placement_drives = PlacementDrive.objects.all()
    placement_applications = PlacementApplication.objects.all()
    tickets = SupportTicket.objects.exclude(status="resolved")
    if tenant:
        placement_companies = placement_companies.filter(college=tenant)
        placement_drives = placement_drives.filter(college=tenant)
        placement_applications = placement_applications.filter(drive__college=tenant)
        tickets = tickets.filter(college=tenant)
    elif not company_scope:
        placement_companies = placement_companies.none()
        placement_drives = placement_drives.none()
        placement_applications = placement_applications.none()
        tickets = tickets.none()
    return {
        "Total Colleges": colleges, "Active Colleges": College.objects.filter(status="active").count(), "Trial Colleges": College.objects.filter(status="trial").count(),
        "Subscription Revenue": f"₹{revenue:,.0f}", "Active Users": users, "Total Students": students,
        "Total Faculty": faculty, "Total Courses": courses, "AI Usage": "0 credits",
        "Storage Usage": "0 GB", "Server Health": "Operational", "Payment Status": "Current",
        "Support Tickets": tickets.count(), "Departments": user_scope.exclude(department_name="").values("department_name").distinct().count(), "Attendance": CourseAttendance.objects.count() if tenant is None else 0,
        "Results": Result.objects.count(), "Placement Rate": "0%", "Fees": "₹0",
        "High Risk Students": 0, "Notifications": NewsAndEvents.objects.count(),
        "Department Students": students, "Faculty": faculty, "Department Analytics": "View",
        "Risk Students": 0, "Approvals": 0, "Reports": Result.objects.count(),
        "Today's Classes": ClassSchedule.objects.filter(day_of_week=timezone.localtime().weekday()).count(),
        "Assignments": 0, "Quizzes": 0, "Student Performance": "View",
        "Courses": courses, "Certificates": 0, "Placement Tracker": "View",
        "Eligible Students": students, "Companies": placement_companies.count(),
        "Interviews": placement_drives.filter(status="interview").count(),
        "Offers": placement_applications.filter(status__in=("offered", "accepted")).count(),
        "Placed Students": placement_applications.filter(status="accepted").values("student_id").distinct().count(), "Resume Reviews": 0,
    }


@login_required
def role_dashboard(request):
    role = request.user.effective_role
    workspace = ROLE_WORKSPACES.get(role)
    if not workspace:
        return redirect("profile")
    values = _workspace_metric_values(request)
    sections = [
        {"name": name, "features": [{"label": label, "slug": feature_slug(label)} for label in labels]}
        for name, labels in workspace["sections"].items()
    ]
    metrics = [{"label": label, "value": values.get(label, 0), "slug": feature_slug(label)} for label in workspace["metrics"]]
    return render(request, "core/role_dashboard.html", {
        "workspace": workspace, "sections": sections, "metrics": metrics,
        "recent_users": User.objects.all()[:6], "recent_activity": ActivityLog.objects.all().order_by("-created_at")[:6],
    })


@login_required
def role_module(request, feature):
    role = request.user.effective_role
    custom_permissions = set(request.user.custom_role.permissions) if request.user.custom_role_id and request.user.custom_role.is_active else set()
    if feature not in allowed_features(role) and feature not in custom_permissions:
        return render(request, "403.html", status=403)
    label = feature_label(role, feature)
    real_routes = {
        "add-college": "enterprise:college_create",
        "edit-college": "enterprise:college_list", "delete-college": "enterprise:college_list",
        "activate-college": "enterprise:college_list", "suspend-college": "enterprise:college_list",
        "extend-subscription": "enterprise:college_list", "upgrade-plan": "enterprise:college_list",
        "change-domain": "enterprise:college_list", "assign-storage": "enterprise:college_list",
        "view-college-analytics": "enterprise:college_list", "total-colleges": "enterprise:college_list",
        "active-colleges": "enterprise:college_list", "trial-colleges": "enterprise:college_list",
        "view-college-users": "enterprise:user_list", "create-student": "enterprise:user_create",
        "create-faculty": "enterprise:user_create", "reset-password": "enterprise:user_list",
        "lock-user": "enterprise:user_list", "unlock-user": "enterprise:user_list",
        "disable-login": "enterprise:user_list", "activate-user": "enterprise:user_list",
        "assign-role": "enterprise:user_list", "change-department": "enterprise:user_list",
        "verify-email": "enterprise:user_list", "force-logout": "enterprise:user_list",
        "students": "enterprise:user_list", "faculty": "enterprise:user_list",
        "placements": "enterprise:placement_dashboard", "eligible-students": "enterprise:placement_dashboard",
        "companies": "enterprise:placement_dashboard", "interviews": "enterprise:placement_dashboard",
        "offers": "enterprise:placement_dashboard", "placed-students": "enterprise:placement_dashboard",
        "placement-tracker": "enterprise:placement_dashboard",
        "server-reports": "enterprise:reports", "active-users": "enterprise:reports",
        "support-tickets": "enterprise:ticket_list",
        "college-logo": "enterprise:tenant_settings", "theme": "enterprise:tenant_settings",
        "email-settings": "enterprise:tenant_settings", "sms-settings": "enterprise:tenant_settings",
        "ai-settings": "enterprise:tenant_settings", "payment-settings": "enterprise:tenant_settings",
        "branding": "enterprise:tenant_settings",
        "create-roles": "enterprise:role_create", "assign-roles": "enterprise:user_list",
        "edit-roles": "enterprise:role_list", "delete-roles": "enterprise:role_list",
        "permission-matrix": "enterprise:role_list",
        "revenue": "enterprise:reports", "subscriptions": "enterprise:reports",
        "renewals": "enterprise:reports", "reports": "enterprise:reports",
        "analytics": "enterprise:reports", "department-analytics": "enterprise:reports",
    }
    if feature in real_routes:
        return redirect(real_routes[feature])
    records = User.objects.all()[:8] if any(word in feature for word in ("user", "student", "faculty", "role")) else Course.objects.all()[:8]
    return render(request, "core/role_module.html", {
        "workspace": ROLE_WORKSPACES[role], "feature": label, "records": records,
    })

@login_required
def new_event(request):
    items = NewsAndEvents.objects.all().order_by("-upload_time", "-pk")
    query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()
    if query:
        items = items.filter(
            Q(title__icontains=query)
            | Q(summary__icontains=query)
            | Q(content__icontains=query)
        )
    if category in {"News", "Event"}:
        items = items.filter(posted_as=category)
    page_obj = Paginator(items, 9).get_page(request.GET.get("page"))
    context = {
        "title": "News & Events",
        "items": page_obj,
        "page_obj": page_obj,
        "query": query,
        "category": category,
    }
    return render(request, "core/index.html", context)


@login_required
def news_event_detail(request, pk):
    item = get_object_or_404(NewsAndEvents, pk=pk)
    return render(request, "core/news_event_detail.html", {"title": item.title, "item": item})
@login_required
def dashboard_view(request):
    if request.user.is_lecturer:
        return redirect("teacher_dashboard")
    if not request.user.is_superuser:
        return redirect("home")

    logs = ActivityLog.objects.all().order_by("-created_at")[:10]
    gender_count = Student.get_gender_count()
    graded_courses = TakenCourse.objects.exclude(grade="").exclude(total=0)
    result_summary = {
        "published_count": Result.objects.count(),
        "graded_course_count": graded_courses.count(),
        "pass_count": graded_courses.filter(comment="PASS").count(),
        "fail_count": graded_courses.filter(comment="FAIL").count(),
        "avg_cgpa": Result.objects.exclude(cgpa__isnull=True).aggregate(
            avg_cgpa=Avg("cgpa")
        )["avg_cgpa"],
    }
    top_courses = list(
        Course.objects.annotate(student_total=Count("taken_courses"))
        .order_by("-student_total", "title")
        .values("title", "student_total")[:6]
    )
    chart_data = {
        "course_labels": [item["title"] for item in top_courses],
        "course_values": [item["student_total"] for item in top_courses],
        "role_labels": ["Students", "Lecturers", "Administrators"],
        "role_values": [
            User.objects.filter(is_student=True).count(),
            User.objects.filter(is_lecturer=True).count(),
            User.objects.filter(is_superuser=True).count(),
        ],
        "outcome_labels": ["Passed", "Failed", "Awaiting grade"],
        "outcome_values": [
            result_summary["pass_count"],
            result_summary["fail_count"],
            TakenCourse.objects.filter(grade="").count(),
        ],
        "gender_labels": ["Male", "Female"],
        "gender_values": [gender_count["M"], gender_count["F"]],
    }
    context = {
        "student_count": User.objects.get_student_count(),
        "lecturer_count": User.objects.get_lecturer_count(),
        "superuser_count": User.objects.get_superuser_count(),
        "males_count": gender_count["M"],
        "females_count": gender_count["F"],
        "result_summary": result_summary,
        "logs": logs,
        "program_count": Program.objects.count(),
        "course_count": Course.objects.count(),
        "allocation_count": CourseAllocation.objects.count(),
        "enrollment_count": TakenCourse.objects.count(),
        "schedule_count": ClassSchedule.objects.count(),
        "attendance_count": CourseAttendance.objects.count(),
        "academic_event_count": AcademicEvent.objects.count(),
        "announcement_count": NewsAndEvents.objects.count(),
        "chart_data": chart_data,
    }
    return render(request, "core/dashboard.html", context)


@login_required
@admin_required
def post_add(request):
    if request.method == "POST":
        form = NewsAndEventsForm(request.POST, request.FILES)
        title = form.cleaned_data.get("title", "Post") if form.is_valid() else None
        if form.is_valid():
            form.save()
            messages.success(request, f"{title} has been uploaded.")
            return redirect("news_event_detail", pk=form.instance.pk)
        messages.error(request, "Please correct the error(s) below.")
    else:
        form = NewsAndEventsForm()
    return render(request, "core/post_add.html", {"title": "Add Post", "form": form})


@login_required
@admin_required
def edit_post(request, pk):
    instance = get_object_or_404(NewsAndEvents, pk=pk)
    if request.method == "POST":
        form = NewsAndEventsForm(request.POST, request.FILES, instance=instance)
        title = form.cleaned_data.get("title", "Post") if form.is_valid() else None
        if form.is_valid():
            form.save()
            messages.success(request, f"{title} has been updated.")
            return redirect("news_event_detail", pk=instance.pk)
        messages.error(request, "Please correct the error(s) below.")
    else:
        form = NewsAndEventsForm(instance=instance)
    return render(request, "core/post_add.html", {"title": "Edit Post", "form": form})


@login_required
@admin_required
def delete_post(request, pk):
    post = get_object_or_404(NewsAndEvents, pk=pk)
    post_title = post.title
    post.delete()
    messages.success(request, f"{post_title} has been deleted.")
    return redirect("news_event")


# ########################################################
# Session
# ########################################################
@login_required
@lecturer_required
def session_list_view(request):
    """Show list of all sessions"""
    sessions = Session.objects.all().order_by("-is_current_session", "-session")
    return render(request, "core/session_list.html", {"sessions": sessions})


@login_required
@lecturer_required
def session_add_view(request):
    """Add a new session"""
    if request.method == "POST":
        form = SessionForm(request.POST)
        if form.is_valid():
            if form.cleaned_data.get("is_current_session"):
                unset_current_session()
            form.save()
            messages.success(request, "Session added successfully.")
            return redirect("session_list")
    else:
        form = SessionForm()
    return render(request, "core/session_update.html", {"form": form})


@login_required
@lecturer_required
def session_update_view(request, pk):
    session = get_object_or_404(Session, pk=pk)
    if request.method == "POST":
        form = SessionForm(request.POST, instance=session)
        if form.is_valid():
            if form.cleaned_data.get("is_current_session"):
                unset_current_session()
            form.save()
            messages.success(request, "Session updated successfully.")
            return redirect("session_list")
    else:
        form = SessionForm(instance=session)
    return render(request, "core/session_update.html", {"form": form})


@login_required
@lecturer_required
def session_delete_view(request, pk):
    session = get_object_or_404(Session, pk=pk)
    if session.is_current_session:
        messages.error(request, "You cannot delete the current session.")
    else:
        session.delete()
        messages.success(request, "Session successfully deleted.")
    return redirect("session_list")


def unset_current_session():
    """Unset current session"""
    current_session = Session.objects.filter(is_current_session=True).first()
    if current_session:
        current_session.is_current_session = False
        current_session.save()


# ########################################################
# Semester
# ########################################################
@login_required
@lecturer_required
def semester_list_view(request):
    semesters = Semester.objects.all().order_by("-is_current_semester", "-semester")
    return render(request, "core/semester_list.html", {"semesters": semesters})


@login_required
@lecturer_required
def semester_add_view(request):
    if request.method == "POST":
        form = SemesterForm(request.POST)
        if form.is_valid():
            if form.cleaned_data.get("is_current_semester"):
                unset_current_semester()
                unset_current_session()
            form.save()
            messages.success(request, "Semester added successfully.")
            return redirect("semester_list")
    else:
        form = SemesterForm()
    return render(request, "core/semester_update.html", {"form": form})


@login_required
@lecturer_required
def semester_update_view(request, pk):
    semester = get_object_or_404(Semester, pk=pk)
    if request.method == "POST":
        form = SemesterForm(request.POST, instance=semester)
        if form.is_valid():
            if form.cleaned_data.get("is_current_semester"):
                unset_current_semester()
                unset_current_session()
            form.save()
            messages.success(request, "Semester updated successfully!")
            return redirect("semester_list")
    else:
        form = SemesterForm(instance=semester)
    return render(request, "core/semester_update.html", {"form": form})


@login_required
@lecturer_required
def semester_delete_view(request, pk):
    semester = get_object_or_404(Semester, pk=pk)
    if semester.is_current_semester:
        messages.error(request, "You cannot delete the current semester.")
    else:
        semester.delete()
        messages.success(request, "Semester successfully deleted.")
    return redirect("semester_list")


def unset_current_semester():
    """Unset current semester"""
    current_semester = Semester.objects.filter(is_current_semester=True).first()
    if current_semester:
        current_semester.is_current_semester = False
        current_semester.save()
