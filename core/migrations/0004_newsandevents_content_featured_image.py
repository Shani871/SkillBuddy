from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0003_newsandevents_summary_es_newsandevents_summary_fr_and_more")]

    operations = [
        migrations.AddField(
            model_name="newsandevents",
            name="content",
            field=models.TextField(blank=True, help_text="Full article or event details"),
        ),
        migrations.AddField(
            model_name="newsandevents",
            name="featured_image",
            field=models.ImageField(blank=True, null=True, upload_to="news_events/%Y/%m/"),
        ),
        migrations.AddField(
            model_name="newsandevents",
            name="content_en",
            field=models.TextField(blank=True, help_text="Full article or event details", null=True),
        ),
        migrations.AddField(
            model_name="newsandevents",
            name="content_es",
            field=models.TextField(blank=True, help_text="Full article or event details", null=True),
        ),
        migrations.AddField(
            model_name="newsandevents",
            name="content_fr",
            field=models.TextField(blank=True, help_text="Full article or event details", null=True),
        ),
        migrations.AddField(
            model_name="newsandevents",
            name="content_ru",
            field=models.TextField(blank=True, help_text="Full article or event details", null=True),
        ),
    ]
