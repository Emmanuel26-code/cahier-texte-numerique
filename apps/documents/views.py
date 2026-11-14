from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from apps.academique.models import Affectation
from apps.comptes.models import Utilisateur
from apps.comptes.permissions import role_requis

from .forms import DocumentForm
from .models import Document

Role = Utilisateur.Role


@role_requis(Role.PROFESSEUR, Role.ADMINISTRATEUR)
def importer(request):
    professeur = request.user if request.user.role == Role.PROFESSEUR else None
    if request.method == "POST":
        form = DocumentForm(request.POST, request.FILES, professeur=professeur)
        if form.is_valid():
            form.save()
            messages.success(request, "Document importé avec succès.")
            return redirect("documents:liste")
    else:
        form = DocumentForm(professeur=professeur)
    return render(request, "documents/importer.html", {"form": form})


@role_requis(Role.PROFESSEUR, Role.ADMINISTRATEUR)
@require_http_methods(["GET", "POST"])
def liste(request):
    documents = Document.objects.select_related(
        "affectation__professeur", "affectation__classe", "affectation__matiere"
    ).prefetch_related("plans")
    if request.user.role != Role.ADMINISTRATEUR:
        documents = documents.filter(affectation__professeur=request.user)
    query = request.GET.get("q", "").strip()
    affectation_id = request.GET.get("affectation", "")
    chapitre = request.GET.get("chapitre", "")
    if query:
        documents = documents.filter(
            Q(nom_original__icontains=query)
            | Q(chapitre__icontains=query)
            | Q(affectation__professeur__first_name__icontains=query)
            | Q(affectation__professeur__last_name__icontains=query)
        )
    if affectation_id.isdigit():
        documents = documents.filter(affectation_id=affectation_id)
    if chapitre:
        documents = documents.filter(chapitre__icontains=chapitre)

    form = None
    if request.method == "POST":
        professeur = request.user if request.user.role == Role.PROFESSEUR else None
        form = DocumentForm(request.POST, request.FILES, professeur=professeur)
        if form.is_valid():
            form.save()
            messages.success(request, "Document importé avec succès.")
            return redirect("documents:liste")
    else:
        professeur = request.user if request.user.role == Role.PROFESSEUR else None
        form = DocumentForm(professeur=professeur)

    selected = None
    selected_id = request.GET.get("document")
    if selected_id and selected_id.isdigit():
        selected = documents.filter(pk=selected_id).first()
        if selected is None:
            get_object_or_404(documents, pk=selected_id)
    if selected is None:
        selected = documents.first()

    return render(
        request,
        "documents/liste.html",
        {
            "documents": documents,
            "selection": selected,
            "form": form,
            "q": query,
            "affectation_filtre": affectation_id,
            "chapitre_filtre": chapitre,
            "affectations": Affectation.objects.select_related(
                "professeur", "classe", "matiere"
            ) if request.user.role == Role.ADMINISTRATEUR else Affectation.objects.filter(
                professeur=request.user
            ).select_related("classe", "matiere"),
        },
    )