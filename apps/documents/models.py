from django.db import models


class Document(models.Model):
    """Fichier de cours importé ; classe, matière et professeur viennent de l'affectation."""
    affectation = models.ForeignKey("academique.Affectation", on_delete=models.PROTECT, related_name="documents")
    chapitre = models.CharField(max_length=150, blank=True)
    nom_original = models.CharField(max_length=255)
    fichier = models.FileField(upload_to="documents/%Y/%m/")  # chemin stocké, pas le contenu
    type_mime = models.CharField(max_length=100)
    taille_octets = models.PositiveIntegerField()
    date_import = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date_import"]

    def __str__(self):
        return self.nom_original
