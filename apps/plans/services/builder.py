"""Écriture en base d'un ArbrePlan : un Plan (statut « proposé ») et ses Titres."""
from django.db import transaction

from apps.plans.models import Plan, Titre

from .schema import ArbrePlan


@transaction.atomic
def creer_plan(document, arbre: ArbrePlan) -> Plan:
    """Crée le Plan et tous ses Titres, ou rien du tout si une écriture échoue.

    `ordre` est un compteur unique par plan, attribué en parcours en profondeur :
    trier par `ordre` redonne donc l'ordre de lecture du document, et l'ordre des
    frères d'un même parent est conservé.
    """
    plan = Plan.objects.create(document=document, statut=Plan.Statut.PROPOSE)
    ordre = 0

    def ecrire(noeuds, parent, niveau):
        nonlocal ordre
        for noeud in noeuds:
            ordre += 1
            # Création un par un : il faut l'identifiant du parent pour ses enfants,
            # et MySQL ne renvoie pas les identifiants avec bulk_create.
            titre = Titre.objects.create(
                plan=plan, parent=parent, niveau=niveau, ordre=ordre, libelle=noeud.libelle
            )
            ecrire(noeud.enfants, titre, niveau + 1)

    ecrire(arbre.racines, None, Titre.Niveau.PARTIE)
    return plan
