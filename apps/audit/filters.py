import django_filters
from .models import JournalActivite


class JournalActiviteFilter(django_filters.FilterSet):
    utilisateur = django_filters.UUIDFilter(field_name='utilisateur__id')
    action = django_filters.ChoiceFilter(choices=JournalActivite.Action.choices)
    modele = django_filters.CharFilter(lookup_expr='iexact')
    date_debut = django_filters.DateFilter(field_name='date_action', lookup_expr='date__gte')
    date_fin = django_filters.DateFilter(field_name='date_action', lookup_expr='date__lte')

    class Meta:
        model = JournalActivite
        fields = ['utilisateur', 'action', 'modele', 'date_debut', 'date_fin']