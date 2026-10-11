import mimetypes
import os
import uuid

from django.db import models
from django.utils import timezone
from django.utils.text import get_valid_filename

from .validators import valider_contenu, valider_extension, valider_taille


def chemin_upload(instance, nom_fichier):
    """Chemin de stockage : le fichier est renommé avec un nom aléatoire.

    Le nom choisi par l'utilisateur n'est jamais utilisé tel quel sur le disque
    (évite les caractères dangereux, les "../" et les doublons).
    """
    extension = os.path.splitext(nom_fichier)[1].lower()
    return f"documents/{timezone.now():%Y/%m}/{uuid.uuid4().hex}{extension}"


def nettoyer_nom(nom):
    """Nettoie un nom de fichier pour l'affichage : pas de chemin, pas de caractères spéciaux."""
    nom = get_valid_filename(os.path.basename(nom.replace("\\", "/")))
    base, extension = os.path.splitext(nom)
    return base[:200] + extension


class Document(models.Model):
    """Fichier de cours importé par un professeur (voir MCD : entité DOCUMENT)."""

    fichier = models.FileField(
        "fichier",
        upload_to=chemin_upload,
        validators=[valider_extension, valider_taille, valider_contenu],
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
            self.nom_original = nettoyer_nom(self.fichier.name)
            self.taille_octets = self.fichier.size
            self.type_mime = (
                mimetypes.guess_type(self.fichier.name)[0] or "application/octet-stream"
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nom_original