from django.urls import path
from .views import (
    ExportRapportOverviewPDFView, ExportRapportFinancierPDFView,
    ExportSitesExcelView, ExportCampagnesExcelView, ExportFinancementsExcelView,
)

urlpatterns = [
    path('rapport-synthese/pdf/', ExportRapportOverviewPDFView.as_view(), name='export-synthese-pdf'),
    path('rapport-financier/pdf/', ExportRapportFinancierPDFView.as_view(), name='export-financier-pdf'),
    path('sites/excel/', ExportSitesExcelView.as_view(), name='export-sites-excel'),
    path('campagnes/excel/', ExportCampagnesExcelView.as_view(), name='export-campagnes-excel'),
    path('financements/excel/', ExportFinancementsExcelView.as_view(), name='export-financements-excel'),
]