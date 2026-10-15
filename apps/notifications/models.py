from django.conf import settings
from django.db import models


class Notification(models.Model):
    """Alerte destinée à un élève (tâche 50, optionnelle)."""

    class Type(models.TextChoices):
        TRAVAIL = "travail", "Travail à faire"
        PLAN = "plan", "Plan de cours"

    destinataire = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    type = models.CharField(max_length=20, choices=Type.choices)
    message = models.CharField(max_length=255)
    creee_le = models.DateTimeField(auto_now_add=True)
    lue = models.BooleanField(default=False)

    class Meta:
        ordering = ["-creee_le", "-id"]
        indexes = [models.Index(fields=["destinataire", "lue"])]

    def __str__(self):
        return f"{self.get_type_display()} → {self.destinataire}"
