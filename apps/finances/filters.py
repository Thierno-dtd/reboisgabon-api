import django_filters
from .models import Partenaire, Financement


class PartenaireFilter(django_filters.FilterSet):
    nom = django_filters.CharFilter(lookup_expr='icontains')
    type_partenaire = django_filters.ChoiceFilter(choices=Partenaire.TypePartenaire.choices)
    pays = django_filters.CharFilter(lookup_expr='icontains')
    actif = django_filters.BooleanFilter()

    class Meta:
        model = Partenaire
        fields = ['nom', 'type_partenaire', 'pays', 'actif']


class FinancementFilter(django_filters.FilterSet):
    partenaire = django_filters.UUIDFilter(field_name='partenaire__id')
    campagne = django_filters.UUIDFilter(field_name='campagne__id')
    site = django_filters.UUIDFilter(field_name='site__id')
    devise = django_filters.ChoiceFilter(choices=Financement.Devise.choices)
    date_debut = django_filters.DateFilter(field_name='date_financement', lookup_expr='gte')
    date_fin = django_filters.DateFilter(field_name='date_financement', lookup_expr='lte')
    montant_min = django_filters.NumberFilter(field_name='montant', lookup_expr='gte')
    montant_max = django_filters.NumberFilter(field_name='montant', lookup_expr='lte')

    class Meta:
        model = Financement
        fields = [
            'partenaire', 'campagne', 'site', 'devise',
            'date_debut', 'date_fin', 'montant_min', 'montant_max',
        ]