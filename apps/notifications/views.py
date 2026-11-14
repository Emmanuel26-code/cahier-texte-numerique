from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.comptes.models import Utilisateur
from apps.comptes.permissions import role_requis

from .models import Notification
from .services import compter_non_lues

NB_MAX = 50


@role_requis(Utilisateur.Role.ELEVE)
def liste(request):
    notifications = Notification.objects.filter(destinataire=request.user)[:NB_MAX]
    return render(request, "notifications/liste.html", {
        "notifications": notifications,
        "nb_non_lues": compter_non_lues(request.user),
    })


@role_requis(Utilisateur.Role.ELEVE)
@require_POST
def marquer_lue(request, pk):
    # Filtrer sur le destinataire : un élève ne peut pas toucher aux notifications d'un autre (404).
    notification = get_object_or_404(Notification, pk=pk, destinataire=request.user)
    notification.lue = True
    notification.save(update_fields=["lue"])
    return redirect("notifications:liste")


@role_requis(Utilisateur.Role.ELEVE)
@require_POST
def tout_marquer_lu(request):
    Notification.objects.filter(destinataire=request.user, lue=False).update(lue=True)
    return redirect("notifications:liste")
