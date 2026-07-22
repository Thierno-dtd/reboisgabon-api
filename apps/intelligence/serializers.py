from rest_framework import serializers


class PredictionSurvieSerializer(serializers.Serializer):
    essence = serializers.CharField()
    province = serializers.CharField()
    superficie_site = serializers.FloatField(min_value=0.01)
    nombre_plants = serializers.IntegerField(min_value=1)
    mois_plantation = serializers.IntegerField(min_value=1, max_value=12)
    croissance_rapide = serializers.BooleanField(default=False)