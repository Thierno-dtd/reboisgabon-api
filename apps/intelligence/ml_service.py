"""
Prédiction du taux de survie d'une campagne à partir de ses caractéristiques.

Modèle : RandomForestRegressor (scikit-learn) — choisi car robuste aux
relations non linéaires et ne nécessite pas de normalisation des features,
contrairement à une régression linéaire classique.

Limite assumée : le modèle est entraîné sur les suivis historiques disponibles
dans la base. Sa fiabilité dépend directement du volume et de la représentativité
de ces données — à réentraîner régulièrement à mesure que de nouvelles
campagnes et suivis réels sont enregistrés en production.
"""

import joblib
import pandas as pd
from pathlib import Path
from django.conf import settings
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score

MODEL_PATH = Path(settings.ML_MODELS_DIR) / 'modele_survie.joblib'
ENCODERS_PATH = Path(settings.ML_MODELS_DIR) / 'encodeurs.joblib'


def _construire_dataset():
    """Construit un DataFrame à partir des campagnes ayant au moins un suivi."""
    from apps.reforestation.models import CampagnePlantation

    lignes = []
    campagnes = CampagnePlantation.objects.select_related('site', 'essence').prefetch_related('suivis')

    for c in campagnes:
        taux = c.taux_survie_moyen
        if taux is None:
            continue
        lignes.append({
            'essence': c.essence.nom,
            'province': c.site.province or 'Inconnue',
            'superficie_site': float(c.site.superficie_hectares),
            'nombre_plants': c.nombre_plants,
            'mois_plantation': c.date_plantation.month,
            'croissance_rapide': int(c.essence.croissance_rapide),
            'taux_survie': float(taux),
        })

    return pd.DataFrame(lignes)


def entrainer_modele():
    """
    Entraîne (ou réentraîne) le modèle sur les données actuelles de la base.
    À exécuter via `python manage.py entrainer_ia` après un enrichissement
    significatif des données (nouvelles campagnes/suivis).
    """
    df = _construire_dataset()
    if len(df) < 20:
        raise ValueError(
            f"Dataset insuffisant ({len(df)} lignes) pour un entraînement fiable. "
            f"Minimum recommandé : 20 campagnes avec suivis."
        )

    encodeurs = {}
    for colonne in ['essence', 'province']:
        le = LabelEncoder()
        df[f'{colonne}_encode'] = le.fit_transform(df[colonne])
        encodeurs[colonne] = le

    features = [
        'essence_encode', 'province_encode', 'superficie_site',
        'nombre_plants', 'mois_plantation', 'croissance_rapide',
    ]
    X = df[features]
    y = df['taux_survie']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    modele = RandomForestRegressor(n_estimators=150, max_depth=8, random_state=42)
    modele.fit(X_train, y_train)

    y_pred = modele.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)

    Path(settings.ML_MODELS_DIR).mkdir(exist_ok=True)
    joblib.dump(modele, MODEL_PATH)
    joblib.dump(encodeurs, ENCODERS_PATH)

    return {
        'nombre_echantillons': len(df),
        'mae': round(mae, 2),      # erreur moyenne absolue, en points de %
        'r2_score': round(r2, 3),  # qualité d'ajustement (1 = parfait, 0 = aucun pouvoir prédictif)
        'features_importance': dict(zip(features, [round(f, 3) for f in modele.feature_importances_])),
    }


def predire_taux_survie(essence_nom, province, superficie_site, nombre_plants, mois_plantation, croissance_rapide):
    """Prédit le taux de survie attendu pour une campagne hypothétique (pas encore créée)."""
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            "Aucun modèle entraîné. Exécutez d'abord : python manage.py entrainer_ia"
        )

    modele = joblib.load(MODEL_PATH)
    encodeurs = joblib.load(ENCODERS_PATH)

    def _encoder_securise(encodeur, valeur):
        """Gère le cas d'une essence/province jamais vue à l'entraînement."""
        if valeur in encodeur.classes_:
            return encodeur.transform([valeur])[0]
        return -1  # valeur hors vocabulaire connu

    X = pd.DataFrame([{
        'essence_encode': _encoder_securise(encodeurs['essence'], essence_nom),
        'province_encode': _encoder_securise(encodeurs['province'], province),
        'superficie_site': superficie_site,
        'nombre_plants': nombre_plants,
        'mois_plantation': mois_plantation,
        'croissance_rapide': int(croissance_rapide),
    }])

    prediction = modele.predict(X)[0]
    return round(max(0, min(100, prediction)), 1)


def recommander_essences(province, superficie_site, top_n=3):
    """
    Recommande les essences les plus performantes historiquement pour une
    province donnée — approche par comparaison statistique (moyenne par groupe),
    plus robuste et plus explicable qu'une prédiction ML pour ce cas d'usage précis.
    """
    from apps.reforestation.models import CampagnePlantation
    from django.db.models import Avg, Count

    resultats = CampagnePlantation.objects.filter(
        site__province=province
    ).values('essence__nom', 'essence__croissance_rapide').annotate(
        taux_moyen=Avg('suivis__taux_survie'),
        nb_campagnes=Count('id'),
    ).filter(taux_moyen__isnull=False, nb_campagnes__gte=2).order_by('-taux_moyen')[:top_n]

    return [
        {
            'essence': r['essence__nom'],
            'croissance_rapide': r['essence__croissance_rapide'],
            'taux_survie_moyen_historique': round(r['taux_moyen'], 1),
            'nombre_campagnes_analysees': r['nb_campagnes'],
        }
        for r in resultats
    ]