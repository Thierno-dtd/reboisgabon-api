from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Notification
from .serializers import NotificationSerializer


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Chaque utilisateur ne voit que SES notifications.
    """
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(destinataire=self.request.user)

    @action(detail=False, methods=['get'])
    def non_lues(self, request):
        count = self.get_queryset().filter(lue=False).count()
        return Response({'nombre_non_lues': count})

    @action(detail=True, methods=['post'])
    def marquer_lue(self, request, pk=None):
        notif = self.get_object()
        notif.lue = True
        notif.save()
        return Response({'detail': 'Notification marquée comme lue.'})

    @action(detail=False, methods=['post'], url_path='marquer-toutes-lues')
    def marquer_toutes_lues(self, request):
        self.get_queryset().filter(lue=False).update(lue=True)
        return Response({'detail': 'Toutes les notifications ont été marquées comme lues.'})