from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from apps.reforestation.models import SiteReboisement, CampagnePlantation, SuiviCroissance, Essence
from apps.accounts.models import User
from apps.finances.models import Partenaire, Financement, BudgetCampagne
from .models import JournalActivite
from .middleware import get_current_user, get_current_ip

# Modèles surveillés automatiquement
MODELES_AUDITES = [
    SiteReboisement, CampagnePlantation, SuiviCroissance, Essence,
    User, Partenaire, Financement, BudgetCampagne,
]


def _utilisateur_courant():
    user = get_current_user()
    if user and getattr(user, 'is_authenticated', False):
        return user
    return None


def enregistrer(action, instance):
    JournalActivite.objects.create(
        utilisateur=_utilisateur_courant(),
        action=action,
        modele=instance.__class__.__name__,
        objet_id=str(instance.pk),
        objet_repr=str(instance)[:255],
        adresse_ip=get_current_ip(),
    )


def make_save_handler():
    def handler(sender, instance, created, **kwargs):
        action = JournalActivite.Action.CREATION if created else JournalActivite.Action.MODIFICATION
        enregistrer(action, instance)
    return handler


def make_delete_handler():
    def handler(sender, instance, **kwargs):
        enregistrer(JournalActivite.Action.SUPPRESSION, instance)
    return handler


for modele in MODELES_AUDITES:
    post_save.connect(make_save_handler(), sender=modele, weak=False)
    post_delete.connect(make_delete_handler(), sender=modele, weak=False)