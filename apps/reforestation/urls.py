from rest_framework.routers import DefaultRouter, path
from .views import (
    EssenceViewSet, PhotoSuiviViewSet, SiteReboisementViewSet,
    CampagnePlantationViewSet, SuiviCroissanceViewSet,
    CalendrierSuivisView, SitesGeoJSONView, SitesProximiteView
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
    path('sites-geojson/', SitesGeoJSONView.as_view(), name='sites-geojson'),
    path('sites-proximite/', SitesProximiteView.as_view(), name='sites-proximite'),
]

urlpatterns = router.urls