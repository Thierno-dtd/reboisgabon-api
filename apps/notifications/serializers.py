from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            'id', 'type_notification', 'titre', 'message', 'lue',
            'lien_objet_id', 'lien_modele', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']