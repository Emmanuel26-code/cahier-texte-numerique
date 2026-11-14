from django import forms

from apps.academique.models import Affectation

from .models import Document


class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ("affectation", "fichier", "chapitre")

    def __init__(self, *args, professeur=None, **kwargs):
        super().__init__(*args, **kwargs)
        affectations = Affectation.objects.select_related("classe", "matiere", "professeur")
        if professeur is not None:
            affectations = affectations.filter(professeur=professeur)
        self.fields["affectation"].queryset = affectations