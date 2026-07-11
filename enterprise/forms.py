from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils.text import slugify

from accounts.models import User
from .models import College, CustomRole, PlacementCompany, PlacementDrive, SupportTicket
from core.role_workspaces import ROLE_WORKSPACES, feature_slug


class StyledModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "form-check-input"
            else:
                field.widget.attrs["class"] = "form-control"


class CollegeForm(StyledModelForm):
    class Meta:
        model = College
        fields = ("name", "code", "domain", "contact_email", "contact_phone", "status", "plan", "subscription_ends_on", "monthly_price", "storage_limit_gb", "primary_color", "logo", "ai_enabled", "ai_monthly_credit_limit", "payments_enabled")
        widgets = {"subscription_ends_on": forms.DateInput(attrs={"type": "date"}), "primary_color": forms.TextInput(attrs={"type": "color"})}

    def clean_code(self):
        return slugify(self.cleaned_data["code"])

    def clean_domain(self):
        return self.cleaned_data["domain"].lower().strip().removeprefix("https://").removeprefix("http://").rstrip("/")


class TenantSettingsForm(StyledModelForm):
    class Meta:
        model = College
        fields = ("name", "contact_email", "contact_phone", "primary_color", "logo", "ai_enabled", "ai_monthly_credit_limit", "payments_enabled")
        widgets = {"primary_color": forms.TextInput(attrs={"type": "color"})}


class EnterpriseUserForm(StyledModelForm):
    password = forms.CharField(widget=forms.PasswordInput, required=False, help_text="Required for new users; leave blank when editing to keep the current password.")

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email", "phone", "role", "custom_role", "college", "department_name", "is_active", "login_disabled")

    def __init__(self, *args, actor=None, **kwargs):
        self.actor = actor
        super().__init__(*args, **kwargs)
        if actor and actor.effective_role != User.ROLE_SUPER_ADMIN:
            self.fields["college"].queryset = College.objects.filter(pk=actor.college_id)
            self.fields["college"].initial = actor.college
            self.fields["college"].disabled = True
            self.fields["role"].choices = [choice for choice in User.ROLE_CHOICES if choice[0] != User.ROLE_SUPER_ADMIN]
            self.fields["custom_role"].queryset = CustomRole.objects.filter(college=actor.college, is_active=True)
        if not self.instance.pk:
            self.fields["password"].required = True

    def clean_password(self):
        password = self.cleaned_data.get("password")
        if password:
            validate_password(password, self.instance)
        return password

    def clean(self):
        data = super().clean()
        if self.actor and self.actor.effective_role != User.ROLE_SUPER_ADMIN and data.get("role") == User.ROLE_SUPER_ADMIN:
            raise ValidationError("Only a SkillBuddy super administrator can assign that role.")
        return data

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password")
        if password:
            user.set_password(password)
        role = user.role
        user.is_student = role == User.ROLE_STUDENT
        user.is_lecturer = role == User.ROLE_FACULTY
        user.is_dep_head = role == User.ROLE_HOD
        if commit:
            user.save()
        return user


class PlacementCompanyForm(StyledModelForm):
    class Meta:
        model = PlacementCompany
        fields = ("name", "website", "contact_name", "contact_email", "is_active")


class PlacementDriveForm(StyledModelForm):
    class Meta:
        model = PlacementDrive
        fields = ("company", "title", "role_title", "minimum_cgpa", "salary_package", "application_deadline", "interview_date", "status")
        widgets = {"application_deadline": forms.DateInput(attrs={"type": "date"}), "interview_date": forms.DateTimeInput(attrs={"type": "datetime-local"})}

    def __init__(self, *args, college=None, **kwargs):
        super().__init__(*args, **kwargs)
        if college:
            self.fields["company"].queryset = PlacementCompany.objects.filter(college=college, is_active=True)


class SupportTicketForm(StyledModelForm):
    class Meta:
        model = SupportTicket
        fields = ("subject", "description", "priority")
        widgets = {"description": forms.Textarea(attrs={"rows": 5})}


PERMISSION_CHOICES = sorted({
    (feature_slug(label), label)
    for workspace in ROLE_WORKSPACES.values()
    for labels in workspace["sections"].values()
    for label in labels
}, key=lambda item: item[1])


class CustomRoleForm(StyledModelForm):
    permissions = forms.MultipleChoiceField(choices=PERMISSION_CHOICES, widget=forms.CheckboxSelectMultiple, required=False)

    class Meta:
        model = CustomRole
        fields = ("college", "name", "slug", "description", "permissions", "is_active")

    def __init__(self, *args, actor=None, **kwargs):
        super().__init__(*args, **kwargs)
        if actor and actor.effective_role != User.ROLE_SUPER_ADMIN:
            self.fields["college"].queryset = College.objects.filter(pk=actor.college_id)
            self.fields["college"].initial = actor.college
            self.fields["college"].disabled = True

    def clean_slug(self):
        return slugify(self.cleaned_data["slug"])
