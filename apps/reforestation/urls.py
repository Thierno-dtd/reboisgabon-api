from rest_framework.routers import DefaultRouter
from .views import (
    EssenceViewSet, SiteReboisementViewSet,
    CampagnePlantationViewSet, SuiviCroissanceViewSet
)

router = DefaultRouter()
router.register('essences', EssenceViewSet, basename='essence')
router.register('sites', SiteReboisementViewSet, basename='site')
router.register('campagnes', CampagnePlantationViewSet, basename='campagne')
router.register('suivis', SuiviCroissanceViewSet, basename='suivi')

urlpatterns = router.urls