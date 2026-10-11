from django.contrib import admin

from .models import Seance, SeanceHistorique

admin.site.register(Seance)
admin.site.register(SeanceHistorique)
