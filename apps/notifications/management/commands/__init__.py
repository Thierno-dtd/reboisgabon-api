from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Avg

from apps.reforestation.models import CampagnePlantation
from apps.accounts.models import User
from apps.notifications.services import notifier
from apps.notifications.models import Notification

SEUIL_CRITIQUE = 50.0
JOURS_SANS_SUIVI = 90


class Command(BaseCommand):
    """
    À exécuter périodiquement (cron / tâche planifiée) : détecte les campagnes
    en taux critique ou sans suivi récent, et notifie les administrateurs +
    le responsable de la campagne concernée.

    Usage : python manage.py check_alertes
    En production : à brancher sur un cron quotidien (ex: `0 7 * * * python manage.py check_alertes`)
    """
    help = "Vérifie les campagnes à risque et génère les notifications correspondantes."

    def handle(self, *args, **options):
        admins = list(User.objects.filter(role=User.Role.ADMIN, is_active=True))
        nb_notifs = 0

        # 1. Taux de survie critique
        campagnes_critiques = CampagnePlantation.objects.annotate(
            taux_moyen=Avg('suivis__taux_survie')
        ).filter(taux_moyen__lt=SEUIL_CRITIQUE, taux_moyen__isnull=False)

        for campagne in campagnes_critiques:
            destinataires = set(admins)
            if campagne.responsable:
                destinataires.add(campagne.responsable)

            for user in destinataires:
                deja_notifie = Notification.objects.filter(
                    destinataire=user, type_notification=Notification.Type.TAUX_CRITIQUE,
                    lien_objet_id=str(campagne.id),
                    created_at__gte=timezone.now() - timedelta(days=7)
                ).exists()
                if not deja_notifie:
                    notifier(
                        destinataire=user,
                        type_notification=Notification.Type.TAUX_CRITIQUE,
                        titre=f"Taux de survie critique — {campagne.site.nom}",
                        message=(
                            f"La campagne {campagne.essence.nom} du {campagne.date_plantation} "
                            f"sur le site {campagne.site.nom} affiche un taux de survie moyen de "
                            f"{round(campagne.taux_moyen, 1)}%, en dessous du seuil critique de {SEUIL_CRITIQUE}%."
                        ),
                        envoyer_email=True,
                        lien_objet_id=campagne.id, lien_modele='CampagnePlantation',
                    )
                    nb_notifs += 1

        # 2. Campagnes sans suivi récent
        limite_date = timezone.now().date() - timedelta(days=JOURS_SANS_SUIVI)
        campagnes_sans_suivi = CampagnePlantation.objects.filter(
            date_plantation__lt=limite_date
        ).exclude(suivis__date_controle__gte=limite_date).distinct()

        for campagne in campagnes_sans_suivi:
            destinataires = set(admins)
            if campagne.responsable:
                destinataires.add(campagne.responsable)

            for user in destinataires:
                deja_notifie = Notification.objects.filter(
                    destinataire=user, type_notification=Notification.Type.SUIVI_EN_RETARD,
                    lien_objet_id=str(campagne.id),
                    created_at__gte=timezone.now() - timedelta(days=7)
                ).exists()
                if not deja_notifie:
                    notifier(
                        destinataire=user,
                        type_notification=Notification.Type.SUIVI_EN_RETARD,
                        titre=f"Suivi en retard — {campagne.site.nom}",
                        message=(
                            f"Aucun contrôle de croissance n'a été effectué depuis plus de "
                            f"{JOURS_SANS_SUIVI} jours pour la campagne {campagne.essence.nom} "
                            f"du site {campagne.site.nom}."
                        ),
                        envoyer_email=False,
                        lien_objet_id=campagne.id, lien_modele='CampagnePlantation',
                    )
                    nb_notifs += 1

        self.stdout.write(self.style.SUCCESS(f"{nb_notifs} nouvelle(s) notification(s) générée(s)."))