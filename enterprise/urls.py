from django.urls import path
from . import views

app_name = "enterprise"

urlpatterns = [
    path("colleges/", views.college_list, name="college_list"),
    path("colleges/add/", views.college_create, name="college_create"),
    path("colleges/<int:pk>/edit/", views.college_edit, name="college_edit"),
    path("colleges/<int:pk>/<slug:action>/", views.college_action, name="college_action"),
    path("users/", views.user_list, name="user_list"),
    path("users/add/", views.user_create, name="user_create"),
    path("users/<int:pk>/edit/", views.user_edit, name="user_edit"),
    path("users/<int:pk>/<slug:action>/", views.user_action, name="user_action"),
    path("placements/", views.placement_dashboard, name="placement_dashboard"),
    path("placements/companies/add/", views.company_create, name="company_create"),
    path("placements/drives/add/", views.drive_create, name="drive_create"),
    path("placements/drives/<int:pk>/apply/", views.apply_to_drive, name="apply_to_drive"),
    path("placements/applications/<int:pk>/status/", views.application_status, name="application_status"),
    path("audit/", views.audit_log, name="audit_log"),
    path("settings/", views.tenant_settings, name="tenant_settings"),
    path("settings/<int:pk>/", views.tenant_settings, name="tenant_settings_for"),
    path("support/", views.ticket_list, name="ticket_list"),
    path("support/add/", views.ticket_create, name="ticket_create"),
    path("support/<int:pk>/status/", views.ticket_status, name="ticket_status"),
    path("roles/", views.role_list, name="role_list"),
    path("roles/add/", views.role_create, name="role_create"),
    path("roles/<int:pk>/edit/", views.role_edit, name="role_edit"),
    path("roles/<int:pk>/delete/", views.role_delete, name="role_delete"),
    path("reports/", views.reports_dashboard, name="reports"),
    path("reports/export/<slug:report_type>/", views.export_report, name="export_report"),
]
