import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [migrations.CreateModel(
        name="College",
        fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("name", models.CharField(max_length=180)),
            ("code", models.SlugField(max_length=40, unique=True)),
            ("domain", models.CharField(max_length=180, unique=True)),
            ("contact_email", models.EmailField(max_length=254)),
            ("contact_phone", models.CharField(blank=True, max_length=30)),
            ("status", models.CharField(choices=[("trial", "Trial"), ("active", "Active"), ("suspended", "Suspended")], default="trial", max_length=16)),
            ("plan", models.CharField(choices=[("starter", "Starter"), ("professional", "Professional"), ("enterprise", "Enterprise")], default="starter", max_length=20)),
            ("subscription_ends_on", models.DateField(blank=True, null=True)),
            ("monthly_price", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
            ("storage_limit_gb", models.PositiveIntegerField(default=10, validators=[django.core.validators.MinValueValidator(1)])),
            ("storage_used_mb", models.PositiveBigIntegerField(default=0)),
            ("primary_color", models.CharField(default="#2563eb", max_length=7)),
            ("logo", models.ImageField(blank=True, upload_to="college_logos/")),
            ("ai_enabled", models.BooleanField(default=True)),
            ("ai_monthly_credit_limit", models.PositiveIntegerField(default=10000)),
            ("payments_enabled", models.BooleanField(default=False)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("updated_at", models.DateTimeField(auto_now=True)),
        ],
        options={"ordering": ("name",)},
    )]
