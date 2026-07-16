from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import User
from .permissions import IsAdminRole
from .serializers import (
    UserListSerializer, UserCreateSerializer, UserUpdateSerializer,
    MeUpdateSerializer, ChangePasswordSerializer
)


class UserViewSet(viewsets.ModelViewSet):
    """
    Module Utilisateurs — réservé à l'administrateur.
    CRUD complet + recherche + filtres.
    """
    queryset = User.objects.all()
    permission_classes = [IsAuthenticated, IsAdminRole]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['role', 'is_active', 'two_fa_enabled']
    search_fields = ['email', 'first_name', 'last_name']
    ordering_fields = ['date_joined', 'email', 'last_name']
    ordering = ['-date_joined']

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        if self.action in ('update', 'partial_update'):
            return UserUpdateSerializer
        return UserListSerializer

    def get_serializer_context(self):
        return {'request': self.request}

    def destroy(self, request, *args, **kwargs):
        """
        Suppression avec confirmation obligatoire.
        Le client doit envoyer ?confirm=true, sinon on refuse (au lieu d'un DELETE silencieux).
        On désactive le compte plutôt que de le supprimer en dur (soft delete),
        pour préserver l'historique des campagnes/suivis liés à cet utilisateur.
        """
        if request.query_params.get('confirm') != 'true':
            return Response(
                {'detail': "Confirmation requise. Ajoutez ?confirm=true à la requête."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = self.get_object()
        if user.id == request.user.id:
            return Response(
                {'detail': "Vous ne pouvez pas supprimer votre propre compte."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.is_active = False
        user.save()
        return Response({'detail': 'Compte désactivé avec succès.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='reactivate')
    def reactivate(self, request, pk=None):
        """Réactive un compte désactivé."""
        user = self.get_object()
        user.is_active = True
        user.save()
        return Response({'detail': 'Compte réactivé.'})


class MyProfileView(viewsets.ViewSet):
    """Endpoints pour l'utilisateur courant, hors module admin."""
    permission_classes = [IsAuthenticated]

    def partial_update_me(self, request):
        serializer = MeUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def change_password(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        if not user.check_password(serializer.validated_data['old_password']):
            return Response({'detail': 'Ancien mot de passe incorrect.'},
                             status=status.HTTP_400_BAD_REQUEST)

        user.set_password(serializer.validated_data['new_password'])
        user.save()
        return Response({'detail': 'Mot de passe modifié avec succès.'})