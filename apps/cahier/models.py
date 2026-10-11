from django.conf import settings
from django.db import models


class Seance(models.Model):
    affectation = models.ForeignKey("academique.Affectation", on_delete=models.PROTECT, related_name="seances")
    date_seance = models.DateField()
    duree_minutes = models.PositiveIntegerField()
    titre = models.CharField(max_length=200)
    contenu_traite = models.TextField()
    travail_a_faire = models.TextField(blank=True)
    supprime = models.BooleanField(default=False)  # suppression logique
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    # Avancement du programme : séance <-> points du plan
    points_du_plan = models.ManyToManyField("plans.Titre", blank=True, related_name="seances")

    class Meta:
        verbose_name = "séance"
        ordering = ["-date_seance"]

    def __str__(self):
        return f"{self.titre} ({self.date_seance})"


class SeanceHistorique(models.Model):
    """État AVANT chaque modification ou suppression d'une séance."""
    class Action(models.TextChoices):
        MODIFICATION = "modification", "Modification"
        SUPPRESSION = "suppression", "Suppression"

    seance = models.ForeignKey(Seance, on_delete=models.CASCADE, related_name="historique")
    modifie_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    action = models.CharField(max_length=15, choices=Action.choices)
    anciennes_valeurs = models.JSONField()
    date_action = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "historique de séance"
        verbose_name_plural = "historiques de séances"
        ordering = ["-date_action"]
