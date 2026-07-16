from rest_framework import serializers
from django.contrib.auth import authenticate
from django.utils import timezone
from .models import User, PasswordResetToken, TOTPDevice


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})

    def validate(self, attrs):
        user = authenticate(email=attrs['email'], password=attrs['password'])
        if not user:
            raise serializers.ValidationError("Email ou mot de passe incorrect.")
        if not user.is_active:
            raise serializers.ValidationError("Ce compte est désactivé.")
        attrs['user'] = user
        return attrs


class TwoFAVerifySerializer(serializers.Serializer):
    """Étape 2 du login : vérification du code TOTP après le mot de passe."""
    temp_token = serializers.CharField()
    otp_code = serializers.CharField(max_length=6, min_length=6)


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ResetPasswordSerializer(serializers.Serializer):
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_new_password(self, value):
        if value.isdigit() or value.isalpha():
            raise serializers.ValidationError(
                "Le mot de passe doit contenir au moins une lettre et un chiffre."
            )
        return value


class TOTPSetupSerializer(serializers.Serializer):
    otp_code = serializers.CharField(max_length=6, min_length=6)

class UserListSerializer(serializers.ModelSerializer):
    """Utilisé pour la liste et le détail."""

    full_name = serializers.CharField(source='get_full_name', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'role', 'is_active', 'two_fa_enabled', 'date_joined', 'created_by',
        ]
        read_only_fields = ['id', 'date_joined', 'created_by', 'two_fa_enabled']


class UserCreateSerializer(serializers.ModelSerializer):
    """Création d'un compte par l'admin. Génère un mot de passe temporaire si non fourni."""

    password = serializers.CharField(write_only=True, required=False, min_length=8)

    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'role', 'password', 'is_active']
        read_only_fields = ['id']

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Un compte existe déjà avec cet email.")
        return value.lower()

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        request = self.context.get('request')

        user = User(**validated_data)
        if password:
            user.set_password(password)
        else:
            import secrets
            user.set_password(secrets.token_urlsafe(12))

        if request and request.user.is_authenticated:
            user.created_by = request.user

        user.save()
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """Mise à jour par l'admin : peut changer rôle, statut actif, etc."""

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'role', 'is_active']


class MeUpdateSerializer(serializers.ModelSerializer):
    """Un utilisateur met à jour son propre profil : pas de rôle, pas de statut actif."""

    class Meta:
        model = User
        fields = ['first_name', 'last_name']


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)