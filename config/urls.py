from django.contrib import admin
from django.urls import include, path
from django.shortcuts import redirect, render

# Les documents importés ne sont jamais servis par une adresse /media/ publique :
# ils passent par documents:telecharger, qui vérifie les droits.


def accueil(request):
    """Page d'accueil publique ; un utilisateur connecté va directement à son tableau de bord."""
    if request.user.is_authenticated:
        return redirect("tableau_de_bord:accueil")
    return render(request, "accueil.html")


urlpatterns = [
    path("admin/", admin.site.urls),
    path("comptes/", include("apps.comptes.urls")),
    path("gestion/", include("apps.academique.urls")),
    path("documents/", include("apps.documents.urls")),
    path("cahier/", include("apps.cahier.urls")),
    path("plans/", include("apps.plans.urls")),
    path("tableau-de-bord/", include("apps.tableau_de_bord.urls")),
    path("notifications/", include("apps.notifications.urls")),
    path("", accueil, name="accueil"),
]
