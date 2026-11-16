from django.urls import path

from . import views

app_name = "documents"

urlpatterns = [
    path("", views.liste, name="liste"),
    path("importer/", views.importer, name="importer"),
    path("mes-cours/", views.mes_cours, name="mes_cours"),
    path("<int:document_id>/telecharger/", views.telecharger, name="telecharger"),
]