from datetime import timedelta
from django.db.models import Avg, Count, Sum, Q, F
from django.db.models.functions import TruncMonth, TruncYear
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.reforestation.models import SiteReboisement, CampagnePlantation, SuiviCroissance, Essence
from apps.accounts.models import User


class DashboardOverviewView(APIView):
    """
    Vue d'ensemble globale — carte de synthèse en haut du dashboard.
    C'est le premier écran que verra le décideur.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        sites = SiteReboisement.objects.all()
        campagnes = CampagnePlantation.objects.all()
        suivis = SuiviCroissance.objects.all()

        taux_global = suivis.aggregate(moyenne=Avg('taux_survie'))['moyenne']

        sites_par_statut = list(
            sites.values('statut').annotate(total=Count('id')).order_by('statut')
        )

        return Response({
            'total_sites': sites.count(),
            'superficie_totale_hectares': sites.aggregate(t=Sum('superficie_hectares'))['t'] or 0,
            'total_campagnes': campagnes.count(),
            'total_plants_plantes': campagnes.aggregate(t=Sum('nombre_plants'))['t'] or 0,
            'total_suivis_effectues': suivis.count(),
            'taux_survie_global': round(taux_global, 2) if taux_global else None,
            'sites_par_statut': sites_par_statut,
            'total_essences_utilisees': campagnes.values('essence').distinct().count(),
            'total_utilisateurs_actifs': User.objects.filter(is_active=True).count(),
        })


class DashboardParSiteView(APIView):
    """
    Classement des sites par performance — top et flop.
    Très utile pour un décideur qui veut savoir où réallouer les moyens.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        sites = SiteReboisement.objects.annotate(
            taux_moyen=Avg('campagnes__suivis__taux_survie'),
            nb_campagnes=Count('campagnes', distinct=True),
            total_plants=Sum('campagnes__nombre_plants'),
        ).filter(taux_moyen__isnull=False).order_by('-taux_moyen')

        data = [
            {
                'id': s.id,
                'nom': s.nom,
                'localite': s.localite,
                'province': s.province,
                'statut': s.statut,
                'taux_survie_moyen': round(s.taux_moyen, 2),
                'nombre_campagnes': s.nb_campagnes,
                'total_plants': s.total_plants or 0,
            }
            for s in sites
        ]

        return Response({
            'top_5_meilleurs_sites': data[:5],
            'top_5_sites_a_risque': list(reversed(data[-5:])) if len(data) > 5 else list(reversed(data)),
            'classement_complet': data,
        })


class DashboardParEssenceView(APIView):
    """Performance comparée par essence — quelle espèce survit le mieux au Gabon."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        essences = Essence.objects.annotate(
            taux_moyen=Avg('campagnes__suivis__taux_survie'),
            nb_campagnes=Count('campagnes', distinct=True),
            total_plants=Sum('campagnes__nombre_plants'),
        ).order_by('-taux_moyen')

        return Response([
            {
                'essence': e.nom,
                'nom_scientifique': e.nom_scientifique,
                'croissance_rapide': e.croissance_rapide,
                'taux_survie_moyen': round(e.taux_moyen, 2) if e.taux_moyen else None,
                'nombre_campagnes': e.nb_campagnes,
                'total_plants': e.total_plants or 0,
            }
            for e in essences
        ])


class DashboardParProvinceView(APIView):
    """Vue géographique agrégée — utile pour une carte / répartition régionale."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        provinces = SiteReboisement.objects.exclude(province='').values('province').annotate(
            nb_sites=Count('id', distinct=True),
            superficie_totale=Sum('superficie_hectares'),
            taux_moyen=Avg('campagnes__suivis__taux_survie'),
            total_plants=Sum('campagnes__nombre_plants'),
        ).order_by('-nb_sites')

        return Response(list(provinces))


class DashboardEvolutionTemporelleView(APIView):
    """
    Évolution mensuelle : plantations et taux de survie dans le temps.
    C'est le graphique en courbe que les décideurs adorent voir en réunion.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        plantations_par_mois = list(
            CampagnePlantation.objects
            .annotate(mois=TruncMonth('date_plantation'))
            .values('mois')
            .annotate(nb_campagnes=Count('id'), total_plants=Sum('nombre_plants'))
            .order_by('mois')
        )

        survie_par_mois = list(
            SuiviCroissance.objects
            .annotate(mois=TruncMonth('date_controle'))
            .values('mois')
            .annotate(taux_moyen=Avg('taux_survie'), nb_controles=Count('id'))
            .order_by('mois')
        )

        return Response({
            'plantations_par_mois': plantations_par_mois,
            'survie_par_mois': survie_par_mois,
        })


class DashboardAlertesView(APIView):
    """
    Signaux d'alerte automatiques : sites/campagnes sous un seuil critique de survie,
    ou sans suivi récent. Argument de vente fort pour un jury : l'API ne fait pas
    que restituer des données, elle aide à la décision.
    """
    permission_classes = [IsAuthenticated]

    SEUIL_CRITIQUE = 50.0  # % taux de survie
    JOURS_SANS_SUIVI_ALERTE = 90

    def get(self, request):
        campagnes_critiques = CampagnePlantation.objects.annotate(
            taux_moyen=Avg('suivis__taux_survie'),
            dernier_suivi=Count('suivis')
        ).filter(taux_moyen__lt=self.SEUIL_CRITIQUE, taux_moyen__isnull=False)

        limite_date = timezone.now().date() - timedelta(days=self.JOURS_SANS_SUIVI_ALERTE)
        campagnes_sans_suivi_recent = CampagnePlantation.objects.filter(
            date_plantation__lt=limite_date
        ).exclude(
            suivis__date_controle__gte=limite_date
        ).distinct()

        return Response({
            'seuil_critique_pourcent': self.SEUIL_CRITIQUE,
            'campagnes_taux_critique': [
                {
                    'id': c.id,
                    'site': c.site.nom,
                    'essence': c.essence.nom,
                    'date_plantation': c.date_plantation,
                    'taux_survie_moyen': round(c.taux_moyen, 2),
                }
                for c in campagnes_critiques
            ],
            'campagnes_sans_suivi_recent': [
                {
                    'id': c.id,
                    'site': c.site.nom,
                    'essence': c.essence.nom,
                    'date_plantation': c.date_plantation,
                    'jours_depuis_derniere_activite': (timezone.now().date() - c.date_plantation).days,
                }
                for c in campagnes_sans_suivi_recent
            ],
        })


class DashboardResponsablesView(APIView):
    """Performance par agent responsable — utile en interne pour évaluer les équipes terrain."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        agents = User.objects.filter(
            campagnes_creees__isnull=False
        ).annotate(
            nb_campagnes=Count('campagnes_creees', distinct=True),
            total_plants=Sum('campagnes_creees__nombre_plants'),
            taux_moyen=Avg('campagnes_creees__suivis__taux_survie'),
        ).distinct().order_by('-nb_campagnes')

        return Response([
            {
                'agent': a.get_full_name(),
                'email': a.email,
                'nombre_campagnes': a.nb_campagnes,
                'total_plants': a.total_plants or 0,
                'taux_survie_moyen': round(a.taux_moyen, 2) if a.taux_moyen else None,
            }
            for a in agents
        ])