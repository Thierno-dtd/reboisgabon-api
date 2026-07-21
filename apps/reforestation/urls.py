from rest_framework.routers import DefaultRouter, path
from .views import (
    EssenceViewSet, PhotoSuiviViewSet, SiteReboisementViewSet,
    CampagnePlantationViewSet, SuiviCroissanceViewSet,
    CalendrierSuivisView
)

router = DefaultRouter()
router.register('essences', EssenceViewSet, basename='essence')
router.register('sites', SiteReboisementViewSet, basename='site')
router.register('campagnes', CampagnePlantationViewSet, basename='campagne')
router.register('suivis', SuiviCroissanceViewSet, basename='suivi')
router.register('photos-suivi', PhotoSuiviViewSet, basename='photo-suivi')

urlpatterns = router.urls
urlpatterns += [
    path('calendrier-suivis/', CalendrierSuivisView.as_view(), name='calendrier-suivis'),
]

urlpatterns = router.urls