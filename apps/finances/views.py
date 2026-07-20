from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, filters, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Partenaire, Financement, BudgetCampagne
from .serializers import PartenaireSerializer, FinancementSerializer, BudgetCampagneSerializer
from .filters import PartenaireFilter, FinancementFilter


class PartenaireViewSet(viewsets.ModelViewSet):
    queryset = Partenaire.objects.all()
    serializer_class = PartenaireSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = PartenaireFilter
    search_fields = ['nom', 'pays', 'contact_email']
    ordering_fields = ['nom', 'created_at']
    ordering = ['nom']

    def destroy(self, request, *args, **kwargs):
        if request.query_params.get('confirm') != 'true':
            return Response(
                {'detail': "Confirmation requise. Ajoutez ?confirm=true à la requête."},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().destroy(request, *args, **kwargs)


class FinancementViewSet(viewsets.ModelViewSet):
    queryset = Financement.objects.select_related('partenaire', 'campagne', 'site').all()
    serializer_class = FinancementSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = FinancementFilter
    search_fields = ['reference', 'description', 'partenaire__nom']
    ordering_fields = ['date_financement', 'montant']
    ordering = ['-date_financement']

    def get_serializer_context(self):
        return {'request': self.request}

    def destroy(self, request, *args, **kwargs):
        if request.query_params.get('confirm') != 'true':
            return Response(
                {'detail': "Confirmation requise. Ajoutez ?confirm=true à la requête."},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().destroy(request, *args, **kwargs)


class BudgetCampagneViewSet(viewsets.ModelViewSet):
    """
    Pas de création directe : le budget se crée automatiquement à la volée
    (get_or_create) lors du premier PATCH pour une campagne donnée.
    """
    queryset = BudgetCampagne.objects.select_related('campagne').all()
    serializer_class = BudgetCampagneSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['campagne']

    def create(self, request, *args, **kwargs):
        campagne_id = request.data.get('campagne')
        budget, _ = BudgetCampagne.objects.get_or_create(campagne_id=campagne_id)
        serializer = self.get_serializer(budget, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)