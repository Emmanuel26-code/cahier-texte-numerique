from django.urls import path

from . import views

app_name = "cahier"

urlpatterns = [
    path("", views.liste_seances, name="liste"),
    path("seances/nouvelle/", views.creer_seance, name="creer"),
    path("seances/<int:seance_id>/", views.detail_seance, name="detail"),
    path("seances/<int:seance_id>/modifier/", views.modifier_seance, name="modifier"),
    path("seances/<int:seance_id>/supprimer/", views.supprimer_seance, name="supprimer"),
    path("seances/<int:seance_id>/vu/", views.marquer_vu_seance, name="marquer_vu"),
    path("historique/", views.historique, name="historique"),
]
