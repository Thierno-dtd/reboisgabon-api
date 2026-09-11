from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets, filters
from apps.accounts.permissions import IsAdminRole
from rest_framework.permissions import IsAuthenticated
from .models import JournalActivite
from .serializers import JournalActiviteSerializer
from .filters import JournalActiviteFilter
import csv
from django.http import HttpResponse
from django.db.models import Count
from rest_framework.decorators import action


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


    @extend_schema(summary="Exporte le journal filtré au format CSV", tags=['Audit'])
    @action(detail=False, methods=['get'], url_path='export-csv')
    def export_csv(self, request):
        queryset = self.filter_queryset(self.get_queryset())

        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="journal_activite.csv"'
        writer = csv.writer(response)
        writer.writerow(['Date', 'Utilisateur', 'Action', 'Modèle', 'Objet', 'Adresse IP'])

        for entree in queryset:
            writer.writerow([
                entree.date_action.strftime('%Y-%m-%d %H:%M:%S'),
                entree.utilisateur.email if entree.utilisateur else 'Système',
                entree.get_action_display(), entree.modele, entree.objet_repr,
                entree.adresse_ip or '',
            ])
        return response

    @extend_schema(summary="Statistiques agrégées du journal (par action, par modèle)", tags=['Audit'])
    @action(detail=False, methods=['get'], url_path='statistiques')
    def statistiques(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        return Response({
            'total_entrees': queryset.count(),
            'par_action': list(queryset.values('action').annotate(total=Count('id')).order_by('-total')),
            'par_modele': list(queryset.values('modele').annotate(total=Count('id')).order_by('-total')),
        })