from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.accounts.models import User
from .services import notifier
from .models import Notification


@receiver(post_save, sender=User)
def notifier_creation_compte(sender, instance, created, **kwargs):
    if created:
        notifier(
            destinataire=instance,
            type_notification=Notification.Type.COMPTE_CREE,
            titre="Bienvenue sur ReboisGabon",
            message=f"Votre compte a été créé par un administrateur. Email : {instance.email}.",
            envoyer_email=False,  # évite de spammer pendant le seed
        )