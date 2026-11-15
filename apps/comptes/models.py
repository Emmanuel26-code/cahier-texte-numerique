import re
from datetime import timedelta

from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.utils import timezone


class UtilisateurManager(UserManager):
    """On se connecte avec son adresse e-mail ; le nom d'utilisateur est généré tout seul."""

    def get_by_natural_key(self, email):
        # Connexion insensible à la casse : « Awa@Ecole.ci » = « awa@ecole.ci »
        return self.get(email__iexact=email)

    def create_user(self, username=None, email=None, password=None, **extra_fields):
        return super().create_user(username or "", email, password, **extra_fields)

    def create_superuser(self, username=None, email=None, password=None, **extra_fields):
        return super().create_superuser(username or "", email, password, **extra_fields)

    def _create_user(self, username, email, password, **extra_fields):
        if not email:
            raise ValueError("L'adresse e-mail est obligatoire.")
        if not username:
            username = self.model.nom_utilisateur_libre(email)
        return super()._create_user(username, email, password, **extra_fields)


class Utilisateur(AbstractUser):
    """Utilisateur unique avec un rôle (voir MCD : entité UTILISATEUR).

    L'identifiant de connexion est l'adresse e-mail. Le champ `username` est conservé
    (Django l'exige et il sert d'identifiant interne) mais il est rempli automatiquement.
    """

    class Role(models.TextChoices):
        PROFESSEUR = "professeur", "Professeur"
        ELEVE = "eleve", "Élève"
        ADMINISTRATEUR = "administrateur", "Administrateur"

    email = models.EmailField("adresse e-mail", unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.ELEVE)
    # Un compte désactivé est supprimé au bout de JOURS_AVANT_SUPPRESSION jours
    # (commande « supprimer_comptes_desactives », lancée chaque jour).
    date_desactivation = models.DateTimeField("désactivé le", null=True, blank=True, editable=False)

    JOURS_AVANT_SUPPRESSION = 30

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = UtilisateurManager()

    @property
    def est_professeur(self):
        return self.role == self.Role.PROFESSEUR

    @property
    def est_eleve(self):
        return self.role == self.Role.ELEVE

    @property
    def est_administrateur(self):
        return self.role == self.Role.ADMINISTRATEUR

    @classmethod
    def nom_utilisateur_libre(cls, email):
        """Identifiant interne unique déduit de l'e-mail (« awa.kone@ecole.ci » -> « awa.kone »)."""
        base = re.sub(r"[^\w.@+-]", "", email.split("@")[0])[:140] or "utilisateur"
        nom, suffixe = base, 1
        while cls.objects.filter(username__iexact=nom).exists():
            suffixe += 1
            nom = f"{base}{suffixe}"
        return nom

    def clean(self):
        super().clean()
        self.email = self.__class__.objects.normalize_email(self.email).lower()

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip().lower()
        if not self.username and self.email:
            self.username = self.nom_utilisateur_libre(self.email)
        if self.is_superuser:
            self.role = self.Role.ADMINISTRATEUR
        # Date de désactivation : posée quand le compte est décoché, effacée s'il est réactivé
        if self.is_active:
            self.date_desactivation = None
        elif self.date_desactivation is None:
            self.date_desactivation = timezone.now()
        if kwargs.get("update_fields") is not None:
            kwargs["update_fields"] = {*kwargs["update_fields"], "date_desactivation"}
        super().save(*args, **kwargs)

    @property
    def date_suppression_prevue(self):
        if self.is_active or self.date_desactivation is None:
            return None
        return self.date_desactivation + timedelta(days=self.JOURS_AVANT_SUPPRESSION)

    def __str__(self):
        return f"{self.get_full_name() or self.email} ({self.get_role_display()})"
