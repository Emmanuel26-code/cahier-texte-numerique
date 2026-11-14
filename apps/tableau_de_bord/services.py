"""Données du tableau de bord élève (tâche 49).

Toute la lecture en base est isolée ici : si les noms de modèles ou de champs
de votre dépôt diffèrent, c'est le SEUL fichier à adapter.

Un élève est rattaché à ses classes via `Inscription` (Utilisateur.classes_suivies)
et un plan de cours à une affectation via son document (Plan.document.affectation).
"""
from apps.cahier.models import Seance
from apps.plans.models import Plan
from apps.notifications.services import compter_non_lues

NB_ELEMENTS = 5
NB_PLANS = 3


def donnees_tableau_bord_eleve(eleve):
    """Retourne ce que voit un élève : ses dernières séances, son travail à faire
    et les plans de cours VALIDÉS de ses classes (jamais les propositions ni les rejets)."""
    classes = list(eleve.classes_suivies.select_related("annee"))
    if not classes:
        return {"sans_classe": True, "classes": [], "seances": [], "travaux": [], "plans": [],
                "nb_non_lues": compter_non_lues(eleve)}

    ids_classes = [c.pk for c in classes]
    seances_classe = (
        Seance.objects.filter(affectation__classe_id__in=ids_classes, supprime=False)
        .select_related("affectation__matiere")
        .order_by("-date_seance", "-id")
    )
    plans = (
        Plan.objects.filter(document__affectation__classe_id__in=ids_classes, statut=Plan.Statut.VALIDE)
        .select_related("document__affectation__matiere")
        .order_by("-date_generation")
    )
    return {
        "sans_classe": False,
        "classes": classes,
        "seances": list(seances_classe[:NB_ELEMENTS]),
        "travaux": list(seances_classe.exclude(travail_a_faire="")[:NB_ELEMENTS]),
        "plans": list(plans[:NB_PLANS]),
        "nb_non_lues": compter_non_lues(eleve),
    }
