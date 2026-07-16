import uuid
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.conf import settings
from .managers import UserManager
import pyotp


class User(AbstractBaseUser, PermissionsMixin):
    """
    Utilisateur custom : login par email.
    Deux rôles métier : ADMIN (gère les comptes) et AGENT (utilisateur terrain).
    """

    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Administrateur'
        AGENT = 'AGENT', 'Agent de terrain'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.AGENT)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    two_fa_enabled = models.BooleanField(default=False)

    date_joined = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='created_users'
    )

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        db_table = 'users'
        verbose_name = 'Utilisateur'
        verbose_name_plural = 'Utilisateurs'
        ordering = ['-date_joined']

    def __str__(self):
        return f"{self.get_full_name()} ({self.email})"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN


class PasswordResetToken(models.Model):
    """Token à usage unique pour la réinitialisation de mot de passe."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reset_tokens')
    token = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)

    class Meta:
        db_table = 'password_reset_tokens'

    def is_valid(self):
        return not self.used and timezone.now() < self.expires_at

    def __str__(self):
        return f"Reset token for {self.user.email}"
    

class TOTPDevice(models.Model):
    """Secret TOTP associé à un utilisateur, façon Google Authenticator."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='totp_device')
    secret = models.CharField(max_length=32, default=pyotp.random_base32)
    confirmed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'totp_devices'

    def get_totp(self):
        return pyotp.TOTP(self.secret)

    def verify(self, code):
        return self.get_totp().verify(code, valid_window=1)

    def get_provisioning_uri(self):
        return self.get_totp().provisioning_uri(
            name=self.user.email,
            issuer_name='ReboisGabon'
        )