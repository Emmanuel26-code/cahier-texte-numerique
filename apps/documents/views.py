import os

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import models
from django.db.models import Q
from django.http import FileResponse, Http404
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from apps.academique.models import Affectation
from apps.comptes.models import Utilisateur
from apps.comptes.permissions import role_requis

from .forms import DocumentForm
from .models import Document

Role = Utilisateur.Role


@role_requis(Role.PROFESSEUR)
def importer(request):
    """Seuls les professeurs importent leurs cours ; l'administration les consulte."""
    professeur = request.user
    if request.method == "POST":
        form = DocumentForm(request.POST, request.FILES, professeur=professeur)
        if form.is_valid():
            form.save()
            messages.success(request, "Document importé avec succès.")
            return redirect("documents:liste")
    else:
        form = DocumentForm(professeur=professeur)
    return render(request, "documents/importer.html", {"form": form, "taille_max": settings.DOCUMENT_MAX_OCTETS})


@role_requis(Role.PROFESSEUR, Role.ADMINISTRATEUR)
@require_http_methods(["GET"])
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

def peut_consulter(utilisateur, document):
    """Qui peut télécharger un document ?

    - l'administrateur ;
    - le professeur de l'affectation ;
    - les élèves inscrits dans la classe de l'affectation.
    """
    if utilisateur.est_administrateur:
        return True
    if utilisateur.est_professeur:
        return document.affectation.professeur_id == utilisateur.id
    if utilisateur.est_eleve:
        return utilisateur.classes_suivies.filter(pk=document.affectation.classe_id).exists()
    return False


@login_required
def telecharger(request, document_id):
    """Envoie le fichier après contrôle des droits.

    Les fichiers ne sont jamais servis par une adresse publique /media/… :
    sans ce contrôle, toute personne ayant le lien pourrait lire un cours.
    """
    document = get_object_or_404(Document.objects.select_related("affectation"), pk=document_id)
    if not peut_consulter(request.user, document):
        # 404 (et non 403) : on ne révèle pas l'existence des documents des autres.
        raise Http404("Document introuvable.")
    try:
        fichier = document.fichier.open("rb")
    except (FileNotFoundError, OSError):
        raise Http404("Le fichier de ce document est introuvable.")
    extension = os.path.splitext(document.nom_original)[1]
    return FileResponse(
        fichier,
        as_attachment=True,
        filename=document.nom_original or f"document-{document.pk}{extension}",
        content_type=document.type_mime or "application/octet-stream",
    )



@role_requis(Role.ELEVE)
def mes_cours(request):
    """Les cours de la classe de l'élève, rangés par matière, avec les plans validés."""
    from apps.plans.models import Plan

    documents = (
        Document.objects.filter(affectation__classe__in=request.user.classes_suivies.all())
        .select_related("affectation__matiere", "affectation__professeur")
        .prefetch_related(models.Prefetch(
            "plans", queryset=Plan.objects.filter(statut=Plan.Statut.VALIDE), to_attr="plans_valides"))
        .order_by("affectation__matiere__nom", "-date_import")
        .distinct()
    )
    matieres = {}
    for document in documents:
        matieres.setdefault(document.affectation.matiere.nom, []).append(document)
    return render(request, "documents/mes_cours.html", {"matieres": matieres})
