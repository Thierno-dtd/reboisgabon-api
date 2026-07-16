import django_filters
from django.db.models import Avg
from .models import SiteReboisement, CampagnePlantation, SuiviCroissance


class SiteReboisementFilter(django_filters.FilterSet):
    """
    Filtres sur le site :
    - par localité
    - par statut
    - par superficie (min/max)
    - par taux de survie moyen (min) -> filtre custom sur champ calculé
    """
    localite = django_filters.CharFilter(field_name='localite', lookup_expr='icontains')
    province = django_filters.CharFilter(field_name='province', lookup_expr='icontains')
    statut = django_filters.ChoiceFilter(choices=SiteReboisement.Statut.choices)
    superficie_min = django_filters.NumberFilter(field_name='superficie_hectares', lookup_expr='gte')
    superficie_max = django_filters.NumberFilter(field_name='superficie_hectares', lookup_expr='lte')
    taux_survie_min = django_filters.NumberFilter(method='filter_taux_survie_min')

    class Meta:
        model = SiteReboisement
        fields = ['localite', 'province', 'statut', 'superficie_min', 'superficie_max', 'taux_survie_min']

    def filter_taux_survie_min(self, queryset, name, value):
        """Ne garde que les sites dont le taux de survie moyen (calculé) est >= value."""
        ids_valides = []
        for site in queryset:
            taux = site.taux_survie_moyen
            if taux is not None and taux >= float(value):
                ids_valides.append(site.id)
        return queryset.filter(id__in=ids_valides)


class CampagnePlantationFilter(django_filters.FilterSet):
    """
    Filtres attendus par le cahier des charges pour ce sujet :
    - par site
    - par essence plantée
    - par période (date_debut / date_fin)
    - par taux de survie (via les suivis liés)
    """
    site = django_filters.UUIDFilter(field_name='site__id')
    site_nom = django_filters.CharFilter(field_name='site__nom', lookup_expr='icontains')
    essence = django_filters.UUIDFilter(field_name='essence__id')
    essence_nom = django_filters.CharFilter(field_name='essence__nom', lookup_expr='icontains')

    date_debut = django_filters.DateFilter(field_name='date_plantation', lookup_expr='gte')
    date_fin = django_filters.DateFilter(field_name='date_plantation', lookup_expr='lte')

    taux_survie_min = django_filters.NumberFilter(method='filter_taux_survie_min')
    taux_survie_max = django_filters.NumberFilter(method='filter_taux_survie_max')

    class Meta:
        model = CampagnePlantation
        fields = [
            'site', 'site_nom', 'essence', 'essence_nom',
            'date_debut', 'date_fin', 'taux_survie_min', 'taux_survie_max',
        ]

    def filter_taux_survie_min(self, queryset, name, value):
        return queryset.annotate(_taux=Avg('suivis__taux_survie')).filter(_taux__gte=value)

    def filter_taux_survie_max(self, queryset, name, value):
        return queryset.annotate(_taux=Avg('suivis__taux_survie')).filter(_taux__lte=value)


class SuiviCroissanceFilter(django_filters.FilterSet):
    """Filtres sur les suivis de croissance eux-mêmes."""
    campagne = django_filters.UUIDFilter(field_name='campagne__id')
    site = django_filters.UUIDFilter(field_name='campagne__site__id')
    essence = django_filters.UUIDFilter(field_name='campagne__essence__id')

    date_debut = django_filters.DateFilter(field_name='date_controle', lookup_expr='gte')
    date_fin = django_filters.DateFilter(field_name='date_controle', lookup_expr='lte')

    taux_survie_min = django_filters.NumberFilter(field_name='taux_survie', lookup_expr='gte')
    taux_survie_max = django_filters.NumberFilter(field_name='taux_survie', lookup_expr='lte')

    class Meta:
        model = SuiviCroissance
        fields = [
            'campagne', 'site', 'essence',
            'date_debut', 'date_fin', 'taux_survie_min', 'taux_survie_max',
        ]