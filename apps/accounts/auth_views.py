import secrets
from datetime import timedelta

from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken

from .models import User, PasswordResetToken, TOTPDevice
from .serializers import (
    LoginSerializer, TwoFAVerifySerializer,
    ForgotPasswordSerializer, ResetPasswordSerializer, TOTPSetupSerializer
)
from apps.audit.models import JournalActivite
from apps.audit.middleware import get_current_ip

from apps.accounts import serializers


def tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {'access': str(refresh.access_token), 'refresh': str(refresh)}


class LoginView(APIView):
    """
    Étape 1 : email + mot de passe.
    - Si 2FA désactivée -> renvoie directement les tokens JWT.
    - Si 2FA activée -> renvoie un temp_token à usage unique, à fournir avec le code OTP.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            JournalActivite.objects.create(
                action=JournalActivite.Action.CONNEXION_ECHOUEE,
                modele='User',
                objet_repr=request.data.get('email', 'inconnu'),
                adresse_ip=get_current_ip(),
            )
            raise serializers.ValidationError(serializer.errors)

        user = serializer.validated_data['user']

        if user.two_fa_enabled:
            temp_token = AccessToken.for_user(user)
            temp_token.set_exp(lifetime=timedelta(minutes=5))
            temp_token['purpose'] = '2fa_pending'
            return Response({'requires_2fa': True, 'temp_token': str(temp_token)})

        JournalActivite.objects.create(
            utilisateur=user, action=JournalActivite.Action.CONNEXION,
            modele='User', objet_id=str(user.id), objet_repr=user.email,
            adresse_ip=get_current_ip(),
        )
        return Response({'requires_2fa': False, **tokens_for_user(user)})


class TwoFAVerifyView(APIView):
    """Étape 2 : vérifie le code TOTP et délivre les vrais tokens JWT."""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = TwoFAVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            temp_token = AccessToken(serializer.validated_data['temp_token'])
            if temp_token.get('purpose') != '2fa_pending':
                raise ValueError
            user = User.objects.get(id=temp_token['user_id'])
        except Exception:
            return Response({'detail': 'Token temporaire invalide ou expiré.'},
                             status=status.HTTP_401_UNAUTHORIZED)

        try:
            device = user.totp_device
        except TOTPDevice.DoesNotExist:
            return Response({'detail': "2FA non configurée pour cet utilisateur."},
                             status=status.HTTP_400_BAD_REQUEST)

        if not device.verify(serializer.validated_data['otp_code']):
            return Response({'detail': 'Code OTP invalide.'}, status=status.HTTP_401_UNAUTHORIZED)

        JournalActivite.objects.create(
            utilisateur=user, action=JournalActivite.Action.CONNEXION,
            modele='User', objet_id=str(user.id), objet_repr=user.email,
            adresse_ip=get_current_ip(),
        )
        return Response(tokens_for_user(user))


class ForgotPasswordView(APIView):
    """Génère un token unique, envoyé par email, expirant dans 1h."""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        try:
            user = User.objects.get(email=email, is_active=True)
        except User.DoesNotExist:
            # Volontairement : même réponse que si l'utilisateur existe (anti-énumération)
            return Response({'detail': "Si ce compte existe, un email a été envoyé."})

        token = secrets.token_urlsafe(48)
        PasswordResetToken.objects.create(
            user=user,
            token=token,
            expires_at=timezone.now() + timedelta(hours=1)
        )

        reset_link = f"{settings.FRONTEND_RESET_URL}?token={token}"
        send_mail(
            subject="ReboisGabon — Réinitialisation de mot de passe",
            message=f"Bonjour {user.first_name},\n\nCliquez sur ce lien pour réinitialiser votre mot de passe "
                    f"(valable 1h) :\n{reset_link}\n\nSi vous n'êtes pas à l'origine de cette demande, ignorez cet email.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
        )

        return Response({'detail': "Si ce compte existe, un email a été envoyé."})


class ResetPasswordView(APIView):
    """Réinitialise le mot de passe via le token reçu, puis l'invalide."""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            reset_token = PasswordResetToken.objects.get(token=serializer.validated_data['token'])
        except PasswordResetToken.DoesNotExist:
            return Response({'detail': 'Token invalide.'}, status=status.HTTP_400_BAD_REQUEST)

        if not reset_token.is_valid():
            return Response({'detail': 'Token expiré ou déjà utilisé.'}, status=status.HTTP_400_BAD_REQUEST)

        user = reset_token.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()

        reset_token.used = True
        reset_token.save()

        return Response({'detail': 'Mot de passe réinitialisé avec succès.'})


class TOTPSetupInitView(APIView):
    """Génère (ou régénère) le secret TOTP et renvoie l'URI de provisioning (QR code)."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        device, _ = TOTPDevice.objects.get_or_create(user=request.user)
        return Response({
            'secret': device.secret,
            'provisioning_uri': device.get_provisioning_uri()
        })


class TOTPSetupConfirmView(APIView):
    """Confirme l'activation de la 2FA après scan du QR code et saisie du 1er code."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = TOTPSetupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            device = request.user.totp_device
        except TOTPDevice.DoesNotExist:
            return Response({'detail': "Aucun secret TOTP généré. Appelez d'abord /2fa/setup/init/."},
                             status=status.HTTP_400_BAD_REQUEST)

        if not device.verify(serializer.validated_data['otp_code']):
            return Response({'detail': 'Code invalide.'}, status=status.HTTP_400_BAD_REQUEST)

        device.confirmed = True
        device.save()
        request.user.two_fa_enabled = True
        request.user.save()

        return Response({'detail': '2FA activée avec succès.'})


class TOTPDisableView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        request.user.two_fa_enabled = False
        request.user.save()
        TOTPDevice.objects.filter(user=request.user).delete()
        return Response({'detail': '2FA désactivée.'})


class MeView(APIView):
    """Infos du user connecté — pratique pour le client JavaFX après login."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        u = request.user
        return Response({
            'id': str(u.id),
            'email': u.email,
            'first_name': u.first_name,
            'last_name': u.last_name,
            'role': u.role,
            'two_fa_enabled': u.two_fa_enabled,
        })