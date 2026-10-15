from django import forms

from apps.academique.models import Affectation

from .models import Document


class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ("affectation", "fichier", "chapitre")

    def __init__(self, *args, professeur, **kwargs):
        super().__init__(*args, **kwargs)
        # Un professeur ne peut rattacher un document qu'à ses propres affectations.
        self.fields["affectation"].queryset = Affectation.objects.filter(
            professeur=professeur
        ).select_related("classe", "matiere")