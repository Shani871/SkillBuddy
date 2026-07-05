from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from datetime import datetime, timedelta

from django.db.models import Avg, Q
from django.utils import timezone

from accounts.decorators import admin_required, lecturer_required, student_required
from accounts.models import User, Student
from result.models import CourseAttendance, Result, TakenCourse
from course.models import AcademicEvent, ClassSchedule, Course, CourseAllocation, Program
from .forms import SessionForm, SemesterForm, NewsAndEventsForm
from .models import NewsAndEvents, ActivityLog, Session, Semester


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
    items = NewsAndEvents.objects.all().order_by("-updated_date")
    context = {
        "title": "News & Events",
        "items": items,
    }
    return render(request, "index.html", context)

def new_event(request):
    items = NewsAndEvents.objects.all().order_by("-updated_date")
    context = {
        "title": "News & Events",
        "items": items,
    }
    return render(request, "core/index.html", context)
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
    }
    return render(request, "core/dashboard.html", context)


@login_required
def post_add(request):
    if request.method == "POST":
        form = NewsAndEventsForm(request.POST)
        title = form.cleaned_data.get("title", "Post") if form.is_valid() else None
        if form.is_valid():
            form.save()
            messages.success(request, f"{title} has been uploaded.")
            return redirect("home")
        messages.error(request, "Please correct the error(s) below.")
    else:
        form = NewsAndEventsForm()
    return render(request, "core/post_add.html", {"title": "Add Post", "form": form})


@login_required
@lecturer_required
def edit_post(request, pk):
    instance = get_object_or_404(NewsAndEvents, pk=pk)
    if request.method == "POST":
        form = NewsAndEventsForm(request.POST, instance=instance)
        title = form.cleaned_data.get("title", "Post") if form.is_valid() else None
        if form.is_valid():
            form.save()
            messages.success(request, f"{title} has been updated.")
            return redirect("home")
        messages.error(request, "Please correct the error(s) below.")
    else:
        form = NewsAndEventsForm(instance=instance)
    return render(request, "core/post_add.html", {"title": "Edit Post", "form": form})


@login_required
@lecturer_required
def delete_post(request, pk):
    post = get_object_or_404(NewsAndEvents, pk=pk)
    post_title = post.title
    post.delete()
    messages.success(request, f"{post_title} has been deleted.")
    return redirect("home")


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
