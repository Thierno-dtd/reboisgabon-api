from datetime import timedelta
from multiprocessing.dummy import connection
from django.db.models import Avg, Count, Sum, Q, F
from django.db.models.functions import TruncMonth, TruncYear
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.core.cache import cache
from django.conf import settings
from django.db import connection
from rest_framework.permissions import AllowAny

from apps.reforestation.models import SiteReboisement, CampagnePlantation, SuiviCroissance, Essence
from apps.accounts.models import User
from apps.finances.models import Partenaire, Financement, BudgetCampagne
from apps.reforestation.models import ObjectifReboisement


class DashboardOverviewView(APIView):
    """
    Vue d'ensemble globale — carte de synthèse en haut du dashboard.
    C'est le premier écran que verra le décideur.
    """
    permission_classes = [IsAuthenticated]
    CACHE_KEY = 'dashboard:overview'
    CACHE_TTL = 180

    def get(self, request):
        cached = cache.get(self.CACHE_KEY)
        if cached is not None:
            return Response(cached)
        
        sites = SiteReboisement.objects.all()
        campagnes = CampagnePlantation.objects.all()
        suivis = SuiviCroissance.objects.all()

        taux_global = suivis.aggregate(moyenne=Avg('taux_survie'))['moyenne']

        sites_par_statut = list(
            sites.values('statut').annotate(total=Count('id')).order_by('statut')
        )

        data = {
            'total_sites': sites.count(),
            'superficie_totale_hectares': sites.aggregate(t=Sum('superficie_hectares'))['t'] or 0,
            'total_campagnes': campagnes.count(),
            'total_plants_plantes': campagnes.aggregate(t=Sum('nombre_plants'))['t'] or 0,
            'total_suivis_effectues': suivis.count(),
            'taux_survie_global': round(taux_global, 2) if taux_global else None,
            'sites_par_statut': list(sites.values('statut').annotate(total=Count('id')).order_by('statut')),
            'total_essences_utilisees': campagnes.values('essence').distinct().count(),
            'total_utilisateurs_actifs': User.objects.filter(is_active=True).count(),
        }
        cache.set(self.CACHE_KEY, data, self.CACHE_TTL)
        return Response(data)


class DashboardParSiteView(APIView):
    """
    Classement des sites par performance — top et flop.
    Très utile pour un décideur qui veut savoir où réallouer les moyens.
    """
    permission_classes = [IsAuthenticated]
    CACHE_KEY = 'dashboard:sites'
    CACHE_TTL = 180

    def get(self, request):
        cached = cache.get(self.CACHE_KEY)
        if cached is not None:
            return Response(cached)
        
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
        cache.set(self.CACHE_KEY, data, self.CACHE_TTL)
        return Response({
            'top_5_meilleurs_sites': data[:5],
            'top_5_sites_a_risque': list(reversed(data[-5:])) if len(data) > 5 else list(reversed(data)),
            'classement_complet': data,
        })


class DashboardParEssenceView(APIView):
    """Performance comparée par essence — quelle espèce survit le mieux au Gabon."""
    permission_classes = [IsAuthenticated]
    CACHE_KEY = 'dashboard:essences'
    CACHE_TTL = 180

    def get(self, request):
        cached = cache.get(self.CACHE_KEY)
        if cached is not None:
            return Response(cached)
    
        essences = Essence.objects.annotate(
            taux_moyen=Avg('campagnes__suivis__taux_survie'),
            nb_campagnes=Count('campagnes', distinct=True),
            total_plants=Sum('campagnes__nombre_plants'),
        ).order_by('-taux_moyen')

        data = [
            {
                'essence': e.nom,
                'nom_scientifique': e.nom_scientifique,
                'croissance_rapide': e.croissance_rapide,
                'taux_survie_moyen': round(e.taux_moyen, 2) if e.taux_moyen else None,
                'nombre_campagnes': e.nb_campagnes,
                'total_plants': e.total_plants or 0,
            }
            for e in essences
        ]
        cache.set(self.CACHE_KEY, data, self.CACHE_TTL)

        return Response(data)


class DashboardParProvinceView(APIView):
    """Vue géographique agrégée — utile pour une carte / répartition régionale."""
    permission_classes = [IsAuthenticated]
    CACHE_KEY = 'dashboard:provinces'
    CACHE_TTL = 180

    def get(self, request):
        cached = cache.get(self.CACHE_KEY)
        if cached is not None:
            return Response(cached)

        provinces = SiteReboisement.objects.exclude(province='').values('province').annotate(
            nb_sites=Count('id', distinct=True),
            superficie_totale=Sum('superficie_hectares'),
            taux_moyen=Avg('campagnes__suivis__taux_survie'),
            total_plants=Sum('campagnes__nombre_plants'),
        ).order_by('-nb_sites')

        data = list(provinces)
        cache.set(self.CACHE_KEY, data, self.CACHE_TTL)

        return Response(data)


