from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from apps.comptes.models import Utilisateur
from apps.comptes.permissions import role_requis

from .services import (
    donnees_tableau_bord_administrateur,
    donnees_tableau_bord_eleve,
    donnees_tableau_bord_professeur,
)


@role_requis(Utilisateur.Role.ELEVE)
def tableau_de_bord_eleve(request):
    """Tâche 49 : dernières séances, travail à faire, plans de cours de la classe."""
    return render(request, "tableau_de_bord/eleve.html", donnees_tableau_bord_eleve(request.user))


@role_requis(Utilisateur.Role.PROFESSEUR)
def tableau_de_bord_professeur(request):
    """Tâche 47 : classes, séances récentes, plans IA à valider, documents."""
    return render(request, "tableau_de_bord/professeur.html", donnees_tableau_bord_professeur(request.user))


@role_requis(Utilisateur.Role.ADMINISTRATEUR)
def tableau_de_bord_administrateur(request):
    """Tâche 48 : chiffres clés de l'établissement et points d'attention."""
    return render(request, "tableau_de_bord/administrateur.html", donnees_tableau_bord_administrateur())


CIBLES = {
    Utilisateur.Role.ELEVE: "tableau_de_bord:eleve",
    Utilisateur.Role.PROFESSEUR: "tableau_de_bord:professeur",
    Utilisateur.Role.ADMINISTRATEUR: "tableau_de_bord:administrateur",
}


@login_required
def accueil(request):
    """Envoie chaque utilisateur vers le tableau de bord de son rôle."""
    return redirect(CIBLES[request.user.role])
