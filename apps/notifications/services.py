from django.core.mail import send_mail
from django.conf import settings
from .models import Notification


def notifier(destinataire, type_notification, titre, message, envoyer_email=False,
             lien_objet_id='', lien_modele=''):
    """
    Point d'entrée unique pour créer une notification.
    Crée toujours la notification interne (visible dans le client JavaFX),
    et envoie un email en plus si envoyer_email=True (cas critique).
    """
    notif = Notification.objects.create(
        destinataire=destinataire,
        type_notification=type_notification,
        titre=titre,
        message=message,
        lien_objet_id=str(lien_objet_id),
        lien_modele=lien_modele,
    )

    if envoyer_email and destinataire.email:
        send_mail(
            subject=f"ReboisGabon — {titre}",
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[destinataire.email],
            fail_silently=True,
        )

    return notif