class DashboardEvolutionTemporelleView(APIView):
    """
    Évolution mensuelle : plantations et taux de survie dans le temps.
    C'est le graphique en courbe que les décideurs adorent voir en réunion.
    """
    permission_classes = [IsAuthenticated]
    CACHE_KEY = 'dashboard:evolution'
    CACHE_TTL = 180

    def get(self, request):
        cached = cache.get(self.CACHE_KEY)
        if cached is not None:
            return Response(cached)
        
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

        data = {
            'plantations_par_mois': plantations_par_mois,
            'survie_par_mois': survie_par_mois,
        }
        cache.set(self.CACHE_KEY, data, self.CACHE_TTL)

        return Response(data)


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

class DashboardFinancierView(APIView):
    """
    Vue financière globale — combien a été investi, par qui, où va l'argent,
    et le rendement réel (coût par plant survivant). C'est l'écran qui parle
    directement aux bailleurs et décideurs financiers.
    """
    permission_classes = [IsAuthenticated]
    CACHE_KEY = 'dashboard:financier'
    CACHE_TTL = 180

    def get(self, request):
        cached = cache.get(self.CACHE_KEY)
        if cached is not None:
            return Response(cached)
        
        total_finance = Financement.objects.aggregate(t=Sum('montant'))['t'] or 0

        par_partenaire = list(
            Partenaire.objects.annotate(
                total=Sum('financements__montant'),
                nb_financements=Count('financements'),
            ).filter(total__isnull=False).order_by('-total').values(
                'nom', 'type_partenaire', 'total', 'nb_financements'
            )
        )

        par_type_partenaire = list(
            Financement.objects.values('partenaire__type_partenaire').annotate(
                total=Sum('montant')
            ).order_by('-total')
        )

        budgets = BudgetCampagne.objects.select_related('campagne').all()
        cout_moyen_par_plant = [
            b.cout_par_plant_survivant for b in budgets if b.cout_par_plant_survivant is not None
        ]

        data = {
            'total_finance': total_finance,
            'nombre_partenaires_actifs': Partenaire.objects.filter(actif=True).count(),
            'financement_par_partenaire': par_partenaire,
            'financement_par_type_partenaire': par_type_partenaire,
            'budget_total_alloue': budgets.aggregate(t=Sum('budget_alloue'))['t'] or 0,
            'cout_reel_total': budgets.aggregate(t=Sum('cout_reel'))['t'] or 0,
            'cout_moyen_par_plant_survivant': (
                round(sum(cout_moyen_par_plant) / len(cout_moyen_par_plant), 2)
                if cout_moyen_par_plant else None
            ),
        }
        cache.set(self.CACHE_KEY, data, self.CACHE_TTL)

        return Response(data)


class HealthCheckView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        db_ok = True
        try:
            connection.ensure_connection()
        except Exception:
            db_ok = False

        return Response({
            'status': 'ok' if db_ok else 'degraded',
            'database': 'connected' if db_ok else 'unavailable',
        }, status=200 if db_ok else 503)


@extend_schema(summary="Vue d'ensemble des objectifs (progression, retards)", tags=['Dashboard'])
class DashboardObjectifsView(APIView):
    """
    Vue synthétique de tous les objectifs actifs — le tableau de bord
    que les décideurs consultent en priorité pour suivre les engagements.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        objectifs = ObjectifReboisement.objects.exclude(
            statut=ObjectifReboisement.Statut.ANNULE
        ).select_related('site')

        data = []
        for obj in objectifs:
            data.append({
                'id': obj.id,
                'titre': obj.titre,
                'portee': obj.portee,
                'progression_pourcentage': obj.progression_pourcentage,
                'plants_realises': obj.plants_realises,
                'nombre_plants_cible': obj.nombre_plants_cible,
                'taux_survie_realise': obj.taux_survie_realise,
                'taux_survie_minimum_vise': float(obj.taux_survie_minimum_vise),
                'date_echeance': obj.date_echeance,
                'statut_calcule': obj.statut_calcule,
            })

        return Response({
            'total_objectifs_actifs': len(data),
            'objectifs_atteints': sum(1 for o in data if o['statut_calcule'] == 'ATTEINT'),
            'objectifs_en_retard': sum(1 for o in data if o['statut_calcule'] == 'NON_ATTEINT'),
            'objectifs': data,
        })