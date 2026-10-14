"""Création et lecture des notifications (tâche 50).

Les notifications ne concernent que les ÉLÈVES de la classe concernée.
"""
from apps.comptes.models import Utilisateur

from .models import Notification

LONGUEUR_EXTRAIT = 80


def extrait(texte, longueur=LONGUEUR_EXTRAIT):
    texte = " ".join(texte.split())
    return texte if len(texte) <= longueur else texte[: longueur - 1].rstrip() + "…"


def notifier_eleves_de_la_classe(classe_id, type_notification, message):
    """Crée UNE notification par élève actif de la classe, en une seule requête d'insertion."""
    ids = Utilisateur.objects.filter(
        role=Utilisateur.Role.ELEVE, classe_id=classe_id, is_active=True
    ).values_list("pk", flat=True)
    return Notification.objects.bulk_create(
        [Notification(destinataire_id=pk, type=type_notification, message=message) for pk in ids]
    )


def compter_non_lues(utilisateur):
    return Notification.objects.filter(destinataire=utilisateur, lue=False).count()
