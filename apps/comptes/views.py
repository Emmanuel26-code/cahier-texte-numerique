from django.contrib.auth import login
from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render

from apps.academique.models import Classe
from .forms import GestionUtilisateurForm, InscriptionForm
from .models import Utilisateur
from .permissions import role_requis


@role_requis(Utilisateur.Role.ADMINISTRATEUR)
def utilisateurs(request):
    query = request.GET.get("q", "").strip()
    role = request.GET.get("role", "")
    classe_id = request.GET.get("classe", "")
    comptes = Utilisateur.objects.annotate(
        nombre_classes=Count("classes_suivies", distinct=True)
    ).order_by("last_name", "first_name", "username")
    if query:
        comptes = comptes.filter(
            Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(username__icontains=query)
            | Q(email__icontains=query)
        )
    if role in dict(Utilisateur.Role.choices):
        comptes = comptes.filter(role=role)
    if classe_id.isdigit():
        comptes = comptes.filter(classes_suivies__id=classe_id)

    selected = None
    if request.method == "POST":
        user_id = request.POST.get("user_id")
        if user_id:
            selected = get_object_or_404(Utilisateur, pk=user_id)
        form = GestionUtilisateurForm(request.POST, instance=selected)
        if form.is_valid():
            form.save()
            messages.success(request, "Le profil utilisateur a été enregistré.")
            return redirect("utilisateurs")
    else:
        user_id = request.GET.get("modifier")
        if user_id:
            selected = get_object_or_404(Utilisateur, pk=user_id)
        elif request.GET.get("nouveau") != "1":
            selected = comptes.first()
        form = GestionUtilisateurForm(instance=selected)

    return render(
        request,
        "comptes/utilisateurs.html",
        {
            "comptes": comptes,
            "selection": selected,
            "form": form,
            "q": query,
            "role_filtre": role,
            "classe_filtre": classe_id,
            "classes": Classe.objects.select_related("annee"),
            "roles": Utilisateur.Role.choices,
            "nombre_total": Utilisateur.objects.count(),
            "inscriptions": (
                selected.inscription_set.select_related("classe__annee")
                if selected and selected.est_eleve else []
            ),
        },
    )


def inscription(request):
    if request.user.is_authenticated:
        return redirect("tableau_de_bord:accueil")

    if request.method == "POST":
        form = InscriptionForm(request.POST)
        if form.is_valid():
            utilisateur = form.save() 
            login(request, utilisateur)  
            return redirect("tableau_de_bord:accueil")
    else:
        form = InscriptionForm()

    return render(request, "comptes/inscription.html", {"form": form})