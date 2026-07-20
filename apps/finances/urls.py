from rest_framework.routers import DefaultRouter
from .views import PartenaireViewSet, FinancementViewSet, BudgetCampagneViewSet

router = DefaultRouter()
router.register('partenaires', PartenaireViewSet, basename='partenaire')
router.register('financements', FinancementViewSet, basename='financement')
router.register('budgets-campagne', BudgetCampagneViewSet, basename='budget-campagne')

urlpatterns = router.urls