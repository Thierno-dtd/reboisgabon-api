from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from apps.accounts.models import User
from apps.reforestation.models import Essence, SiteReboisement, CampagnePlantation, SuiviCroissance
from datetime import date


class SiteFiltresTests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email='u@reboisgabon.ga', password='Pass1234', first_name='U', last_name='Ser'
        )
        self.client.force_authenticate(user=self.user)

        self.essence = Essence.objects.create(nom='Okoumé')
        self.site1 = SiteReboisement.objects.create(
            nom='Site A', localite='Lopé', superficie_hectares=100, statut='EN_COURS'
        )
        self.site2 = SiteReboisement.objects.create(
            nom='Site B', localite='Makokou', superficie_hectares=50, statut='TERMINE'
        )

        campagne = CampagnePlantation.objects.create(
            site=self.site1, essence=self.essence,
            date_plantation=date(2025, 3, 1), nombre_plants=1000
        )
        SuiviCroissance.objects.create(
            campagne=campagne, date_controle=date(2025, 6, 1), taux_survie=85
        )

    def test_filtre_par_localite(self):
        response = self.client.get('/api/sites/?localite=Lopé')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)

    def test_filtre_par_statut(self):
        response = self.client.get('/api/sites/?statut=TERMINE')
        self.assertEqual(response.data['count'], 1)

    def test_filtres_combinables_campagnes(self):
        response = self.client.get(
            '/api/campagnes/?essence_nom=okoumé&date_debut=2025-01-01&date_fin=2025-12-31'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)

    def test_taux_survie_moyen_calcule_sur_site(self):
        self.site1.refresh_from_db()
        self.assertEqual(self.site1.taux_survie_moyen, 85.0)

    def test_suppression_sans_confirmation_refusee(self):
        response = self.client.delete(f'/api/sites/{self.site2.id}/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)