from django.contrib import admin

from .models import AuditEvent, College, CustomRole, PlacementApplication, PlacementCompany, PlacementDrive, SupportTicket


@admin.register(College)
class CollegeAdmin(admin.ModelAdmin):
    list_display = ("name", "domain", "status", "plan", "subscription_ends_on", "storage_limit_gb")
    list_filter = ("status", "plan", "ai_enabled", "payments_enabled")
    search_fields = ("name", "code", "domain", "contact_email")


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor", "action", "target_type", "college")
    list_filter = ("action", "target_type", "college")
    readonly_fields = ("actor", "college", "action", "target_type", "target_id", "description", "ip_address", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


admin.site.register(PlacementCompany)
admin.site.register(PlacementDrive)
admin.site.register(PlacementApplication)
admin.site.register(SupportTicket)
admin.site.register(CustomRole)
