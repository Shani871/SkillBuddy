from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0002_initial")]

    operations = [
        migrations.AddField(
            model_name="user",
            name="role",
            field=models.CharField(blank=True, choices=[
                ("super_admin", "Super Admin"),
                ("college_admin", "College Admin / Principal"),
                ("hod", "Head of Department"),
                ("faculty", "Faculty"),
                ("student", "Student"),
                ("placement_officer", "Placement Officer"),
            ], max_length=32),
        ),
        migrations.AddField(model_name="user", name="college_name", field=models.CharField(blank=True, max_length=160)),
        migrations.AddField(model_name="user", name="department_name", field=models.CharField(blank=True, max_length=120)),
    ]
