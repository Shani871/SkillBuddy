from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from emotions.models import EmotionAlert
from emotions.services import EmotionAnalysisService


class Command(BaseCommand):
    help = "Resend unread emotion alerts older than a given number of hours."

    def add_arguments(self, parser):
        parser.add_argument(
            "--hours",
            type=int,
            default=24,
            help="Minimum age in hours for unread alerts to be resent (default: 24).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be resent without sending notifications.",
        )

    def handle(self, *args, **options):
        hours = options["hours"]
        dry_run = options["dry_run"]
        cutoff = timezone.now() - timedelta(hours=hours)

        alerts = EmotionAlert.objects.select_related("student__student").filter(
            is_read=False,
            timestamp__lte=cutoff,
        )

        total = alerts.count()
        self.stdout.write(
            f"Found {total} unread alert(s) older than {hours} hour(s)."
        )

        processed = 0
        for alert in alerts:
            if dry_run:
                self.stdout.write(
                    f"[DRY RUN] Would resend alert #{alert.id} for {alert.student}"
                )
            else:
                EmotionAnalysisService.dispatch_alert_notifications(alert.id)
                self.stdout.write(f"Resent alert #{alert.id} for {alert.student}")
            processed += 1

        self.stdout.write(self.style.SUCCESS(f"Done. Processed {processed} alert(s)."))
