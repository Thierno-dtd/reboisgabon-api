import random
from datetime import timedelta, date
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.reforestation.models import Essence, SiteReboisement, CampagnePlantation, SuiviCroissance


PROVINCES_GABON = [
    "Estuaire", "Haut-Ogooué", "Moyen-Ogooué", "Ngounié",
    "Nyanga", "Ogooué-Ivindo", "Ogooué-Lolo", "Ogooué-Maritime",
    "Woleu-Ntem",
]

LOCALITES = [
    ("Libreville", "Estuaire"), ("Kango", "Estuaire"), ("Ntoum", "Estuaire"),
    ("Franceville", "Haut-Ogooué"), ("Moanda", "Haut-Ogooué"), ("Lastoursville", "Haut-Ogooué"),
    ("Lambaréné", "Moyen-Ogooué"), ("Ndjolé", "Moyen-Ogooué"),
    ("Mouila", "Ngounié"), ("Fougamou", "Ngounié"),
    ("Tchibanga", "Nyanga"), ("Mayumba", "Nyanga"),
    ("Makokou", "Ogooué-Ivindo"), ("Booué", "Ogooué-Ivindo"),
    ("Koulamoutou", "Ogooué-Lolo"), ("Lopé", "Ogooué-Lolo"),
    ("Port-Gentil", "Ogooué-Maritime"), ("Omboué", "Ogooué-Maritime"),
    ("Oyem", "Woleu-Ntem"), ("Bitam", "Woleu-Ntem"), ("Minvoul", "Woleu-Ntem"),
]

SITE_PREFIXES = [
    "Forêt de", "Périmètre de", "Zone de reboisement de", "Réserve de",
    "Bloc forestier de", "Parcelle pilote de",
]

ESSENCES_DATA = [
    ("Okoumé", "Aucoumea klaineana", True),
    ("Moabi", "Baillonella toxisperma", False),
    ("Padouk", "Pterocarpus soyauxii", False),
    ("Kevazingo", "Guibourtia tessmannii", False),
    ("Eucalyptus", "Eucalyptus spp.", True),
    ("Acacia", "Acacia mangium", True),
    ("Azobé", "Lophira alata", False),
    ("Movingui", "Distemonanthus benthamianus", False),
    ("Ozigo", "Dacryodes buettneri", False),
    ("Tali", "Erythrophleum ivorense", False),
]

PRENOMS = ["Jean", "Marie", "Paul", "Sylvie", "Pierre", "Alice", "David", "Christelle",
           "Emmanuel", "Nadège", "Serge", "Judith", "Franck", "Vanessa", "Patrick"]
NOMS = ["Mba", "Ndong", "Obiang", "Nzue", "Moussavou", "Bongo", "Ella", "Nguema",
        "Ondo", "Assengone", "Mabika", "Ogandaga"]

OBSERVATIONS = [
    "Croissance homogène, aucun signe de stress hydrique.",
    "Quelques plants attaqués par les termites, traitement appliqué.",
    "Sécheresse locale ayant affecté la parcelle nord.",
    "Développement conforme aux attentes.",
    "Sol dégradé identifié sur une partie du site, replantation partielle recommandée.",
    "Excellente reprise après la saison des pluies.",
    "Concurrence des adventices à surveiller.",
    "Aucune observation particulière.",
]


