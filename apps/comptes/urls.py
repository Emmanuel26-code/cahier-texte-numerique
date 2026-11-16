from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("utilisateurs/", views.utilisateurs, name="utilisateurs"),
    path("inscription/", views.inscription, name="inscription"),
    path("inscription/envoyee/", views.inscription_envoyee, name="inscription_envoyee"),
    path("confirmer/<str:jeton>/", views.confirmer_email, name="confirmer_email"),
    path("confirmer-renvoyer/", views.renvoyer_confirmation, name="renvoyer_confirmation"),
    path("utilisateurs/<int:compte_id>/valider/", views.valider_professeur, name="valider_professeur"),
    path("utilisateurs/<int:compte_id>/refuser/", views.refuser_professeur, name="refuser_professeur"),
    path("connexion/", views.Connexion.as_view(), name="login"),
    path("deconnexion/", auth_views.LogoutView.as_view(), name="logout"),
    # Mot de passe oublié : demande -> e-mail envoyé -> nouveau mot de passe -> terminé
    path("mot-de-passe-oublie/", views.MotDePasseOublie.as_view(), name="password_reset"),
    path("mot-de-passe-oublie/envoye/", views.MotDePasseOublieEnvoye.as_view(), name="password_reset_done"),
    path("reinitialiser/<uidb64>/<token>/", views.NouveauMotDePasse.as_view(), name="password_reset_confirm"),
    path("reinitialiser/termine/", views.MotDePasseModifie.as_view(), name="password_reset_complete"),
]
