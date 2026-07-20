from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, filters
from apps.accounts.permissions import IsAdminRole
from rest_framework.permissions import IsAuthenticated
from .models import JournalActivite
from .serializers import JournalActiviteSerializer
from .filters import JournalActiviteFilter


class JournalActiviteViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Lecture seule (personne ne modifie un journal d'audit), réservé aux administrateurs.
    """
    queryset = JournalActivite.objects.select_related('utilisateur').all()
    serializer_class = JournalActiviteSerializer
    permission_classes = [IsAuthenticated, IsAdminRole]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = JournalActiviteFilter
    search_fields = ['objet_repr', 'modele']
    ordering_fields = ['date_action']
    ordering = ['-date_action']