class Command(BaseCommand):
    help = "Génère un jeu de données de démonstration volumineux pour ReboisGabon."

    def add_arguments(self, parser):
        parser.add_argument('--flush', action='store_true', help="Vide les données métier avant de re-seeder.")

    @transaction.atomic
    def handle(self, *args, **options):
        if options['flush']:
            self.stdout.write("Suppression des anciennes données métier...")
            SuiviCroissance.objects.all().delete()
            CampagnePlantation.objects.all().delete()
            SiteReboisement.objects.all().delete()
            Essence.objects.all().delete()
            User.objects.filter(is_superuser=False).delete()

        admin = self._seed_admin()
        agents = self._seed_agents()
        essences = self._seed_essences()
        sites = self._seed_sites(agents)
        campagnes = self._seed_campagnes(sites, essences, agents)
        self._seed_suivis(campagnes, agents)

        self.stdout.write(self.style.SUCCESS(
            f"\nSeed terminé :\n"
            f"  - 1 admin (admin@reboisgabon.ga / Admin@123)\n"
            f"  - {len(agents)} agents\n"
            f"  - {len(essences)} essences\n"
            f"  - {len(sites)} sites\n"
            f"  - {len(campagnes)} campagnes\n"
            f"  - {SuiviCroissance.objects.count()} suivis de croissance\n"
        ))

    def _seed_admin(self):
        admin, created = User.objects.get_or_create(
            email='admin@reboisgabon.ga',
            defaults={
                'first_name': 'Admin', 'last_name': 'ReboisGabon',
                'role': User.Role.ADMIN, 'is_staff': True, 'is_superuser': True,
            }
        )
        if created:
            admin.set_password('Admin@123')
            admin.save()
        return admin

    def _seed_agents(self, n=12):
        agents = []
        used_emails = set()
        for i in range(n):
            prenom = random.choice(PRENOMS)
            nom = random.choice(NOMS)
            email = f"{prenom.lower()}.{nom.lower()}{i}@reboisgabon.ga"
            if email in used_emails:
                continue
            used_emails.add(email)

            agent, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': prenom, 'last_name': nom,
                    'role': User.Role.AGENT,
                }
            )
            if created:
                agent.set_password('Agent@123')
                agent.save()
            agents.append(agent)
        return agents

    def _seed_essences(self):
        essences = []
        for nom, nom_sci, rapide in ESSENCES_DATA:
            essence, _ = Essence.objects.get_or_create(
                nom=nom, defaults={'nom_scientifique': nom_sci, 'croissance_rapide': rapide}
            )
            essences.append(essence)
        return essences

    def _seed_sites(self, agents, n=18):
        sites = []
        statuts = [c[0] for c in SiteReboisement.Statut.choices]

        for i in range(n):
            localite, province = random.choice(LOCALITES)
            prefixe = random.choice(SITE_PREFIXES)
            nom = f"{prefixe} {localite} {['Nord', 'Sud', 'Est', 'Ouest', ''][i % 5]}".strip()

            site = SiteReboisement.objects.create(
                nom=nom,
                localite=localite,
                province=province,
                superficie_hectares=Decimal(random.uniform(15, 400)).quantize(Decimal('0.01')),
                statut=random.choices(statuts, weights=[15, 45, 30, 10])[0],
                latitude=Decimal(random.uniform(-3.9, 2.3)).quantize(Decimal('0.000001')),
                longitude=Decimal(random.uniform(8.7, 14.5)).quantize(Decimal('0.000001')),
                responsable=random.choice(agents),
            )
            sites.append(site)
        return sites

    def _seed_campagnes(self, sites, essences, agents, min_par_site=3, max_par_site=9):
        campagnes = []
        today = date.today()
        start_range = today - timedelta(days=730)  # 2 ans d'historique

        for site in sites:
            nb = random.randint(min_par_site, max_par_site)
            for _ in range(nb):
                jours_offset = random.randint(0, 730)
                date_plantation = start_range + timedelta(days=jours_offset)

                campagne = CampagnePlantation.objects.create(
                    site=site,
                    essence=random.choice(essences),
                    date_plantation=date_plantation,
                    nombre_plants=random.randint(200, 5000),
                    responsable=random.choice(agents),
                )
                campagnes.append(campagne)
        return campagnes

    def _seed_suivis(self, campagnes, agents):
        today = date.today()

        for campagne in campagnes:
            # Nombre de contrôles dépend de l'ancienneté de la campagne
            jours_ecoules = (today - campagne.date_plantation).days
            nb_controles = min(max(jours_ecoules // 60, 1), 8)  # un contrôle tous les ~2 mois, max 8

            # Tendance de survie propre à la campagne (certaines campagnes réussissent mieux que d'autres)
            tendance = random.choice(['excellente', 'bonne', 'moyenne', 'difficile'])
            taux_base = {
                'excellente': 92, 'bonne': 80, 'moyenne': 65, 'difficile': 45,
            }[tendance]

            taux_courant = 100.0  # au début, 100% des plants sont vivants
            date_courante = campagne.date_plantation

            for c in range(nb_controles):
                date_courante = date_courante + timedelta(days=random.randint(45, 75))
                if date_courante > today:
                    break

                # Le taux décroît progressivement vers le taux "cible" de la tendance, avec du bruit
                decroissance = (100 - taux_base) / max(nb_controles, 1)
                taux_courant = max(0, taux_courant - decroissance + random.uniform(-4, 4))
                taux_courant = min(100, taux_courant)

                nombre_vivants = int(campagne.nombre_plants * (taux_courant / 100))

                SuiviCroissance.objects.create(
                    campagne=campagne,
                    date_controle=date_courante,
                    taux_survie=Decimal(str(round(taux_courant, 2))),
                    nombre_plants_vivants=nombre_vivants,
                    observations=random.choice(OBSERVATIONS),
                    controle_par=random.choice(agents),
                )