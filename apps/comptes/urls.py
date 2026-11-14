from django.contrib.auth import views as auth_views
from django.urls import path

from . import views
from .forms import ConnexionForm

urlpatterns = [
    path("utilisateurs/", views.utilisateurs, name="utilisateurs"),
    path("inscription/", views.inscription, name="inscription"),
    path(
        "connexion/",
        auth_views.LoginView.as_view(
            template_name="comptes/connexion.html",
            authentication_form=ConnexionForm,
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path("deconnexion/", auth_views.LogoutView.as_view(), name="logout"),
]