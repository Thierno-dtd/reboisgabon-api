import uuid
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone


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
    prochaine_date_controle = models.DateField(
        null=True, blank=True,
        help_text="Date prévue pour le prochain contrôle de terrain."
    )
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
        

def chemin_photo_suivi(instance, filename):
    """Organise les photos par campagne pour éviter un dossier media/ fourre-tout."""
    return f"suivis/{instance.suivi.campagne.site.id}/{instance.suivi.id}/{filename}"


class PhotoSuivi(models.Model):
    """Photo terrain associée à un contrôle de croissance — preuve visuelle."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    suivi = models.ForeignKey(
        SuiviCroissance, on_delete=models.CASCADE, related_name='photos'
    )
    image = models.ImageField(upload_to=chemin_photo_suivi)
    legende = models.CharField(max_length=255, blank=True)
    prise_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='photos_prises'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'photos_suivi'
        verbose_name = 'Photo de suivi'
        verbose_name_plural = 'Photos de suivi'
        ordering = ['-created_at']

    def __str__(self):
        return f"Photo — {self.suivi} ({self.created_at:%Y-%m-%d})"


class ObjectifReboisement(models.Model):
    """
    Cible de reboisement fixée (par province, par site, ou globale) sur une période donnée.
    La progression est calculée automatiquement à partir des campagnes réelles.
    """

    class Portee(models.TextChoices):
        GLOBAL = 'GLOBAL', 'National'
        PROVINCE = 'PROVINCE', 'Province'
        SITE = 'SITE', 'Site spécifique'

    class Statut(models.TextChoices):
        EN_COURS = 'EN_COURS', 'En cours'
        ATTEINT = 'ATTEINT', 'Atteint'
        NON_ATTEINT = 'NON_ATTEINT', 'Non atteint (échéance dépassée)'
        ANNULE = 'ANNULE', 'Annulé'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    titre = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    portee = models.CharField(max_length=10, choices=Portee.choices, default=Portee.GLOBAL)
    province = models.CharField(max_length=100, blank=True)
    site = models.ForeignKey(
        SiteReboisement, on_delete=models.CASCADE, null=True, blank=True, related_name='objectifs'
    )

    nombre_plants_cible = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    taux_survie_minimum_vise = models.DecimalField(
        max_digits=5, decimal_places=2, default=70,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    date_debut = models.DateField()
    date_echeance = models.DateField()
    statut = models.CharField(max_length=15, choices=Statut.choices, default=Statut.EN_COURS)

    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='objectifs_geres'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'objectifs_reboisement'
        verbose_name = 'Objectif de reboisement'
        verbose_name_plural = 'Objectifs de reboisement'
        ordering = ['date_echeance']
        indexes = [models.Index(fields=['statut']), models.Index(fields=['date_echeance'])]

    def __str__(self):
        return f"{self.titre} ({self.nombre_plants_cible} plants)"

    def clean(self):
        if self.portee == self.Portee.SITE and not self.site:
            raise ValidationError("Un objectif de portée 'Site' doit référencer un site.")
        if self.portee == self.Portee.PROVINCE and not self.province:
            raise ValidationError("Un objectif de portée 'Province' doit préciser une province.")
        if self.date_echeance <= self.date_debut:
            raise ValidationError("La date d'échéance doit être postérieure à la date de début.")

    def _campagnes_concernees(self):
        qs = CampagnePlantation.objects.filter(
            date_plantation__gte=self.date_debut, date_plantation__lte=self.date_echeance
        )
        if self.portee == self.Portee.SITE:
            qs = qs.filter(site=self.site)
        elif self.portee == self.Portee.PROVINCE:
            qs = qs.filter(site__province=self.province)
        return qs

    @property
    def plants_realises(self):
        from django.db.models import Sum
        return self._campagnes_concernees().aggregate(t=Sum('nombre_plants'))['t'] or 0

    @property
    def taux_survie_realise(self):
        from django.db.models import Avg
        result = SuiviCroissance.objects.filter(
            campagne__in=self._campagnes_concernees()
        ).aggregate(m=Avg('taux_survie'))
        return round(result['m'], 2) if result['m'] is not None else None

    @property
    def progression_pourcentage(self):
        if self.nombre_plants_cible == 0:
            return 0
        return round(min(self.plants_realises / self.nombre_plants_cible * 100, 100), 1)

    @property
    def statut_calcule(self):
        """Recalcule dynamiquement le statut réel (sans écraser un statut ANNULE manuel)."""
        if self.statut == self.Statut.ANNULE:
            return self.statut
        if self.progression_pourcentage >= 100:
            return self.Statut.ATTEINT
        if timezone.now().date() > self.date_echeance:
            return self.Statut.NON_ATTEINT
        return self.Statut.EN_COURS