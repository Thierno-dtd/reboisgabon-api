from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Avg, Count
from .scoring import calculer_score_ecologique

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
from django.db.models import F
from math import radians, cos, sin, asin, sqrt
from .filters import ObjectifReboisementFilter
from .serializers import ObjectifReboisementSerializer
from .models import ObjectifReboisement


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


class SitesGeoJSONView(APIView):
    """
    Renvoie tous les sites géolocalisés au format GeoJSON standard —
    directement exploitable par une carte (Leaflet, Google Maps, etc.)
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Sites au format GeoJSON pour affichage cartographique", tags=['Sites'])
    def get(self, request):
        sites = SiteReboisement.objects.filter(
            latitude__isnull=False, longitude__isnull=False
        ).select_related('responsable')

        features = []
        for site in sites:
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(site.longitude), float(site.latitude)]
                },
                "properties": {
                    "id": str(site.id),
                    "nom": site.nom,
                    "localite": site.localite,
                    "province": site.province,
                    "statut": site.statut,
                    "superficie_hectares": float(site.superficie_hectares),
                    "taux_survie_moyen": site.taux_survie_moyen,
                    "responsable": site.responsable.get_full_name() if site.responsable else None,
                }
            })

        return Response({"type": "FeatureCollection", "features": features})


def haversine(lat1, lon1, lat2, lon2):
    """Distance en km entre deux points GPS (formule de Haversine)."""
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * 6371 * asin(sqrt(a))


class SitesProximiteView(APIView):
    """
    Trouve les sites dans un rayon donné autour d'un point GPS — utile pour
    un agent terrain qui veut voir "les sites proches de ma position actuelle".
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Sites à proximité d'un point GPS (rayon en km)",
        tags=['Sites'],
        parameters=[
            OpenApiParameter('lat', float, required=True, description="Latitude du point de référence"),
            OpenApiParameter('lon', float, required=True, description="Longitude du point de référence"),
            OpenApiParameter('rayon_km', float, required=False, description="Rayon de recherche (défaut: 50 km)"),
        ]
    )
    def get(self, request):
        try:
            lat = float(request.query_params['lat'])
            lon = float(request.query_params['lon'])
        except (KeyError, ValueError):
            return Response(
                {'detail': "Paramètres 'lat' et 'lon' requis (nombres décimaux)."},
                status=status.HTTP_400_BAD_REQUEST
            )
        rayon_km = float(request.query_params.get('rayon_km', 50))

        sites = SiteReboisement.objects.filter(latitude__isnull=False, longitude__isnull=False)
        resultats = []
        for site in sites:
            distance = haversine(lat, lon, float(site.latitude), float(site.longitude))
            if distance <= rayon_km:
                resultats.append({
                    'id': site.id, 'nom': site.nom, 'localite': site.localite,
                    'distance_km': round(distance, 2),
                    'statut': site.statut,
                })

        resultats.sort(key=lambda x: x['distance_km'])
        return Response({'rayon_km': rayon_km, 'nombre_sites_trouves': len(resultats), 'sites': resultats})


class DashboardCarteProvinceView(APIView):
    """Agrégation géographique enrichie — centroïde par province + statistiques, pour affichage carte-choroplèthe."""
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Statistiques géographiques agrégées par province (pour carte)", tags=['Dashboard'])
    def get(self, request):
        from django.db.models import Avg, Count, Sum

        provinces = SiteReboisement.objects.exclude(province='').values('province').annotate(
            nb_sites=Count('id'),
            latitude_moyenne=Avg('latitude'),
            longitude_moyenne=Avg('longitude'),
            superficie_totale=Sum('superficie_hectares'),
            taux_survie_moyen=Avg('campagnes__suivis__taux_survie'),
        ).order_by('-nb_sites')

        return Response(list(provinces))


@extend_schema_view(
    list=extend_schema(summary="Lister les objectifs de reboisement", tags=['Objectifs']),
    create=extend_schema(summary="Créer un objectif", tags=['Objectifs']),
    retrieve=extend_schema(summary="Détail d'un objectif avec progression calculée", tags=['Objectifs']),
    update=extend_schema(summary="Modifier un objectif", tags=['Objectifs']),
    partial_update=extend_schema(summary="Modifier partiellement un objectif", tags=['Objectifs']),
    destroy=extend_schema(summary="Supprimer un objectif (nécessite ?confirm=true)", tags=['Objectifs']),
)
class ObjectifReboisementViewSet(viewsets.ModelViewSet):
    queryset = ObjectifReboisement.objects.select_related('site', 'responsable').all()
    serializer_class = ObjectifReboisementSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ObjectifReboisementFilter
    search_fields = ['titre', 'description', 'province']
    ordering_fields = ['date_echeance', 'nombre_plants_cible']
    ordering = ['date_echeance']

    def destroy(self, request, *args, **kwargs):
        if request.query_params.get('confirm') != 'true':
            return Response(
                {'detail': "Confirmation requise. Ajoutez ?confirm=true à la requête."},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().destroy(request, *args, **kwargs)



@extend_schema(summary="Score écologique détaillé d'un site (explicable)", tags=['Sites'])
class ScoreEcologiqueSiteView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            site = SiteReboisement.objects.get(pk=pk)
        except SiteReboisement.DoesNotExist:
            return Response({'detail': 'Site introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        resultat = calculer_score_ecologique(site)
        resultat['site'] = {'id': site.id, 'nom': site.nom, 'localite': site.localite}
        return Response(resultat)


@extend_schema(summary="Classement de tous les sites par score écologique", tags=['Dashboard'])
class ClassementScoreEcologiqueView(APIView):
    """
    Classement global — permet à un décideur d'identifier immédiatement
    les sites exemplaires (à valoriser auprès des bailleurs) et les sites
    qui nécessitent une intervention.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.core.cache import cache

        cache_key = 'dashboard:scores_ecologiques'
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        sites = SiteReboisement.objects.all()
        classement = []
        for site in sites:
            resultat = calculer_score_ecologique(site)
            classement.append({
                'id': site.id, 'nom': site.nom, 'localite': site.localite,
                'score_global': resultat['score_global'], 'classe': resultat['classe'],
            })

        classement.sort(key=lambda x: x['score_global'], reverse=True)
        data = {
            'classement': classement,
            'score_moyen_national': round(
                sum(c['score_global'] for c in classement) / len(classement), 1
            ) if classement else None,
        }
        cache.set(cache_key, data, 180)
        return Response(data)