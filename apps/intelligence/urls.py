from django.urls import path
from .views import PredictionSurvieView, RecommandationEssenceView, ReentrainerModeleView, DetectionRisquePredictifView

urlpatterns = [
    path('predire-survie/', PredictionSurvieView.as_view(), name='predire-survie'),
    path('recommander-essence/', RecommandationEssenceView.as_view(), name='recommander-essence'),
    path('reentrainer/', ReentrainerModeleView.as_view(), name='reentrainer-modele'),
    path('detection-risque/', DetectionRisquePredictifView.as_view(), name='detection-risque-predictif'),
]