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
from rest_framework.parsers import MultiPartParser, FormParser
from .models import PhotoSuivi
from .serializers import PhotoSuiviSerializer
from datetime import timedelta
from django.utils import timezone


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
    

class PhotoSuiviViewSet(viewsets.ModelViewSet):
    queryset = PhotoSuivi.objects.select_related('suivi', 'prise_par').all()
    serializer_class = PhotoSuiviSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['suivi']

    def get_serializer_context(self):
        return {'request': self.request}
    

class CalendrierSuivisView(APIView):
    """
    Vue calendrier : tous les suivis programmés dans les prochains jours.
    Utile pour un écran 'planning terrain' côté JavaFX.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        horizon_jours = int(request.query_params.get('horizon', 30))
        aujourdhui = timezone.now().date()
        limite = aujourdhui + timedelta(days=horizon_jours)

        suivis_programmes = SuiviCroissance.objects.filter(
            prochaine_date_controle__isnull=False,
            prochaine_date_controle__gte=aujourdhui,
            prochaine_date_controle__lte=limite,
        ).select_related('campagne', 'campagne__site', 'campagne__essence').order_by('prochaine_date_controle')

        en_retard = SuiviCroissance.objects.filter(
            prochaine_date_controle__isnull=False,
            prochaine_date_controle__lt=aujourdhui,
        ).select_related('campagne', 'campagne__site').order_by('prochaine_date_controle')

        def serialize(qs):
            return [
                {
                    'id': s.id,
                    'site': s.campagne.site.nom,
                    'essence': s.campagne.essence.nom,
                    'prochaine_date_controle': s.prochaine_date_controle,
                    'dernier_taux_survie': s.taux_survie,
                }
                for s in qs
            ]

        return Response({
            'horizon_jours': horizon_jours,
            'suivis_a_venir': serialize(suivis_programmes),
            'suivis_en_retard': serialize(en_retard),
        })