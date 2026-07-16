import uuid
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError


class Essence(models.Model):
    """Espèce d'arbre plantée (Okoumé, Moabi, Padouk, etc.)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField(max_length=100, unique=True)
    nom_scientifique = models.CharField(max_length=150, blank=True)
    croissance_rapide = models.BooleanField(default=False)

    class Meta:
        db_table = 'essences'
        verbose_name = 'Essence'
        verbose_name_plural = 'Essences'
        ordering = ['nom']

    def __str__(self):
        return self.nom


class SiteReboisement(models.Model):
    """Site géographique où se déroulent les campagnes de plantation."""

    class Statut(models.TextChoices):
        PLANIFIE = 'PLANIFIE', 'Planifié'
        EN_COURS = 'EN_COURS', 'En cours'
        TERMINE = 'TERMINE', 'Terminé'
        SUSPENDU = 'SUSPENDU', 'Suspendu'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField(max_length=150)
    localite = models.CharField(max_length=150)
    province = models.CharField(max_length=100, blank=True)
    superficie_hectares = models.DecimalField(
        max_digits=8, decimal_places=2,
        validators=[MinValueValidator(0.01)]
    )
    statut = models.CharField(max_length=10, choices=Statut.choices, default=Statut.PLANIFIE)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='sites_geres'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sites_reboisement'
        verbose_name = 'Site de reboisement'
        verbose_name_plural = 'Sites de reboisement'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['localite']),
            models.Index(fields=['statut']),
        ]

    def __str__(self):
        return f"{self.nom} ({self.localite})"

    @property
    def taux_survie_moyen(self):
        """Défi technique : moyenne des taux de survie des suivis liés à ce site (via ses campagnes)."""
        from django.db.models import Avg
        result = SuiviCroissance.objects.filter(
            campagne__site=self
        ).aggregate(moyenne=Avg('taux_survie'))
        return round(result['moyenne'], 2) if result['moyenne'] is not None else None


class CampagnePlantation(models.Model):
    """Une opération de plantation sur un site donné, à une date donnée."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    site = models.ForeignKey(
        SiteReboisement, on_delete=models.CASCADE, related_name='campagnes'
    )
    essence = models.ForeignKey(
        Essence, on_delete=models.PROTECT, related_name='campagnes'
    )
    date_plantation = models.DateField()
    nombre_plants = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='campagnes_creees'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'campagnes_plantation'
        verbose_name = 'Campagne de plantation'
        verbose_name_plural = 'Campagnes de plantation'
        ordering = ['-date_plantation']
        indexes = [
            models.Index(fields=['date_plantation']),
        ]

    def __str__(self):
        return f"{self.site.nom} — {self.essence.nom} ({self.date_plantation})"

    @property
    def taux_survie_moyen(self):
        from django.db.models import Avg
        result = self.suivis.aggregate(moyenne=Avg('taux_survie'))
        return round(result['moyenne'], 2) if result['moyenne'] is not None else None


class SuiviCroissance(models.Model):
    """Contrôle périodique du taux de survie d'une campagne de plantation."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campagne = models.ForeignKey(
        CampagnePlantation, on_delete=models.CASCADE, related_name='suivis'
    )
    date_controle = models.DateField()
    taux_survie = models.DecimalField(
        max_digits=5, decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Pourcentage de plants ayant survécu (0 à 100)."
    )
    nombre_plants_vivants = models.PositiveIntegerField(null=True, blank=True)
    observations = models.TextField(blank=True)

    controle_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='suivis_effectues'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'suivis_croissance'
        verbose_name = 'Suivi de croissance'
        verbose_name_plural = 'Suivis de croissance'
        ordering = ['-date_controle']
        indexes = [
            models.Index(fields=['date_controle']),
            models.Index(fields=['taux_survie']),
        ]

    def __str__(self):
        return f"Suivi {self.campagne} — {self.date_controle} ({self.taux_survie}%)"

    def clean(self):
        if self.date_controle and self.campagne_id and self.date_controle < self.campagne.date_plantation:
            raise ValidationError("La date de contrôle ne peut pas précéder la date de plantation.")