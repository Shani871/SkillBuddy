import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("enterprise", "0001_initial"), ("accounts", "0003_user_enterprise_role")]
    operations = [
        migrations.AddField(model_name="user", name="college", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="users", to="enterprise.college")),
        migrations.AddField(model_name="user", name="login_disabled", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="user", name="email_verified_at", field=models.DateTimeField(blank=True, null=True)),
    ]
