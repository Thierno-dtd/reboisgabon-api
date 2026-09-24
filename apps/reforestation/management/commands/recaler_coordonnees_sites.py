import random
from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.reforestation.management.commands.seed_data import LOCALITES
from apps.reforestation.models import SiteReboisement
from apps.reforestation.utils import coordonnees_pour


class Command(BaseCommand):
    help = "Rattache chaque site à la province réelle de sa localité et le place sur la carte, à l'intérieur de cette province."

    def handle(self, *args, **options):
        provinces = dict(LOCALITES)
        total = 0
        for site in SiteReboisement.objects.all():
            province = provinces.get(site.localite, site.province)
            coordonnees = coordonnees_pour(site.localite, province, random.Random(str(site.id)))
            if coordonnees is None:
                continue
            site.province = province
            site.latitude = Decimal(str(coordonnees[0]))
            site.longitude = Decimal(str(coordonnees[1]))
            site.save(update_fields=['province', 'latitude', 'longitude'])
            total += 1
        self.stdout.write(self.style.SUCCESS(f"{total} sites recalés sur leur localité et leur province."))
