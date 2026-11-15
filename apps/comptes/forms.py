from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm, SetPasswordForm, UserCreationForm
from django.contrib.auth.password_validation import validate_password

from apps.academique.models import Classe, Inscription

from .models import Utilisateur


class InscriptionForm(UserCreationForm):
    """Formulaire d'inscription : l'e-mail sert d'identifiant, le mot de passe est haché."""

    class Meta(UserCreationForm.Meta):
        model = Utilisateur
        fields = ("first_name", "last_name", "email", "role")
        labels = {"first_name": "Prénom", "last_name": "Nom", "email": "Adresse e-mail", "role": "Je suis"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["role"].choices = [
            (Utilisateur.Role.ELEVE, "Élève"),
            (Utilisateur.Role.PROFESSEUR, "Professeur"),
        ]
        self.fields["role"].widget = forms.RadioSelect(choices=self.fields["role"].choices)
        self.fields["first_name"].required = True
        self.fields["last_name"].required = True
        self.fields["password1"].help_text = "8 caractères minimum."
        self.fields["password2"].label = "Confirmer le mot de passe"
        self.fields["password2"].help_text = ""
        autocompletes = {"first_name": "given-name", "last_name": "family-name", "email": "email",
                         "password1": "new-password", "password2": "new-password"}
        for nom, valeur in autocompletes.items():
            self.fields[nom].widget.attrs["autocomplete"] = valeur
        self.fields["email"].widget.attrs.update({"inputmode": "email", "autocapitalize": "none", "spellcheck": "false"})

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if Utilisateur.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Un compte existe déjà avec cette adresse e-mail.")
        return email


class ConnexionForm(AuthenticationForm):
    """Connexion avec l'adresse e-mail."""

    error_messages = {
        "invalid_login": "Adresse e-mail ou mot de passe incorrect.",
        "inactive": "Ce compte est désactivé. Contactez l'administration.",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Adresse e-mail"
        self.fields["username"].widget = forms.EmailInput(attrs={
            "autocomplete": "email", "inputmode": "email",
            "autocapitalize": "none", "spellcheck": "false",
        })
        self.fields["password"].widget.attrs["autocomplete"] = "current-password"


    rester_connecte = forms.BooleanField(label="Rester connecté", required=False, initial=True)


class DemandeReinitialisationForm(PasswordResetForm):
    """Demande de lien de réinitialisation (on ne révèle jamais si l'adresse existe)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].label = "Adresse e-mail du compte"
        self.fields["email"].widget.attrs.update({
            "autocomplete": "email", "inputmode": "email", "autocapitalize": "none", "spellcheck": "false",
        })


class NouveauMotDePasseForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["new_password1"].label = "Nouveau mot de passe"
        self.fields["new_password1"].help_text = "8 caractères minimum."
        self.fields["new_password1"].widget.attrs["autocomplete"] = "new-password"
        self.fields["new_password2"].label = "Confirmer le nouveau mot de passe"
        self.fields["new_password2"].help_text = ""
        self.fields["new_password2"].widget.attrs["autocomplete"] = "new-password"


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
            "email", "first_name", "last_name", "role",
            "is_active", "classes",
        )
        labels = {
            "email": "Adresse e-mail (identifiant de connexion)",
            "first_name": "Prénom",
            "last_name": "Nom",
            "role": "Rôle",
            "is_active": "Compte actif",
        }
        help_texts = {"is_active": "Décoché : la connexion est bloquée et le compte est supprimé au bout de 30 jours."}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].widget.attrs.update({"autocomplete": "off", "inputmode": "email", "autocapitalize": "none"})
        self.fields["mot_de_passe"].widget.attrs["autocomplete"] = "new-password"
        if self.instance.pk:
            self.fields["mot_de_passe"].help_text = "Laissez vide pour conserver le mot de passe actuel."
        if self.instance.pk and self.instance.est_eleve:
            self.fields["classes"].initial = self.instance.classes_suivies.all()

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        doublons = Utilisateur.objects.filter(email__iexact=email)
        if self.instance.pk:
            doublons = doublons.exclude(pk=self.instance.pk)
        if doublons.exists():
            raise forms.ValidationError("Un compte existe déjà avec cette adresse e-mail.")
        return email

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