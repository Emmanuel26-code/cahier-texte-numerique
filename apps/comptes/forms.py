from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.password_validation import validate_password

from apps.academique.models import Classe, Inscription

from .models import Utilisateur


class InscriptionForm(UserCreationForm):
    """Formulaire d'inscription : crée un compte avec un mot de passe haché."""

    class Meta(UserCreationForm.Meta):
        model = Utilisateur
        fields = ("username", "first_name", "last_name", "email", "role")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.fields["role"].choices = [
            (Utilisateur.Role.PROFESSEUR, "Professeur"),
            (Utilisateur.Role.ELEVE, "Élève"),
        ]
        self.fields["first_name"].required = True
        self.fields["last_name"].required = True


class GestionUtilisateurForm(forms.ModelForm):
    mot_de_passe = forms.CharField(
        label="Mot de passe",
        widget=forms.PasswordInput,
        required=False,
        help_text="Obligatoire pour un nouvel utilisateur.",
    )
    classes = forms.ModelMultipleChoiceField(
        label="Classes d’inscription",
        queryset=Classe.objects.select_related("annee"),
        required=False,
        widget=forms.SelectMultiple,
    )

    class Meta:
        model = Utilisateur
        fields = (
            "username", "first_name", "last_name", "email", "role",
            "is_active", "classes",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.est_eleve:
            self.fields["classes"].initial = self.instance.classes_suivies.all()

    def clean_mot_de_passe(self):
        password = self.cleaned_data.get("mot_de_passe")
        if not self.instance.pk and not password:
            raise forms.ValidationError("Un mot de passe est requis pour créer le compte.")
        if password:
            validate_password(password, self.instance)
        return password

    def save(self, commit=True):
        utilisateur = super().save(commit=False)
        password = self.cleaned_data.get("mot_de_passe")
        if password:
            utilisateur.set_password(password)
        if commit:
            utilisateur.save()
            self._save_m2m()
        else:
            self.save_m2m = self._save_m2m
        return utilisateur

    def _save_m2m(self):
        super()._save_m2m()
        utilisateur = self.instance
        if not utilisateur.pk:
            return
        if utilisateur.est_eleve:
            utilisateur.classes_suivies.set(self.cleaned_data.get("classes", []))
        else:
            Inscription.objects.filter(eleve=utilisateur).delete()