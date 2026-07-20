import uuid
from django.db import models
from django.conf import settings


class JournalActivite(models.Model):
    """Trace toute action de création/modification/suppression sur les entités sensibles."""

    class Action(models.TextChoices):
        CREATION = 'CREATION', 'Création'
        MODIFICATION = 'MODIFICATION', 'Modification'
        SUPPRESSION = 'SUPPRESSION', 'Suppression'
        CONNEXION = 'CONNEXION', 'Connexion'
        CONNEXION_ECHOUEE = 'CONNEXION_ECHOUEE', 'Connexion échouée'
        DESACTIVATION = 'DESACTIVATION', 'Désactivation de compte'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='actions_journal'
    )
    action = models.CharField(max_length=20, choices=Action.choices)
    modele = models.CharField(max_length=100, help_text="Nom du modèle concerné (ex: SiteReboisement)")
    objet_id = models.CharField(max_length=100, blank=True)
    objet_repr = models.CharField(max_length=255, blank=True, help_text="Représentation lisible de l'objet")
    details = models.JSONField(null=True, blank=True, help_text="Changements (avant/après) le cas échéant")
    adresse_ip = models.GenericIPAddressField(null=True, blank=True)
    date_action = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'journal_activite'
        verbose_name = "Entrée du journal d'activité"
        verbose_name_plural = "Journal d'activité"
        ordering = ['-date_action']
        indexes = [
            models.Index(fields=['-date_action']),
            models.Index(fields=['modele']),
            models.Index(fields=['action']),
            models.Index(fields=['utilisateur']),
        ]

    def __str__(self):
        return f"[{self.date_action:%Y-%m-%d %H:%M}] {self.utilisateur} — {self.action} — {self.modele}"