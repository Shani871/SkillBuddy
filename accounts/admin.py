from django.contrib import admin
from .models import User, Student, Parent


class UserAdmin(admin.ModelAdmin):
    list_display = [
        "get_full_name",
        "username",
        "email",
        "role",
        "college_name",
        "college",
        "login_disabled",
        "is_active",
        "is_student",
        "is_lecturer",
        "is_parent",
        "is_staff",
    ]
    list_filter = ["role", "college", "is_active", "login_disabled"]
    search_fields = [
        "username",
        "first_name",
        "last_name",
        "email",
        "is_active",
        "is_lecturer",
        "is_parent",
        "is_staff",
    ]

    class Meta:
        managed = True
        verbose_name = "User"
        verbose_name_plural = "Users"


admin.site.register(User, UserAdmin)
admin.site.register(Student)
admin.site.register(Parent)
