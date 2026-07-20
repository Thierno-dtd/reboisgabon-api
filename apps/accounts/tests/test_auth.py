from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from apps.accounts.models import User, TOTPDevice
import pyotp


class AuthFlowTests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@reboisgabon.ga', password='TestPass123',
            first_name='Test', last_name='User'
        )

    def test_login_sans_2fa_renvoie_tokens_directs(self):
        url = reverse('login')
        response = self.client.post(url, {
            'email': 'test@reboisgabon.ga', 'password': 'TestPass123'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertFalse(response.data['requires_2fa'])

    def test_login_mauvais_mot_de_passe_refuse(self):
        url = reverse('login')
        response = self.client.post(url, {
            'email': 'test@reboisgabon.ga', 'password': 'wrong'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_avec_2fa_active_demande_code_otp(self):
        device = TOTPDevice.objects.create(user=self.user, confirmed=True)
        self.user.two_fa_enabled = True
        self.user.save()

        url = reverse('login')
        response = self.client.post(url, {
            'email': 'test@reboisgabon.ga', 'password': 'TestPass123'
        })
        self.assertTrue(response.data['requires_2fa'])
        self.assertIn('temp_token', response.data)

        # Étape 2 : vérification OTP
        totp = pyotp.TOTP(device.secret)
        verify_url = reverse('login-2fa-verify')
        response2 = self.client.post(verify_url, {
            'temp_token': response.data['temp_token'],
            'otp_code': totp.now(),
        })
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertIn('access', response2.data)

    def test_forgot_password_genere_token_et_reset_fonctionne(self):
        forgot_url = reverse('password-forgot')
        self.client.post(forgot_url, {'email': 'test@reboisgabon.ga'})

        from apps.accounts.models import PasswordResetToken
        token_obj = PasswordResetToken.objects.filter(user=self.user).first()
        self.assertIsNotNone(token_obj)

        reset_url = reverse('password-reset')
        response = self.client.post(reset_url, {
            'token': token_obj.token, 'new_password': 'NouveauPass123'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        token_obj.refresh_from_db()
        self.assertTrue(token_obj.used)

        # L'ancien mot de passe ne doit plus fonctionner
        login_response = self.client.post(reverse('login'), {
            'email': 'test@reboisgabon.ga', 'password': 'TestPass123'
        })
        self.assertEqual(login_response.status_code, status.HTTP_400_BAD_REQUEST)


class UserModuleTests(APITestCase):

    def setUp(self):
        self.admin = User.objects.create_superuser(
            email='admin@reboisgabon.ga', password='Admin@123',
            first_name='Admin', last_name='Root'
        )
        self.agent = User.objects.create_user(
            email='agent@reboisgabon.ga', password='Agent@123',
            first_name='Agent', last_name='Terrain', role=User.Role.AGENT
        )

    def test_agent_ne_peut_pas_lister_utilisateurs(self):
        self.client.force_authenticate(user=self.agent)
        response = self.client.get('/api/users/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_peut_creer_utilisateur(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post('/api/users/', {
            'email': 'nouveau@reboisgabon.ga', 'first_name': 'Nouveau',
            'last_name': 'Compte', 'role': 'AGENT', 'password': 'Pass12345'
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_suppression_sans_confirmation_refusee(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.delete(f'/api/users/{self.agent.id}/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_suppression_avec_confirmation_desactive_compte(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.delete(f'/api/users/{self.agent.id}/?confirm=true')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.agent.refresh_from_db()
        self.assertFalse(self.agent.is_active)