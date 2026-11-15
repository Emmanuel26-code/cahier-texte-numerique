"""Supprime les comptes désactivés depuis plus de 30 jours.

    python manage.py supprimer_comptes_desactives            # supprime
    python manage.py supprimer_comptes_desactives --simulation   # affiche seulement

Lancée chaque jour par GitHub Actions (.github/workflows/nettoyage.yml).

Un compte encore lié au cahier de texte (professeur ayant des affectations, auteur
d'une modification dans l'historique…) ne peut pas être effacé sans détruire l'historique
de la classe : on efface alors toutes ses données personnelles (nom, e-mail, mot de
passe, inscriptions, notifications) et il ne reste qu'une trace anonyme.
Les comptes superutilisateurs ne sont jamais supprimés automatiquement.
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models.deletion import ProtectedError
from django.utils import timezone

from apps.academique.models import Inscription
from apps.comptes.models import Utilisateur
from apps.notifications.models import Notification

DOMAINE_ANONYME = "compte-supprime.invalid"


def anonymiser(compte):
    """Efface toutes les données personnelles d'un compte qui doit rester en base."""
    Inscription.objects.filter(eleve=compte).delete()
    Notification.objects.filter(destinataire=compte).delete()
    compte.email = f"compte-{compte.pk}@{DOMAINE_ANONYME}"
    compte.username = f"compte-supprime-{compte.pk}"
    compte.first_name = "Compte"
    compte.last_name = "supprimé"
    compte.set_unusable_password()
    compte.is_active = False
    compte.is_staff = False
    compte.save()


class Command(BaseCommand):
    help = "Supprime les comptes désactivés depuis plus de 30 jours."

    def add_arguments(self, parser):
        parser.add_argument("--simulation", action="store_true", help="Affiche sans rien supprimer.")

    def handle(self, *args, simulation=False, **options):
        limite = timezone.now() - timedelta(days=Utilisateur.JOURS_AVANT_SUPPRESSION)
        comptes = Utilisateur.objects.filter(
            is_active=False, is_superuser=False, date_desactivation__lte=limite,
        ).exclude(email__endswith=f"@{DOMAINE_ANONYME}")

        supprimes = anonymises = 0
        for compte in comptes:
            if simulation:
                self.stdout.write(f"À supprimer : compte n° {compte.pk} (désactivé le {compte.date_desactivation:%d/%m/%Y})")
                continue
            try:
                with transaction.atomic():
                    compte.delete()
                supprimes += 1
            except ProtectedError:
                with transaction.atomic():
                    anonymiser(compte)
                anonymises += 1

        # On n'affiche jamais de nom ni d'e-mail : seulement des nombres (journaux GitHub).
        self.stdout.write(self.style.SUCCESS(
            f"{supprimes} compte(s) supprimé(s), {anonymises} compte(s) anonymisé(s)"
            + (" (simulation)" if simulation else "")
        ))
