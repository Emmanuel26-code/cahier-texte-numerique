from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("utilisateurs/", views.utilisateurs, name="utilisateurs"),
    path("inscription/", views.inscription, name="inscription"),
    path("connexion/", views.Connexion.as_view(), name="login"),
    path("deconnexion/", auth_views.LogoutView.as_view(), name="logout"),
    # Mot de passe oublié : demande -> e-mail envoyé -> nouveau mot de passe -> terminé
    path("mot-de-passe-oublie/", views.MotDePasseOublie.as_view(), name="password_reset"),
    path("mot-de-passe-oublie/envoye/", views.MotDePasseOublieEnvoye.as_view(), name="password_reset_done"),
    path("reinitialiser/<uidb64>/<token>/", views.NouveauMotDePasse.as_view(), name="password_reset_confirm"),
    path("reinitialiser/termine/", views.MotDePasseModifie.as_view(), name="password_reset_complete"),
]
