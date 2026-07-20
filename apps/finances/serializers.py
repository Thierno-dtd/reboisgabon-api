from rest_framework import serializers
from .models import Partenaire, Financement, BudgetCampagne


class PartenaireSerializer(serializers.ModelSerializer):
    montant_total_finance = serializers.SerializerMethodField()
    nombre_financements = serializers.IntegerField(source='financements.count', read_only=True)

    class Meta:
        model = Partenaire
        fields = [
            'id', 'nom', 'type_partenaire', 'pays', 'contact_nom', 'contact_email',
            'contact_telephone', 'actif', 'notes', 'montant_total_finance',
            'nombre_financements', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_montant_total_finance(self, obj):
        return obj.montant_total_finance


class FinancementSerializer(serializers.ModelSerializer):
    partenaire_nom = serializers.CharField(source='partenaire.nom', read_only=True)
    campagne_info = serializers.CharField(source='campagne.__str__', read_only=True, default=None)
    site_nom = serializers.CharField(source='site.nom', read_only=True, default=None)

    class Meta:
        model = Financement
        fields = [
            'id', 'partenaire', 'partenaire_nom', 'campagne', 'campagne_info',
            'site', 'site_nom', 'montant', 'devise', 'date_financement',
            'reference', 'description', 'enregistre_par', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def validate(self, attrs):
        campagne = attrs.get('campagne')
        site = attrs.get('site')
        if not campagne and not site:
            raise serializers.ValidationError("Précisez une campagne ou un site à financer.")
        if campagne and site:
            raise serializers.ValidationError("Choisissez soit une campagne, soit un site, pas les deux.")
        return attrs

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['enregistre_par'] = request.user
        return super().create(validated_data)


class BudgetCampagneSerializer(serializers.ModelSerializer):
    ecart_budgetaire = serializers.SerializerMethodField()
    cout_par_plant_survivant = serializers.SerializerMethodField()
    campagne_info = serializers.CharField(source='campagne.__str__', read_only=True)

    class Meta:
        model = BudgetCampagne
        fields = [
            'id', 'campagne', 'campagne_info', 'budget_alloue', 'cout_reel', 'devise',
            'ecart_budgetaire', 'cout_par_plant_survivant', 'updated_at',
        ]
        read_only_fields = ['id', 'updated_at']

    def get_ecart_budgetaire(self, obj):
        return obj.ecart_budgetaire

    def get_cout_par_plant_survivant(self, obj):
        return obj.cout_par_plant_survivant