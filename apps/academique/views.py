from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods
from django.utils import timezone

from apps.comptes.models import Utilisateur
from apps.comptes.permissions import role_requis

from .forms import AffectationForm, AnneeScolaireForm, ClasseForm, MatiereForm
from .models import Affectation, AnneeScolaire, Classe, Matiere


Role = Utilisateur.Role


@role_requis(Role.ADMINISTRATEUR)
@require_http_methods(["GET", "POST"])
def affectations(request):
    selection = None
    if request.method == "POST":
        affectation_id = request.POST.get("affectation_id")
        if affectation_id:
            selection = get_object_or_404(Affectation, pk=affectation_id)
        form = AffectationForm(request.POST, instance=selection)
        if form.is_valid():
            form.save()
            messages.success(request, "L’affectation a été enregistrée.")
            return redirect("academique:affectations")
    else:
        affectation_id = request.GET.get("modifier")
        if affectation_id:
            selection = get_object_or_404(Affectation, pk=affectation_id)

    items = Affectation.objects.select_related(
        "professeur", "classe__annee", "matiere"
    ).annotate(
        nombre_documents=Count("documents", distinct=True),
        nombre_seances=Count(
            "seances", filter=Q(seances__supprime=False), distinct=True
        ),
    )
    nouvelle = request.GET.get("nouveau") == "1" and request.method == "GET"
    if selection is None and not nouvelle:
        selection = items.first()
    form = AffectationForm(request.POST or None, instance=selection)

    return render(
        request,
        "academique/affectations.html",
        {
            "affectations": items,
            "nombre_enseignants": items.values("professeur_id").distinct().count(),
            "selection": selection,
            "seances_actives": (
                selection.seances.filter(supprime=False).count() if selection else 0
            ),
            "nouvelle": nouvelle,
            "form": form,
            "documents_recents": (
                selection.documents.order_by("-date_import")[:4] if selection else []
            ),
            "seances_recentes": (
                selection.seances.filter(supprime=False).order_by("-date_seance")[:4]
                if selection else []
            ),
        },
    )


@role_requis(Role.ADMINISTRATEUR)
@require_http_methods(["GET", "POST"])
def referentiels(request):
    annees = AnneeScolaire.objects.annotate(
        nombre_classes=Count("classes", distinct=True)
    )
    today = timezone.localdate()
    for annee in annees:
        annee.est_courante = annee.date_debut <= today <= annee.date_fin
    classes = Classe.objects.select_related("annee").annotate(
        nombre_affectations=Count("affectations", distinct=True)
    )
    matieres = Matiere.objects.annotate(
        nombre_affectations=Count("affectations", distinct=True)
    )
    form_types = {
        "annee": (AnneeScolaireForm, AnneeScolaire),
        "classe": (ClasseForm, Classe),
        "matiere": (MatiereForm, Matiere),
    }
    form_type = request.GET.get("modifier", "")
    object_id = request.GET.get("id", "")
    instance = None

    if request.method == "POST":
        form_type = request.POST.get("action", "")
        if form_type not in form_types:
            messages.error(request, "Type de référentiel inconnu.")
            return redirect("academique:referentiels")
        form_class, model = form_types[form_type]
        object_id = request.POST.get("object_id", "")
        instance = get_object_or_404(model, pk=object_id) if object_id else None
        form = form_class(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, "Le référentiel a été enregistré.")
            return redirect("academique:referentiels")
    elif form_type in form_types:
        form_class, model = form_types[form_type]
        instance = get_object_or_404(model, pk=object_id) if object_id else None
        form = form_class(instance=instance)
    else:
        form_type = ""
        object_id = ""
        form = None

    return render(
        request,
        "academique/referentiels.html",
        {
            "annees": annees,
            "classes": classes,
            "matieres": matieres,
            "form_type": form_type,
            "object_id": object_id,
            "form": form,
        },
    )
