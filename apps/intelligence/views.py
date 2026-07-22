from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter

from .serializers import PredictionSurvieSerializer
from .ml_service import predire_taux_survie, recommander_essences, entrainer_modele


@extend_schema(
    summary="Prédit le taux de survie attendu pour une campagne hypothétique",
    tags=['Intelligence écologique'],
    request=PredictionSurvieSerializer,
)
class PredictionSurvieView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PredictionSurvieSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            taux_predit = predire_taux_survie(
                essence_nom=data['essence'], province=data['province'],
                superficie_site=data['superficie_site'], nombre_plants=data['nombre_plants'],
                mois_plantation=data['mois_plantation'], croissance_rapide=data['croissance_rapide'],
            )
        except FileNotFoundError as e:
            return Response({'detail': str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        seuil_alerte = 50
        return Response({
            'taux_survie_predit': taux_predit,
            'niveau_confiance': "Estimation statistique basée sur l'historique — à valider par un suivi terrain réel.",
            'campagne_a_risque': taux_predit < seuil_alerte,
        })


@extend_schema(
    summary="Recommande les essences les plus performantes pour une province",
    tags=['Intelligence écologique'],
    parameters=[
        OpenApiParameter('province', str, required=True),
        OpenApiParameter('superficie_site', float, required=False),
        OpenApiParameter('top_n', int, required=False),
    ]
)
class RecommandationEssenceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        province = request.query_params.get('province')
        if not province:
            return Response({'detail': "Paramètre 'province' requis."}, status=status.HTTP_400_BAD_REQUEST)

        top_n = int(request.query_params.get('top_n', 3))
        recommandations = recommander_essences(province=province, superficie_site=0, top_n=top_n)

        if not recommandations:
            return Response({
                'province': province,
                'recommandations': [],
                'message': "Données historiques insuffisantes pour cette province (minimum 2 campagnes par essence)."
            })

        return Response({'province': province, 'recommandations': recommandations})


@extend_schema(summary="Réentraîne le modèle de prédiction (admin)", tags=['Intelligence écologique'])
class ReentrainerModeleView(APIView):
    """Permet de déclencher un réentraînement depuis l'admin sans passer par le terminal."""
    from apps.accounts.permissions import IsAdminRole
    permission_classes = [IsAuthenticated, IsAdminRole]

    def post(self, request):
        try:
            metriques = entrainer_modele()
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'detail': 'Modèle réentraîné avec succès.', 'metriques': metriques})


@extend_schema(summary="Détecte les campagnes récentes sans suivi encore à risque prédictif", tags=['Intelligence écologique'])
class DetectionRisquePredictifView(APIView):
    """
    Contrairement à /api/dashboard/alertes/ (qui détecte un risque déjà CONSTATÉ
    via des suivis réels), cette vue prédit un risque AVANT même le premier
    contrôle terrain — utile pour prioriser les visites de suivi.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.reforestation.models import CampagnePlantation

        campagnes_sans_suivi = CampagnePlantation.objects.filter(
            suivis__isnull=True
        ).select_related('site', 'essence')

        resultats = []
        for c in campagnes_sans_suivi:
            try:
                taux_predit = predire_taux_survie(
                    essence_nom=c.essence.nom, province=c.site.province or 'Inconnue',
                    superficie_site=float(c.site.superficie_hectares), nombre_plants=c.nombre_plants,
                    mois_plantation=c.date_plantation.month, croissance_rapide=c.essence.croissance_rapide,
                )
            except FileNotFoundError:
                return Response(
                    {'detail': "Modèle non entraîné. Exécutez python manage.py entrainer_ia."},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )

            if taux_predit < 55:
                resultats.append({
                    'campagne_id': c.id, 'site': c.site.nom, 'essence': c.essence.nom,
                    'date_plantation': c.date_plantation, 'taux_survie_predit': taux_predit,
                })

        return Response({
            'nombre_campagnes_a_risque_predit': len(resultats),
            'campagnes': sorted(resultats, key=lambda x: x['taux_survie_predit']),
        })