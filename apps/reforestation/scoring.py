"""
Calcul du score écologique d'un site — formule pondérée et transparente,
volontairement explicable (chaque composante est documentée), contrairement
à un modèle "boîte noire".

Score final sur 100, décomposé en 4 axes :
- Survie (50%)      : taux de survie moyen du site
- Régularité (20%)  : fréquence réelle des contrôles par rapport à l'attendu (1 tous les 2 mois)
- Diversité (15%)   : nombre d'essences différentes plantées sur le site
- Vitalité (15%)    : statut du site (EN_COURS/TERMINE valorisés, SUSPENDU pénalisé)
"""

from datetime import date
from django.db.models import Avg, Count

PONDERATION_SURVIE = 0.50
PONDERATION_REGULARITE = 0.20
PONDERATION_DIVERSITE = 0.15
PONDERATION_VITALITE = 0.15

BAREME_STATUT = {
    'EN_COURS': 100,
    'TERMINE': 90,
    'PLANIFIE': 60,
    'SUSPENDU': 20,
}

DIVERSITE_CIBLE = 4  # 4 essences différentes ou plus = score diversité maximal


def _score_survie(site):
    taux = site.taux_survie_moyen
    if taux is None:
        return None, 0  # pas encore de données -> composante neutre (0), signalé côté "None"
    return round(taux, 1), min(float(taux), 100)


def _score_regularite(site):
    """
    Compare le nombre de suivis réels au nombre de suivis 'attendus'
    (1 tous les 2 mois depuis la date de la 1ère campagne du site).
    """
    from apps.reforestation.models import CampagnePlantation, SuiviCroissance

    campagnes = CampagnePlantation.objects.filter(site=site)
    if not campagnes.exists():
        return None, 0

    plus_ancienne = campagnes.order_by('date_plantation').first().date_plantation
    jours_ecoules = max((date.today() - plus_ancienne).days, 1)
    suivis_attendus = max(jours_ecoules // 60, 1)

    suivis_reels = SuiviCroissance.objects.filter(campagne__site=site).count()
    taux_regularite = min(suivis_reels / suivis_attendus * 100, 100)
    return round(taux_regularite, 1), taux_regularite


def _score_diversite(site):
    from apps.reforestation.models import CampagnePlantation

    nb_essences = CampagnePlantation.objects.filter(site=site).values('essence').distinct().count()
    if nb_essences == 0:
        return 0, 0
    score = min(nb_essences / DIVERSITE_CIBLE * 100, 100)
    return nb_essences, score


def _score_vitalite(site):
    score = BAREME_STATUT.get(site.statut, 50)
    return site.get_statut_display(), score


def calculer_score_ecologique(site):
    """Retourne le score global (0-100) et le détail explicable de chaque composante."""

    taux_survie, score_survie = _score_survie(site)
    taux_regularite, score_regularite = _score_regularite(site)
    nb_essences, score_diversite = _score_diversite(site)
    statut_label, score_vitalite = _score_vitalite(site)

    score_global = (
        score_survie * PONDERATION_SURVIE +
        score_regularite * PONDERATION_REGULARITE +
        score_diversite * PONDERATION_DIVERSITE +
        score_vitalite * PONDERATION_VITALITE
    )

    if score_global >= 80:
        classe = 'EXCELLENT'
    elif score_global >= 60:
        classe = 'BON'
    elif score_global >= 40:
        classe = 'MOYEN'
    else:
        classe = 'FAIBLE'

    return {
        'score_global': round(score_global, 1),
        'classe': classe,
        'details': {
            'survie': {
                'valeur': taux_survie, 'score_sur_100': round(score_survie, 1),
                'ponderation': PONDERATION_SURVIE,
            },
            'regularite_suivi': {
                'valeur_pourcentage': taux_regularite, 'score_sur_100': round(score_regularite, 1),
                'ponderation': PONDERATION_REGULARITE,
            },
            'diversite_essences': {
                'nombre_essences': nb_essences, 'score_sur_100': round(score_diversite, 1),
                'ponderation': PONDERATION_DIVERSITE,
            },
            'vitalite_statut': {
                'statut': statut_label, 'score_sur_100': score_vitalite,
                'ponderation': PONDERATION_VITALITE,
            },
        },
    }