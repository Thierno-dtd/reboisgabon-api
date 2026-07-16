from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Avg, Count

from .models import Essence, SiteReboisement, CampagnePlantation, SuiviCroissance
from .serializers import (
    EssenceSerializer,
    SiteReboisementListSerializer, SiteReboisementWriteSerializer,
    CampagnePlantationListSerializer, CampagnePlantationWriteSerializer,
    SuiviCroissanceSerializer,
)
from .filters import SiteReboisementFilter, CampagnePlantationFilter, SuiviCroissanceFilter


class EssenceViewSet(viewsets.ModelViewSet):
    queryset = Essence.objects.all()
    serializer_class = EssenceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['nom', 'nom_scientifique']
    ordering_fields = ['nom']


class SiteReboisementViewSet(viewsets.ModelViewSet):
    """CRUD complet des sites + recherche + filtres combinables."""

    queryset = SiteReboisement.objects.select_related('responsable').all()
    permission_classes = [IsAuthenticated]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = SiteReboisementFilter
    search_fields = ['nom', 'localite', 'province']
    ordering_fields = ['nom', 'superficie_hectares', 'created_at']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return SiteReboisementWriteSerializer
        return SiteReboisementListSerializer

    def destroy(self, request, *args, **kwargs):
        """Suppression avec confirmation obligatoire (?confirm=true)."""
        if request.query_params.get('confirm') != 'true':
            return Response(
                {'detail': "Confirmation requise. Ajoutez ?confirm=true à la requête."},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['get'], url_path='statistiques')
    def statistiques(self, request, pk=None):
        """Détail des stats du site — utile pour le dashboard côté JavaFX."""
        site = self.get_object()
        campagnes = site.campagnes.all()
        stats = SuiviCroissance.objects.filter(campagne__site=site).aggregate(
            taux_moyen=Avg('taux_survie')
        )
        return Response({
            'site': site.nom,
            'nombre_campagnes': campagnes.count(),
            'total_plants': sum(c.nombre_plants for c in campagnes),
            'taux_survie_moyen': round(stats['taux_moyen'], 2) if stats['taux_moyen'] else None,
        })


class CampagnePlantationViewSet(viewsets.ModelViewSet):
    queryset = CampagnePlantation.objects.select_related('site', 'essence', 'responsable').all()
    permission_classes = [IsAuthenticated]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = CampagnePlantationFilter
    search_fields = ['site__nom', 'essence__nom']
    ordering_fields = ['date_plantation', 'nombre_plants']
    ordering = ['-date_plantation']

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return CampagnePlantationWriteSerializer
        return CampagnePlantationListSerializer

    def destroy(self, request, *args, **kwargs):
        if request.query_params.get('confirm') != 'true':
            return Response(
                {'detail': "Confirmation requise. Ajoutez ?confirm=true à la requête."},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().destroy(request, *args, **kwargs)


class SuiviCroissanceViewSet(viewsets.ModelViewSet):
    queryset = SuiviCroissance.objects.select_related(
        'campagne', 'campagne__site', 'campagne__essence'
    ).all()
    serializer_class = SuiviCroissanceSerializer
    permission_classes = [IsAuthenticated]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = SuiviCroissanceFilter
    search_fields = ['campagne__site__nom', 'observations']
    ordering_fields = ['date_controle', 'taux_survie']
    ordering = ['-date_controle']

    def destroy(self, request, *args, **kwargs):
        if request.query_params.get('confirm') != 'true':
            return Response(
                {'detail': "Confirmation requise. Ajoutez ?confirm=true à la requête."},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().destroy(request, *args, **kwargs)