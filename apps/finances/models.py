import uuid
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from apps.reforestation.models import CampagnePlantation, SiteReboisement


class Partenaire(models.Model):
    """Bailleur, ONG, ministère ou entreprise finançant des campagnes."""

    class TypePartenaire(models.TextChoices):
        ONG = 'ONG', 'ONG'
        ETAT = 'ETAT', 'État / Ministère'
        ENTREPRISE = 'ENTREPRISE', 'Entreprise privée'
        BAILLEUR_INTL = 'BAILLEUR_INTL', 'Bailleur international'
        AUTRE = 'AUTRE', 'Autre'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField(max_length=200, unique=True)
    type_partenaire = models.CharField(max_length=20, choices=TypePartenaire.choices)
    pays = models.CharField(max_length=100, blank=True)
    contact_nom = models.CharField(max_length=150, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_telephone = models.CharField(max_length=30, blank=True)
    actif = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'partenaires'
        verbose_name = 'Partenaire'
        verbose_name_plural = 'Partenaires'
        ordering = ['nom']
        indexes = [models.Index(fields=['type_partenaire'])]

    def __str__(self):
        return self.nom

    @property
    def montant_total_finance(self):
        from django.db.models import Sum
        return self.financements.aggregate(t=Sum('montant'))['t'] or 0


class Financement(models.Model):
    """Un apport financier d'un partenaire sur une campagne donnée."""

    class Devise(models.TextChoices):
        XAF = 'XAF', 'Franc CFA (XAF)'
        EUR = 'EUR', 'Euro'
        USD = 'USD', 'Dollar US'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    partenaire = models.ForeignKey(Partenaire, on_delete=models.PROTECT, related_name='financements')
    campagne = models.ForeignKey(
        CampagnePlantation, on_delete=models.CASCADE, related_name='financements',
        null=True, blank=True
    )
    site = models.ForeignKey(
        SiteReboisement, on_delete=models.CASCADE, related_name='financements',
        null=True, blank=True, help_text="Financement global d'un site (hors campagne précise)."
    )
    montant = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(0.01)])
    devise = models.CharField(max_length=3, choices=Devise.choices, default=Devise.XAF)
    date_financement = models.DateField()
    reference = models.CharField(max_length=100, blank=True, help_text="Numéro de convention, référence bancaire...")
    description = models.TextField(blank=True)

    enregistre_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='financements_enregistres'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'financements'
        verbose_name = 'Financement'
        verbose_name_plural = 'Financements'
        ordering = ['-date_financement']
        indexes = [
            models.Index(fields=['date_financement']),
        ]

    def __str__(self):
        if self.campagne_id:
            cible = f"Campagne #{self.campagne_id}"
        elif self.site_id:
            cible = f"Site #{self.site_id}"
        else:
            cible = "—"

        return f"{self.partenaire.nom} → {cible} ({self.montant} {self.devise})"

    def clean(self):
        from django.core.exceptions import ValidationError
        if not self.campagne and not self.site:
            raise ValidationError("Un financement doit cibler soit une campagne, soit un site.")
        if self.campagne and self.site:
            raise ValidationError("Un financement ne peut pas cibler à la fois une campagne et un site.")


class BudgetCampagne(models.Model):
    """Budget prévisionnel et coût réel d'une campagne — pour calculer le coût par plant survivant."""

    campagne = models.OneToOneField(
        CampagnePlantation, on_delete=models.CASCADE, related_name='budget'
    )
    budget_alloue = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    cout_reel = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    devise = models.CharField(max_length=3, choices=Financement.Devise.choices, default=Financement.Devise.XAF)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'budgets_campagne'
        verbose_name = 'Budget de campagne'
        verbose_name_plural = 'Budgets de campagne'

    def __str__(self):
        return f"Budget {self.campagne} — {self.cout_reel}/{self.budget_alloue} {self.devise}"

    @property
    def ecart_budgetaire(self):
        return self.budget_alloue - self.cout_reel

    @property
    def cout_par_plant_survivant(self):
        """Métrique clé pour un décideur : combien coûte un arbre qui a réellement survécu."""
        taux = self.campagne.taux_survie_moyen
        if not taux or taux == 0 or self.cout_reel == 0:
            return None
        plants_survivants = self.campagne.nombre_plants * (float(taux) / 100)
        if plants_survivants == 0:
            return None
        return round(float(self.cout_reel) / plants_survivants, 2)