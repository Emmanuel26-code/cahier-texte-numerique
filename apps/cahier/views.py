from django import forms
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, render

from apps.comptes.models import Utilisateur
from apps.comptes.permissions import role_requis

from .models import Seance, SeanceHistorique


def _seances_visibles(utilisateur):
    seances = Seance.objects.filter(supprime=False).select_related(
        "affectation__professeur",
        "affectation__classe__annee",
        "affectation__matiere",
    )
    if utilisateur.est_professeur:
        return seances.filter(affectation__professeur=utilisateur)
    if utilisateur.est_eleve:
        return seances.filter(affectation__classe__eleves=utilisateur).distinct()
    return seances


@login_required
def liste_seances(request):
    seances = _seances_visibles(request.user)
    recherche = request.GET.get("q", "").strip()
    if recherche:
        seances = seances.filter(
            Q(titre__icontains=recherche)
            | Q(contenu_traite__icontains=recherche)
            | Q(travail_a_faire__icontains=recherche)
            | Q(affectation__matiere__nom__icontains=recherche)
            | Q(affectation__classe__nom__icontains=recherche)
        )
    return render(
        request,
        "cahier/seances.html",
        {"seances": seances, "recherche": recherche},
    )


@login_required
def detail_seance(request, seance_id):
    seance = get_object_or_404(_seances_visibles(request.user), pk=seance_id)
    return render(request, "cahier/seance_detail.html", {"seance": seance})


class HistoriqueFiltreForm(forms.Form):
    seance = forms.ModelChoiceField(
        queryset=Seance.objects.none(),
        required=False,
        empty_label="Toutes les séances",
        label="Séance",
    )
    auteur = forms.ModelChoiceField(
        queryset=Utilisateur.objects.none(),
        required=False,
        empty_label="Tous les utilisateurs",
        label="Auteur",
    )
    action = forms.ChoiceField(
        required=False,
        choices=(("", "Toutes les actions"), *SeanceHistorique.Action.choices),
    )
    date_debut = forms.DateField(
        required=False, label="Date de début",
        widget=forms.DateInput(attrs={"type": "date"})
    )
    date_fin = forms.DateField(
        required=False, label="Date de fin",
        widget=forms.DateInput(attrs={"type": "date"})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["seance"].queryset = Seance.objects.select_related(
            "affectation__classe", "affectation__matiere"
        ).order_by("-date_seance")
        self.fields["seance"].label_from_instance = (
            lambda seance: f"{seance.titre} — {seance.affectation.classe.nom}"
        )
        self.fields["auteur"].queryset = Utilisateur.objects.order_by(
            "last_name", "first_name", "username"
        )


@role_requis(Utilisateur.Role.ADMINISTRATEUR)
def historique(request):
    filters = HistoriqueFiltreForm(request.GET or None)
    entrees = SeanceHistorique.objects.select_related(
        "seance__affectation__classe",
        "seance__affectation__matiere",
        "modifie_par",
    )
    if filters.is_valid():
        donnees = filters.cleaned_data
        if donnees["seance"]:
            entrees = entrees.filter(seance=donnees["seance"])
        if donnees["auteur"]:
            entrees = entrees.filter(modifie_par=donnees["auteur"])
        if donnees["action"]:
            entrees = entrees.filter(action=donnees["action"])
        if donnees["date_debut"]:
            entrees = entrees.filter(date_action__date__gte=donnees["date_debut"])
        if donnees["date_fin"]:
            entrees = entrees.filter(date_action__date__lte=donnees["date_fin"])
    elif request.GET:
        entrees = entrees.none()

    detail_id = request.GET.get("detail")
    detail = None
    if detail_id and detail_id.isdigit():
        detail = entrees.filter(pk=detail_id).first()
        if detail is None:
            get_object_or_404(SeanceHistorique, pk=detail_id)

    return render(
        request,
        "cahier/historique.html",
        {"filters": filters, "entrees": entrees, "detail": detail},
    )
