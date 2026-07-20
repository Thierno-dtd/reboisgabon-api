from django.contrib import admin
from .models import Partenaire, Financement, BudgetCampagne


@admin.register(Partenaire)
class PartenaireAdmin(admin.ModelAdmin):
    list_display = ['nom', 'type_partenaire', 'pays', 'actif', 'montant_total_finance']
    list_filter = ['type_partenaire', 'actif', 'pays']
    search_fields = ['nom']


@admin.register(Financement)
class FinancementAdmin(admin.ModelAdmin):
    list_display = ['partenaire', 'campagne', 'site', 'montant', 'devise', 'date_financement']
    list_filter = ['devise', 'date_financement']
    search_fields = ['reference', 'partenaire__nom']


@admin.register(BudgetCampagne)
class BudgetCampagneAdmin(admin.ModelAdmin):
    list_display = ['campagne', 'budget_alloue', 'cout_reel', 'ecart_budgetaire', 'cout_par_plant_survivant']