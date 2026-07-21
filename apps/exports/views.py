from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from apps.reforestation.models import SiteReboisement, CampagnePlantation
from apps.finances.models import Financement
from apps.dashboard.views import (
    DashboardOverviewView, DashboardParSiteView,
    DashboardParEssenceView, DashboardFinancierView
)
from . import pdf_service, excel_service


class ExportRapportOverviewPDFView(APIView):
    """
    Génère le PDF de synthèse générale en réutilisant la logique du dashboard
    (pas de duplication de requêtes : on appelle directement les mêmes calculs).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        overview = DashboardOverviewView()
        overview_data = overview.get(request).data

        sites_view = DashboardParSiteView()
        sites_data = sites_view.get(request).data

        essences_view = DashboardParEssenceView()
        essences_data = essences_view.get(request).data

        buffer = pdf_service.generer_rapport_overview_pdf(overview_data, sites_data, essences_data)

        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="rapport_reboisgabon_synthese.pdf"'
        return response


class ExportRapportFinancierPDFView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        financier_view = DashboardFinancierView()
        financier_data = financier_view.get(request).data

        buffer = pdf_service.generer_rapport_financier_pdf(financier_data)

        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="rapport_reboisgabon_financier.pdf"'
        return response


class ExportSitesExcelView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        sites = SiteReboisement.objects.select_related('responsable').all()
        buffer = excel_service.generer_export_sites_excel(sites)

        response = HttpResponse(
            buffer,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="sites_reboisgabon.xlsx"'
        return response


class ExportCampagnesExcelView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        campagnes = CampagnePlantation.objects.select_related(
            'site', 'essence', 'responsable', 'budget'
        ).all()
        buffer = excel_service.generer_export_campagnes_excel(campagnes)

        response = HttpResponse(
            buffer,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="campagnes_reboisgabon.xlsx"'
        return response


class ExportFinancementsExcelView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        financements = Financement.objects.select_related('partenaire', 'campagne', 'site').all()
        buffer = excel_service.generer_export_financements_excel(financements)

        response = HttpResponse(
            buffer,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="financements_reboisgabon.xlsx"'
        return response