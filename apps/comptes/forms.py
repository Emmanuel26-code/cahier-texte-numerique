from django.contrib.auth.forms import UserCreationForm

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