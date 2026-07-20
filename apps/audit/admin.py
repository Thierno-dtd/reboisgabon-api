from django.contrib import admin
from .models import JournalActivite


@admin.register(JournalActivite)
class JournalActiviteAdmin(admin.ModelAdmin):
    list_display = ['date_action', 'utilisateur', 'action', 'modele', 'objet_repr', 'adresse_ip']
    list_filter = ['action', 'modele', 'date_action']
    search_fields = ['objet_repr', 'utilisateur__email']
    readonly_fields = [f.name for f in JournalActivite._meta.fields]

    def has_add_permission(self, request):
        return False