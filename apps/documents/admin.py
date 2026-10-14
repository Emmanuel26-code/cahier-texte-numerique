from django.contrib import admin

from .models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("nom_original", "chapitre", "type_mime", "taille_octets", "date_import")