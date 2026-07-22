from django.urls import path
from .views import (
    DashboardOverviewView, DashboardParSiteView, DashboardParEssenceView,
    DashboardParProvinceView, DashboardEvolutionTemporelleView,
    DashboardAlertesView, DashboardResponsablesView, DashboardFinancierView
)
from apps.reforestation.views import DashboardCarteProvinceView

urlpatterns = [
    path('overview/', DashboardOverviewView.as_view(), name='dashboard-overview'),
    path('sites/', DashboardParSiteView.as_view(), name='dashboard-sites'),
    path('essences/', DashboardParEssenceView.as_view(), name='dashboard-essences'),
    path('provinces/', DashboardParProvinceView.as_view(), name='dashboard-provinces'),
    path('evolution/', DashboardEvolutionTemporelleView.as_view(), name='dashboard-evolution'),
    path('alertes/', DashboardAlertesView.as_view(), name='dashboard-alertes'),
    path('responsables/', DashboardResponsablesView.as_view(), name='dashboard-responsables'),
]

urlpatterns += [
    path('financier/', DashboardFinancierView.as_view(), name='dashboard-financier'),
    path('carte-provinces/', DashboardCarteProvinceView.as_view(), name='dashboard-carte-provinces'),
]