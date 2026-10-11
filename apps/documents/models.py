import mimetypes

from django.db import models

from .validators import valider_extension, valider_taille


class Document(models.Model):
    """Fichier de cours importé par un professeur (voir MCD : entité DOCUMENT)."""

    fichier = models.FileField(
        "fichier",
        upload_to="documents/%Y/%m/",
        validators=[valider_extension, valider_taille],
    )
    chapitre = models.CharField("chapitre", max_length=150, blank=True)
    nom_original = models.CharField(max_length=255, editable=False)
    type_mime = models.CharField(max_length=100, editable=False)
    taille_octets = models.PositiveIntegerField(editable=False)
    date_import = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date_import"]

    def save(self, *args, **kwargs):
        if not self.nom_original:
            self.nom_original = self.fichier.name
            self.taille_octets = self.fichier.size
            self.type_mime = (
                mimetypes.guess_type(self.fichier.name)[0] or "application/octet-stream"
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nom_original