import uuid
from django.db import models
from django.conf import settings


class Notification(models.Model):
    """Notification interne à un utilisateur — visible côté client JavaFX (cloche de notifications)."""

    class Type(models.TextChoices):
        TAUX_CRITIQUE = 'TAUX_CRITIQUE', 'Taux de survie critique'
        SUIVI_EN_RETARD = 'SUIVI_EN_RETARD', 'Suivi en retard'
        SUIVI_A_VENIR = 'SUIVI_A_VENIR', 'Suivi programmé bientôt'
        NOUVEAU_FINANCEMENT = 'NOUVEAU_FINANCEMENT', 'Nouveau financement reçu'
        COMPTE_CREE = 'COMPTE_CREE', 'Compte créé'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    destinataire = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications'
    )
    type_notification = models.CharField(max_length=25, choices=Type.choices)
    titre = models.CharField(max_length=200)
    message = models.TextField()
    lue = models.BooleanField(default=False)
    lien_objet_id = models.CharField(max_length=100, blank=True)
    lien_modele = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['destinataire', 'lue']),
        ]

    def __str__(self):
        return f"{self.titre} → {self.destinataire.email}"