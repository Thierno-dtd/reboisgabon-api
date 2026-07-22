from django.core.management.base import BaseCommand
from apps.intelligence.ml_service import entrainer_modele


class Command(BaseCommand):
    help = "Entraîne le modèle de prédiction du taux de survie sur les données actuelles."

    def handle(self, *args, **options):
        self.stdout.write("Entraînement du modèle en cours...")
        try:
            metriques = entrainer_modele()
        except ValueError as e:
            self.stderr.write(self.style.ERROR(str(e)))
            return

        self.stdout.write(self.style.SUCCESS(
            f"\nModèle entraîné avec succès :\n"
            f"  - Échantillons utilisés : {metriques['nombre_echantillons']}\n"
            f"  - Erreur moyenne absolue (MAE) : {metriques['mae']} points de %\n"
            f"  - Score R² : {metriques['r2_score']} (1.0 = parfait)\n"
            f"  - Importance des variables : {metriques['features_importance']}\n"
        ))