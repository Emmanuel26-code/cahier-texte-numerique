from django import forms

from apps.comptes.models import Utilisateur

from .models import Affectation, AnneeScolaire, Classe, Matiere


class AffectationForm(forms.ModelForm):
    class Meta:
        model = Affectation
        fields = ("professeur", "classe", "matiere")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["professeur"].queryset = Utilisateur.objects.filter(
            role=Utilisateur.Role.PROFESSEUR
        ).order_by("last_name", "first_name", "username")


class AnneeScolaireForm(forms.ModelForm):
    class Meta:
        model = AnneeScolaire
        fields = ("libelle", "date_debut", "date_fin")
        widgets = {
            "date_debut": forms.DateInput(attrs={"type": "date"}),
            "date_fin": forms.DateInput(attrs={"type": "date"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        debut = cleaned_data.get("date_debut")
        fin = cleaned_data.get("date_fin")
        if debut and fin and fin <= debut:
            self.add_error("date_fin", "La date de fin doit être postérieure à la date de début.")
        return cleaned_data


class ClasseForm(forms.ModelForm):
    class Meta:
        model = Classe
        fields = ("nom", "annee")


class MatiereForm(forms.ModelForm):
    class Meta:
        model = Matiere
        fields = ("nom",)
