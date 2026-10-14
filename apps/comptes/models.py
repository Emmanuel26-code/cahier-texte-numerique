from django.contrib.auth.models import AbstractUser
from django.db import models


class Utilisateur(AbstractUser):
    """Utilisateur unique avec un rôle (voir MCD : entité UTILISATEUR)."""

    class Role(models.TextChoices):
        PROFESSEUR = "professeur", "Professeur"
        ELEVE = "eleve", "Élève"
        ADMINISTRATEUR = "administrateur", "Administrateur"

    email = models.EmailField("adresse e-mail", unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.ELEVE)

    @property
    def est_professeur(self):
        return self.role == self.Role.PROFESSEUR

    @property
    def est_eleve(self):
        return self.role == self.Role.ELEVE

    @property
    def est_administrateur(self):
        return self.role == self.Role.ADMINISTRATEUR

    def save(self, *args, **kwargs):
        if self.is_superuser:
            self.role = self.Role.ADMINISTRATEUR
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"