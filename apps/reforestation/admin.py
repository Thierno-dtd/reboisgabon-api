from django.contrib import admin
from .models import Essence, SiteReboisement, CampagnePlantation, SuiviCroissance


@admin.register(Essence)
class EssenceAdmin(admin.ModelAdmin):
    list_display = ['nom', 'nom_scientifique', 'croissance_rapide']
    search_fields = ['nom']


@admin.register(SiteReboisement)
class SiteReboisementAdmin(admin.ModelAdmin):
    list_display = ['nom', 'localite', 'province', 'superficie_hectares', 'statut', 'taux_survie_moyen']
    list_filter = ['statut', 'province']
    search_fields = ['nom', 'localite']


@admin.register(CampagnePlantation)
class CampagnePlantationAdmin(admin.ModelAdmin):
    list_display = ['site', 'essence', 'date_plantation', 'nombre_plants', 'taux_survie_moyen']
    list_filter = ['essence', 'date_plantation']
    search_fields = ['site__nom', 'essence__nom']


@admin.register(SuiviCroissance)
class SuiviCroissanceAdmin(admin.ModelAdmin):
    list_display = ['campagne', 'date_controle', 'taux_survie', 'nombre_plants_vivants']
    list_filter = ['date_controle']
    search_fields = ['campagne__site__nom']