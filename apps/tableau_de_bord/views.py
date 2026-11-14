from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from apps.comptes.models import Utilisateur
from apps.comptes.permissions import role_requis

from .services import donnees_tableau_bord_eleve


@role_requis(Utilisateur.Role.ELEVE)
def tableau_de_bord_eleve(request):
    """Tâche 49 : dernières séances, travail à faire, plans de cours de la classe."""
    return render(request, "tableau_de_bord/eleve.html", donnees_tableau_bord_eleve(request.user))


# --- Pages de remplacement (démonstration uniquement) --------------------------------
# Les vrais tableaux de bord professeur (tâche 47) et administrateur (tâche 48) sont
# réalisés par d'autres membres ; ces stubs servent aux tests d'accès par rôle (tâche 51).
@role_requis(Utilisateur.Role.PROFESSEUR)
def tableau_de_bord_professeur(request):
    return render(request, "tableau_de_bord/en_construction.html", {"titre": "Tableau de bord professeur"})


@role_requis(Utilisateur.Role.ADMINISTRATEUR)
def tableau_de_bord_administrateur(request):
    return render(request, "tableau_de_bord/en_construction.html", {"titre": "Tableau de bord administrateur"})


CIBLES = {
    Utilisateur.Role.ELEVE: "tableau_de_bord:eleve",
    Utilisateur.Role.PROFESSEUR: "tableau_de_bord:professeur",
    Utilisateur.Role.ADMINISTRATEUR: "tableau_de_bord:administrateur",
}


@login_required
def accueil(request):
    """Envoie chaque utilisateur vers le tableau de bord de son rôle."""
    return redirect(CIBLES[request.user.role])
