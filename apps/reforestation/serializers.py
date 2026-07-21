from rest_framework import serializers
from django.db.models import Avg
from .models import Essence, PhotoSuivi, SiteReboisement, CampagnePlantation, SuiviCroissance


class EssenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Essence
        fields = ['id', 'nom', 'nom_scientifique', 'croissance_rapide']


class SiteReboisementListSerializer(serializers.ModelSerializer):
    """Liste : version allégée avec le taux de survie moyen calculé."""

    taux_survie_moyen = serializers.SerializerMethodField()
    responsable_nom = serializers.CharField(source='responsable.get_full_name', read_only=True, default=None)
    nombre_campagnes = serializers.IntegerField(source='campagnes.count', read_only=True)

    class Meta:
        model = SiteReboisement
        fields = [
            'id', 'nom', 'localite', 'province', 'superficie_hectares',
            'statut', 'latitude', 'longitude', 'responsable', 'responsable_nom',
            'nombre_campagnes', 'taux_survie_moyen', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_taux_survie_moyen(self, obj):
        return obj.taux_survie_moyen


class SiteReboisementWriteSerializer(serializers.ModelSerializer):
    """Création / modification : champs simples uniquement."""

    class Meta:
        model = SiteReboisement
        fields = [
            'id', 'nom', 'localite', 'province', 'superficie_hectares',
            'statut', 'latitude', 'longitude', 'responsable',
        ]
        read_only_fields = ['id']

    def validate_superficie_hectares(self, value):
        if value <= 0:
            raise serializers.ValidationError("La superficie doit être supérieure à 0.")
        return value


class CampagnePlantationListSerializer(serializers.ModelSerializer):
    site_nom = serializers.CharField(source='site.nom', read_only=True)
    essence_nom = serializers.CharField(source='essence.nom', read_only=True)
    taux_survie_moyen = serializers.SerializerMethodField()

    class Meta:
        model = CampagnePlantation
        fields = [
            'id', 'site', 'site_nom', 'essence', 'essence_nom',
            'date_plantation', 'nombre_plants', 'responsable',
            'taux_survie_moyen', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_taux_survie_moyen(self, obj):
        return obj.taux_survie_moyen


class CampagnePlantationWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = CampagnePlantation
        fields = ['id', 'site', 'essence', 'date_plantation', 'nombre_plants', 'responsable']
        read_only_fields = ['id']

    def validate_nombre_plants(self, value):
        if value <= 0:
            raise serializers.ValidationError("Le nombre de plants doit être supérieur à 0.")
        return value


class SuiviCroissanceSerializer(serializers.ModelSerializer):
    campagne_info = serializers.CharField(source='campagne.__str__', read_only=True)
    site_nom = serializers.CharField(source='campagne.site.nom', read_only=True)
    essence_nom = serializers.CharField(source='campagne.essence.nom', read_only=True)

    class Meta:
        model = SuiviCroissance
        fields = [
            'id', 'campagne', 'campagne_info', 'site_nom', 'essence_nom',
            'date_controle', 'taux_survie', 'nombre_plants_vivants',
            'observations', 'controle_par', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def validate(self, attrs):
        campagne = attrs.get('campagne') or getattr(self.instance, 'campagne', None)
        date_controle = attrs.get('date_controle') or getattr(self.instance, 'date_controle', None)

        if campagne and date_controle and date_controle < campagne.date_plantation:
            raise serializers.ValidationError(
                {'date_controle': "La date de contrôle ne peut pas précéder la date de plantation."}
            )
        return attrs

class PhotoSuiviSerializer(serializers.ModelSerializer):
    prise_par_nom = serializers.CharField(source='prise_par.get_full_name', read_only=True, default=None)

    class Meta:
        model = PhotoSuivi
        fields = ['id', 'suivi', 'image', 'legende', 'prise_par', 'prise_par_nom', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate_image(self, value):
        extensions_autorisees = ('.jpg', '.jpeg', '.png', '.webp')
        if not value.name.lower().endswith(extensions_autorisees):
            raise serializers.ValidationError("Formats acceptés : JPG, JPEG, PNG, WEBP.")
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError("La taille de l'image ne doit pas dépasser 5 Mo.")
        return value

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['prise_par'] = request.user
        return super().create(validated_data)