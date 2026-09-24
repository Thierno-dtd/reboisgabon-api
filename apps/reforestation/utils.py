def paginer_liste(request, liste, param='page', page_size=20):
   
    try:
        page = int(request.query_params.get(param, 1))
    except (TypeError, ValueError):
        page = 1
    page = max(page, 1)

    total = len(liste)
    start = (page - 1) * page_size
    end = start + page_size

    return {
        'count': total,
        'page': page,
        'page_size': page_size,
        'has_next': end < total,
        'has_previous': page > 1,
        'results': liste[start:end],
    }

COORDONNEES_LOCALITES = {
    'Libreville': (0.4162, 9.4673), 'Kango': (0.1770, 10.1170), 'Ntoum': (0.3906, 9.7614),
    'Franceville': (-1.6333, 13.5833), 'Moanda': (-1.5667, 13.2000), 'Lastoursville': (-0.8167, 12.7167),
    'Lambaréné': (-0.7001, 10.2406), 'Ndjolé': (-0.1833, 10.7667),
    'Mouila': (-1.8667, 11.0556), 'Fougamou': (-1.2167, 10.5833),
    'Tchibanga': (-2.8500, 11.0333), 'Mayumba': (-3.4333, 10.6500),
    'Makokou': (0.5667, 12.8667), 'Booué': (-0.1000, 11.9333),
    'Koulamoutou': (-1.1333, 12.4833), 'Lopé': (-0.2000, 11.6000),
    'Port-Gentil': (-0.7193, 8.7815), 'Omboué': (-1.5746, 9.2618),
    'Oyem': (1.5995, 11.5793), 'Bitam': (2.0833, 11.4833), 'Minvoul': (2.1500, 12.1333),
}


def statistiques_provinces():
    from django.db.models import Avg, Count, Sum
    from .models import SiteReboisement, CampagnePlantation, SuiviCroissance

    base = {
        ligne['province']: ligne for ligne in SiteReboisement.objects.exclude(province='')
        .values('province').annotate(
            nb_sites=Count('id'),
            superficie_totale=Sum('superficie_hectares'),
            latitude_moyenne=Avg('latitude'),
            longitude_moyenne=Avg('longitude'),
        )
    }
    plants = dict(
        CampagnePlantation.objects.exclude(site__province='')
        .values_list('site__province').annotate(total=Sum('nombre_plants'))
    )
    survie = dict(
        SuiviCroissance.objects.exclude(campagne__site__province='')
        .values_list('campagne__site__province').annotate(moyenne=Avg('taux_survie'))
    )
    resultat = []
    for province, ligne in base.items():
        taux = survie.get(province)
        resultat.append({
            'province': province,
            'nb_sites': ligne['nb_sites'],
            'superficie_totale': float(ligne['superficie_totale'] or 0),
            'latitude_moyenne': float(ligne['latitude_moyenne']) if ligne['latitude_moyenne'] is not None else None,
            'longitude_moyenne': float(ligne['longitude_moyenne']) if ligne['longitude_moyenne'] is not None else None,
            'total_plants': plants.get(province) or 0,
            'taux_moyen': round(float(taux), 2) if taux is not None else None,
            'taux_survie_moyen': round(float(taux), 2) if taux is not None else None,
        })
    resultat.sort(key=lambda l: -l['nb_sites'])
    return resultat


_CONTOURS_PROVINCES = None


def _contours_provinces():
    global _CONTOURS_PROVINCES
    if _CONTOURS_PROVINCES is None:
        import json
        from pathlib import Path
        chemin = Path(__file__).resolve().parent / 'fixtures' / 'provinces-gabon.geojson'
        with open(chemin, encoding='utf-8') as flux:
            _CONTOURS_PROVINCES = json.load(flux)
    return _CONTOURS_PROVINCES


def _normaliser(texte):
    import unicodedata
    return ''.join(c for c in unicodedata.normalize('NFD', texte or '') if unicodedata.category(c) != 'Mn').lower().strip()


def _dans_anneau(lon, lat, anneau):
    dedans = False
    j = len(anneau) - 1
    for i in range(len(anneau)):
        xi, yi = anneau[i]
        xj, yj = anneau[j]
        if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / (yj - yi) + xi:
            dedans = not dedans
        j = i
    return dedans


def point_dans_province(latitude, longitude, province):
    for feature in _contours_provinces()['features']:
        if _normaliser(feature['properties']['nom']) != _normaliser(province):
            continue
        geometrie = feature['geometry']
        polygones = geometrie['coordinates'] if geometrie['type'] == 'MultiPolygon' else [geometrie['coordinates']]
        return any(_dans_anneau(longitude, latitude, polygone[0]) for polygone in polygones)
    return False


def coordonnees_pour(localite, province, aleatoire):
    base = COORDONNEES_LOCALITES.get(localite)
    if base is None:
        return None
    for rayon in (0.12, 0.08, 0.05, 0.03, 0.015):
        for _ in range(25):
            lat = base[0] + aleatoire.uniform(-rayon, rayon)
            lon = base[1] + aleatoire.uniform(-rayon, rayon)
            if point_dans_province(lat, lon, province):
                return round(lat, 6), round(lon, 6)
    for pas in range(1, 40):
        for dlat, dlon in ((0, pas * 0.01), (0, -pas * 0.01), (pas * 0.01, 0), (-pas * 0.01, 0)):
            if point_dans_province(base[0] + dlat, base[1] + dlon, province):
                return round(base[0] + dlat, 6), round(base[1] + dlon, 6)
    return base
