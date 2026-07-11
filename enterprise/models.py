from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class College(models.Model):
    STATUS_CHOICES = (("trial", "Trial"), ("active", "Active"), ("suspended", "Suspended"))
    PLAN_CHOICES = (("starter", "Starter"), ("professional", "Professional"), ("enterprise", "Enterprise"))

    name = models.CharField(max_length=180)
    code = models.SlugField(max_length=40, unique=True)
    domain = models.CharField(max_length=180, unique=True)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=30, blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="trial")
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default="starter")
    subscription_ends_on = models.DateField(null=True, blank=True)
    monthly_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    storage_limit_gb = models.PositiveIntegerField(default=10, validators=[MinValueValidator(1)])
    storage_used_mb = models.PositiveBigIntegerField(default=0)
    primary_color = models.CharField(max_length=7, default="#2563eb")
    logo = models.ImageField(upload_to="college_logos/", blank=True)
    ai_enabled = models.BooleanField(default=True)
    ai_monthly_credit_limit = models.PositiveIntegerField(default=10000)
    payments_enabled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name

    @property
    def subscription_is_current(self):
        return not self.subscription_ends_on or self.subscription_ends_on >= timezone.localdate()


class CustomRole(models.Model):
    college = models.ForeignKey(College, related_name="custom_roles", null=True, blank=True, on_delete=models.CASCADE)
    name = models.CharField(max_length=80)
    slug = models.SlugField(max_length=80)
    description = models.CharField(max_length=240, blank=True)
    permissions = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)
        constraints = [models.UniqueConstraint(fields=("college", "slug"), name="unique_custom_role_per_college")]

    def __str__(self):
        return self.name


class PlacementCompany(models.Model):
    college = models.ForeignKey(College, related_name="placement_companies", on_delete=models.CASCADE)
    name = models.CharField(max_length=160)
    website = models.URLField(blank=True)
    contact_name = models.CharField(max_length=120, blank=True)
    contact_email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("name",)
        constraints = [models.UniqueConstraint(fields=("college", "name"), name="unique_company_per_college")]

    def __str__(self):
        return self.name


class PlacementDrive(models.Model):
    STATUS_CHOICES = (("draft", "Draft"), ("open", "Open"), ("interview", "Interview"), ("completed", "Completed"))
    college = models.ForeignKey(College, related_name="placement_drives", on_delete=models.CASCADE)
    company = models.ForeignKey(PlacementCompany, related_name="drives", on_delete=models.CASCADE)
    title = models.CharField(max_length=180)
    role_title = models.CharField(max_length=160)
    minimum_cgpa = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    salary_package = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    application_deadline = models.DateField()
    interview_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.company} · {self.role_title}"


class PlacementApplication(models.Model):
    STATUS_CHOICES = (("applied", "Applied"), ("shortlisted", "Shortlisted"), ("interview", "Interview"), ("offered", "Offered"), ("rejected", "Rejected"), ("accepted", "Accepted"))
    drive = models.ForeignKey(PlacementDrive, related_name="applications", on_delete=models.CASCADE)
    student = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="placement_applications", on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="applied")
    notes = models.TextField(blank=True)
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("drive", "student"), name="unique_drive_student_application")]


class SupportTicket(models.Model):
    STATUS_CHOICES = (("open", "Open"), ("in_progress", "In progress"), ("resolved", "Resolved"))
    college = models.ForeignKey(College, related_name="support_tickets", null=True, blank=True, on_delete=models.SET_NULL)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="support_tickets", null=True, on_delete=models.SET_NULL)
    subject = models.CharField(max_length=200)
    description = models.TextField()
    priority = models.CharField(max_length=12, choices=(("low", "Low"), ("normal", "Normal"), ("high", "High"), ("urgent", "Urgent")), default="normal")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="open")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class AuditEvent(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="audit_events", null=True, on_delete=models.SET_NULL)
    college = models.ForeignKey(College, related_name="audit_events", null=True, blank=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=80)
    target_type = models.CharField(max_length=80)
    target_id = models.CharField(max_length=80, blank=True)
    description = models.CharField(max_length=255)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
