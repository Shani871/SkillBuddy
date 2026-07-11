from django.urls import path

from .views import (
    home_view,
    post_add,
    edit_post,
    delete_post,
    session_list_view,
    session_add_view,
    session_update_view,
    session_delete_view,
    semester_list_view,
    semester_add_view,
    semester_update_view,
    semester_delete_view,
    dashboard_view, new_event, news_event_detail,
    student_schedule,
    student_attendance,
    student_calendar,
    academic_calendar,
    role_dashboard,
    role_module,
)


urlpatterns = [
    # Accounts url
    path("", home_view, name="home"),
    path("news-events/", new_event, name="news_event"),
    path("news-events/<int:pk>/", news_event_detail, name="news_event_detail"),
    path("add_item/", post_add, name="add_item"),
    path("item/<int:pk>/edit/", edit_post, name="edit_post"),
    path("item/<int:pk>/delete/", delete_post, name="delete_post"),
    path("session/", session_list_view, name="session_list"),
    path("session/add/", session_add_view, name="add_session"),
    path("session/<int:pk>/edit/", session_update_view, name="edit_session"),
    path("session/<int:pk>/delete/", session_delete_view, name="delete_session"),
    path("semester/", semester_list_view, name="semester_list"),
    path("semester/add/", semester_add_view, name="add_semester"),
    path("semester/<int:pk>/edit/", semester_update_view, name="edit_semester"),
    path("semester/<int:pk>/delete/", semester_delete_view, name="delete_semester"),
    path("dashboard/", dashboard_view, name="dashboard"),
    path("workspace/", role_dashboard, name="role_dashboard"),
    path("workspace/<slug:feature>/", role_module, name="role_module"),
    path("student/schedule/", student_schedule, name="student_schedule"),
    path("student/attendance/", student_attendance, name="student_attendance"),
    path("student/calendar/", student_calendar, name="student_calendar"),
    path("student/academic-calendar/", academic_calendar, name="academic_calendar"),
]
