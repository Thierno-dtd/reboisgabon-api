import random
import unicodedata
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Min, Q

from apps.accounts.models import User
from apps.audit.models import JournalActivite
from apps.finances.models import Financement
from apps.reforestation.models import SiteReboisement

TAUX_CHANGE = {'XAF': Decimal('1'), 'EUR': Decimal('655.957'), 'USD': Decimal('600')}


def identifiant(texte):
    sans_accents = unicodedata.normalize('NFD', texte or '').encode('ascii', 'ignore').decode()
    return ''.join(c for c in sans_accents.lower() if c.isalnum() or c == '-')


def email_demo(prenom, nom, deja_pris):
    base = f"{identifiant(prenom)}.{identifiant(nom)}"
    email = f"{base}@reboisgabon.ga"
    rang = 2
    while email in deja_pris:
        email = f"{base}{rang}@reboisgabon.ga"
        rang += 1
    deja_pris.add(email)
    return email


def montant_plausible(devise, minimum_xaf, maximum_xaf, aleatoire):
    montant_xaf = Decimal(aleatoire.randint(minimum_xaf, maximum_xaf))
    return (montant_xaf / TAUX_CHANGE.get(devise, Decimal('1'))).quantize(Decimal('1'))


class Command(BaseCommand):
    help = "Rend les données de démonstration cohérentes : journal sans traces de tests, e-mails lisibles, statuts, dates et montants de financement plausibles."

    @transaction.atomic
    def handle(self, *args, **options):
        aleatoire = random.Random(2026)

        filtre_tests = Q()
        for motif in ('Site test interface', 'E2E', 'e2e.', 'Interdit', 'Sans site'):
            filtre_tests |= Q(objet_repr__icontains=motif)
        purges, _ = JournalActivite.objects.filter(filtre_tests).delete()

        deja_pris = set(User.objects.values_list('email', flat=True).filter(Q(is_superuser=True) | ~Q(email__endswith='@reboisgabon.ga') | Q(email='demo2fa@reboisgabon.ga')))
        emails = 0
        comptes_fixes = {'demo2fa@reboisgabon.ga', 'demo.2fa@reboisgabon.ga'}
        for utilisateur in User.objects.filter(is_superuser=False, email__endswith='@reboisgabon.ga').exclude(email__in=comptes_fixes).order_by('date_joined', 'last_name'):
            nouvel_email = email_demo(utilisateur.first_name, utilisateur.last_name, deja_pris)
            if nouvel_email != utilisateur.email:
                utilisateur.email = nouvel_email
                utilisateur.save(update_fields=['email'])
                emails += 1

        statuts = 0
        for site in SiteReboisement.objects.all():
            a_des_campagnes = site.campagnes.exists()
            if site.statut == SiteReboisement.Statut.PLANIFIE and a_des_campagnes:
                site.statut = SiteReboisement.Statut.EN_COURS
                site.save(update_fields=['statut'])
                statuts += 1
            elif not a_des_campagnes and site.statut != SiteReboisement.Statut.PLANIFIE:
                site.statut = SiteReboisement.Statut.PLANIFIE
                site.save(update_fields=['statut'])
                statuts += 1

        financements = 0
        for financement in Financement.objects.select_related('site', 'campagne'):
            if financement.campagne_id:
                financement.date_financement = financement.campagne.date_plantation - timedelta(days=aleatoire.randint(15, 75))
                financement.montant = montant_plausible(financement.devise, 800_000, 12_000_000, aleatoire)
            else:
                premiere = financement.site.campagnes.aggregate(d=Min('date_plantation'))['d'] if financement.site_id else None
                if premiere:
                    financement.date_financement = premiere - timedelta(days=aleatoire.randint(30, 120))
                financement.montant = montant_plausible(financement.devise, 15_000_000, 120_000_000, aleatoire)
            financement.save(update_fields=['date_financement', 'montant'])
            financements += 1

        self.stdout.write(self.style.SUCCESS(
            f"Journal : {purges} traces de tests retirées. E-mails : {emails} normalisés. "
            f"Statuts : {statuts} corrigés. Financements : {financements} redatés et remis à l'échelle."
        ))
