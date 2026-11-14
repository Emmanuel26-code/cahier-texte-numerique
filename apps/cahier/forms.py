from django import forms

from apps.academique.models import Affectation
from apps.plans.models import Plan, Titre

from .models import Seance


class SeanceForm(forms.ModelForm):
    """Saisie d'une séance par le professeur (ou l'administrateur)."""

    class Meta:
        model = Seance
        fields = (
            "affectation", "date_seance", "duree_minutes", "titre",
            "contenu_traite", "travail_a_faire", "points_du_plan",
        )
        labels = {
            "affectation": "Classe et matière",
            "date_seance": "Date de la séance",
            "duree_minutes": "Durée (minutes)",
            "titre": "Titre de la séance",
            "contenu_traite": "Contenu traité",
            "travail_a_faire": "Travail à faire",
            "points_du_plan": "Points du plan abordés",
        }
        help_texts = {
            "travail_a_faire": "Les élèves de la classe seront notifiés.",
            "points_du_plan": "Points des plans de cours validés pour cette classe et cette matière.",
        }
        widgets = {
            "date_seance": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "contenu_traite": forms.Textarea(attrs={"rows": 6}),
            "travail_a_faire": forms.Textarea(attrs={"rows": 3}),
            "points_du_plan": forms.SelectMultiple(attrs={"size": 8}),
        }

    def __init__(self, *args, professeur=None, **kwargs):
        super().__init__(*args, **kwargs)
        affectations = Affectation.objects.select_related("professeur", "classe__annee", "matiere")
        if professeur is not None:
            affectations = affectations.filter(professeur=professeur)
        self.fields["affectation"].queryset = affectations
        self.fields["affectation"].label_from_instance = (
            lambda a: f"{a.classe.nom} ({a.classe.annee.libelle}) · {a.matiere.nom}"
            + ("" if professeur else f" · {a.professeur.get_full_name() or a.professeur.username}")
        )
        self.fields["duree_minutes"].min_value = 1
        self.fields["duree_minutes"].widget.attrs["min"] = 1

        points = Titre.objects.filter(
            plan__statut=Plan.Statut.VALIDE,
            plan__document__affectation__in=affectations,
        ).select_related("plan__document__affectation__matiere", "plan__document__affectation__classe")
        self.fields["points_du_plan"].queryset = points
        self.fields["points_du_plan"].required = False
        self.fields["points_du_plan"].label_from_instance = (
            lambda t: f"{t.plan.document.affectation.classe.nom} · "
                      f"{t.plan.document.affectation.matiere.nom} — {'  ' * (t.niveau - 1)}{t.libelle}"
        )

    def clean_duree_minutes(self):
        duree = self.cleaned_data["duree_minutes"]
        if duree is not None and not 1 <= duree <= 600:
            raise forms.ValidationError("La durée doit être comprise entre 1 et 600 minutes.")
        return duree

    def clean(self):
        donnees = super().clean()
        affectation = donnees.get("affectation")
        points = donnees.get("points_du_plan")
        if affectation and points:
            hors_affectation = [p for p in points if p.plan.document.affectation_id != affectation.id]
            if hors_affectation:
                self.add_error(
                    "points_du_plan",
                    "Ces points appartiennent au plan d'une autre classe ou matière.",
                )
        return donnees
