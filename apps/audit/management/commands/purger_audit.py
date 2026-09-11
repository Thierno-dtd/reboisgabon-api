from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.audit.models import JournalActivite


class Command(BaseCommand):
    help = "Purge les entrées d'audit antérieures à --jours jours (défaut : 365)."

    def add_arguments(self, parser):
        parser.add_argument('--jours', type=int, default=365)

    def handle(self, *args, **options):
        limite = timezone.now() - timedelta(days=options['jours'])
        qs = JournalActivite.objects.filter(date_action__lt=limite)
        nb = qs.count()
        qs.delete()
        self.stdout.write(self.style.SUCCESS(
            f"{nb} entrée(s) purgée(s) (antérieures à {options['jours']} jours)."
        ))