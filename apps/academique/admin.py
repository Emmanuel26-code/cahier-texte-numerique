from django.contrib import admin

from .models import Affectation, AnneeScolaire, Classe, Inscription, Matiere

for m in (AnneeScolaire, Classe, Matiere, Inscription, Affectation):
    admin.site.register(m)
