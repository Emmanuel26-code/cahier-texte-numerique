from django.conf import settings
from django.db import models


class AnneeScolaire(models.Model):
    libelle = models.CharField(max_length=20, unique=True)  # ex. 2026-2027
    date_debut = models.DateField()
    date_fin = models.DateField()

    class Meta:
        verbose_name = "année scolaire"
        verbose_name_plural = "années scolaires"
        ordering = ["-date_debut"]

    def __str__(self):
        return self.libelle


class Classe(models.Model):
    nom = models.CharField(max_length=50)
    annee = models.ForeignKey(AnneeScolaire, on_delete=models.PROTECT, related_name="classes")
    eleves = models.ManyToManyField(
        settings.AUTH_USER_MODEL, through="Inscription",
        related_name="classes_suivies", blank=True,
    )

    class Meta:
        constraints = [models.UniqueConstraint(fields=["nom", "annee"], name="classe_unique_par_annee")]
        ordering = ["annee", "nom"]

    def __str__(self):
        return f"{self.nom} ({self.annee})"


class Matiere(models.Model):
    nom = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name = "matière"
        ordering = ["nom"]

    def __str__(self):
        return self.nom


class Inscription(models.Model):
    """Un élève appartient à une classe (donc à une année)."""
    eleve = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        limit_choices_to={"role": "eleve"},
    )
    classe = models.ForeignKey(Classe, on_delete=models.CASCADE)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["eleve", "classe"], name="inscription_unique")]

    def __str__(self):
        return f"{self.eleve} → {self.classe}"


class Affectation(models.Model):
    """Un professeur enseigne une matière dans une classe."""
    professeur = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="affectations", limit_choices_to={"role": "professeur"},
    )
    classe = models.ForeignKey(Classe, on_delete=models.PROTECT, related_name="affectations")
    matiere = models.ForeignKey(Matiere, on_delete=models.PROTECT, related_name="affectations")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["professeur", "classe", "matiere"], name="affectation_unique")
        ]

    def __str__(self):
        return f"{self.professeur} – {self.matiere} – {self.classe}"
