from django.urls import path

from . import views

app_name = "cahier"

urlpatterns = [
    path("", views.liste_seances, name="liste"),
    path("seances/<int:seance_id>/", views.detail_seance, name="detail"),
    path("historique/", views.historique, name="historique"),
]
