from django.core.management.base import BaseCommand
from django.core.mail import EmailMessage
from django.conf import settings
from django.test import RequestFactory

from apps.accounts.models import User
from apps.dashboard.views import DashboardOverviewView, DashboardParSiteView, DashboardParEssenceView
from apps.exports import pdf_service


class Command(BaseCommand):
    """
    Génère le rapport de synthèse PDF et l'envoie par email à tous les
    administrateurs actifs. À planifier en cron (hebdomadaire ou mensuel).
    """
    help = "Envoie automatiquement le rapport de synthèse PDF aux administrateurs."

    def handle(self, *args, **options):
        admin_reference = User.objects.filter(role=User.Role.ADMIN, is_active=True).first()
        if not admin_reference:
            self.stderr.write(self.style.ERROR("Aucun administrateur actif trouvé."))
            return

        request = RequestFactory().get('/')
        request.user = admin_reference

        overview_data = DashboardOverviewView().get(request).data
        sites_data = DashboardParSiteView().get(request).data
        essences_data = DashboardParEssenceView().get(request).data

        buffer = pdf_service.generer_rapport_overview_pdf(overview_data, sites_data, essences_data)

        destinataires = list(
            User.objects.filter(role=User.Role.ADMIN, is_active=True)
            .exclude(email='').values_list('email', flat=True)
        )
        if not destinataires:
            self.stdout.write(self.style.WARNING("Aucun email administrateur valide."))
            return

        email = EmailMessage(
            subject="ReboisGabon — Rapport périodique de synthèse",
            body="Rapport généré automatiquement. Voir la pièce jointe.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=destinataires,
        )
        email.attach('rapport_reboisgabon.pdf', buffer.getvalue(), 'application/pdf')
        email.send(fail_silently=False)

        self.stdout.write(self.style.SUCCESS(f"Rapport envoyé à {len(destinataires)} administrateur(s)."))