import os
import logging

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

logger = logging.getLogger(__name__)

app = Celery("skillbuddy")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    logger.debug("Celery debug task request: %r", self.request)
