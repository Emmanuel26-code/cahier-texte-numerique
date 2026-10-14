"""Données du tableau de bord élève (tâche 49).

Toute la lecture en base est isolée ici : si les noms de modèles ou de champs
de votre dépôt diffèrent, c'est le SEUL fichier à adapter.
"""
from apps.academique.models import Plan, Seance
from apps.notifications.services import compter_non_lues

NB_ELEMENTS = 5
NB_PLANS = 3


def donnees_tableau_bord_eleve(eleve):
    """Retourne ce que voit un élève : ses dernières séances, son travail à faire
    et les plans de cours VALIDÉS de sa classe (jamais les brouillons)."""
    if eleve.classe_id is None:
        return {"sans_classe": True, "seances": [], "travaux": [], "plans": [],
                "nb_non_lues": compter_non_lues(eleve)}

    seances_classe = (
        Seance.objects.filter(affectation__classe_id=eleve.classe_id)
        .select_related("affectation__matiere")
        .order_by("-date", "-id")
    )
    plans = (
        Plan.objects.filter(affectation__classe_id=eleve.classe_id, statut=Plan.Statut.VALIDE)
        .select_related("affectation__matiere")
        .order_by("-date_generation")
    )
    return {
        "sans_classe": False,
        "seances": list(seances_classe[:NB_ELEMENTS]),
        "travaux": list(seances_classe.exclude(travail_a_faire="")[:NB_ELEMENTS]),
        "plans": list(plans[:NB_PLANS]),
        "nb_non_lues": compter_non_lues(eleve),
    }
