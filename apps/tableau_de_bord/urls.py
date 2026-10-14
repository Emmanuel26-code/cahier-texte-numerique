from django.urls import path

from . import views

app_name = "tableau_de_bord"

urlpatterns = [
    path("", views.accueil, name="accueil"),
    path("eleve/", views.tableau_de_bord_eleve, name="eleve"),
    path("professeur/", views.tableau_de_bord_professeur, name="professeur"),
    path("administrateur/", views.tableau_de_bord_administrateur, name="administrateur"),
]
