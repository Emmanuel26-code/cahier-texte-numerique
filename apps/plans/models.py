from django.db import models


class Plan(models.Model):
    class Statut(models.TextChoices):
        PROPOSE = "propose", "Proposé par l'IA"
        VALIDE = "valide", "Validé"
        REJETE = "rejete", "Rejeté"

    document = models.ForeignKey("documents.Document", on_delete=models.CASCADE, related_name="plans")
    statut = models.CharField(max_length=10, choices=Statut.choices, default=Statut.PROPOSE)
    date_generation = models.DateTimeField(auto_now_add=True)
    date_validation = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Plan #{self.pk} ({self.get_statut_display()})"


class Titre(models.Model):
    """Nœud du plan : Partie > Chapitre > Titre > Sous-titre (auto-référence)."""
    class Niveau(models.IntegerChoices):
        PARTIE = 1, "Partie"
        CHAPITRE = 2, "Chapitre"
        TITRE = 3, "Titre"
        SOUS_TITRE = 4, "Sous-titre"

    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name="titres")
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE, related_name="enfants")
    niveau = models.PositiveSmallIntegerField(choices=Niveau.choices)
    ordre = models.PositiveIntegerField()
    libelle = models.CharField(max_length=255)

    class Meta:
        ordering = ["plan", "ordre"]

    def __str__(self):
        return self.libelle
