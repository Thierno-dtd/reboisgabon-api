from rest_framework import serializers
from .models import JournalActivite


class JournalActiviteSerializer(serializers.ModelSerializer):
    utilisateur_nom = serializers.CharField(source='utilisateur.get_full_name', read_only=True, default='Système')
    utilisateur_email = serializers.CharField(source='utilisateur.email', read_only=True, default=None)

    class Meta:
        model = JournalActivite
        fields = [
            'id', 'utilisateur', 'utilisateur_nom', 'utilisateur_email',
            'action', 'modele', 'objet_id', 'objet_repr', 'adresse_ip', 'date_action',
        ]