from django.core.cache import cache
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from apps.reforestation.models import SiteReboisement, CampagnePlantation, SuiviCroissance
from apps.finances.models import Financement, BudgetCampagne

CACHE_KEYS_A_INVALIDER = [
    'dashboard:overview', 'dashboard:sites', 'dashboard:essences',
    'dashboard:provinces', 'dashboard:evolution', 'dashboard:financier',
]

MODELES_DECLENCHEURS = [
    SiteReboisement, CampagnePlantation, SuiviCroissance, Financement, BudgetCampagne,
]


def invalider_cache_dashboard(sender, **kwargs):
    cache.delete_many(CACHE_KEYS_A_INVALIDER)


for modele in MODELES_DECLENCHEURS:
    post_save.connect(invalider_cache_dashboard, sender=modele, weak=False)
    post_delete.connect(invalider_cache_dashboard, sender=modele, weak=False)