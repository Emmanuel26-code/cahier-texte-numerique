"""Données du tableau de bord élève (tâche 49).

Toute la lecture en base est isolée ici : si les noms de modèles ou de champs
de votre dépôt diffèrent, c'est le SEUL fichier à adapter.

Un élève est rattaché à ses classes via `Inscription` (Utilisateur.classes_suivies)
et un plan de cours à une affectation via son document (Plan.document.affectation).
"""
from apps.cahier.models import Seance
from apps.plans.models import Plan
from apps.plans.services.avancement import par_affectation, par_plan
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
        "plans": _avec_avancement(list(plans[:NB_PLANS])),
        "nb_non_lues": compter_non_lues(eleve),
    }


def donnees_tableau_bord_professeur(professeur):
    """Ce que voit un professeur : ses classes, ses dernières séances, les plans IA
    en attente de validation et ses documents récents."""
    from django.db.models import Count, Q
    from django.utils import timezone

    from apps.academique.models import Affectation
    from apps.documents.models import Document

    aujourd_hui = timezone.localdate()
    debut_mois = aujourd_hui.replace(day=1)
    affectations = list(
        Affectation.objects.filter(professeur=professeur)
        .select_related("classe__annee", "matiere")
        .annotate(nb_seances=Count("seances", filter=Q(seances__supprime=False)))
        .order_by("classe__nom", "matiere__nom")
    )
    seances = Seance.objects.filter(affectation__professeur=professeur, supprime=False)
    avancements = par_affectation(a.pk for a in affectations)
    for a in affectations:
        a.avancement = avancements.get(a.pk)
    return {
        "affectations": affectations,
        "seances_recentes": list(
            seances.select_related("affectation__classe", "affectation__matiere")
            .order_by("-date_seance", "-id")[:NB_ELEMENTS]
        ),
        "nb_seances_mois": seances.filter(date_seance__gte=debut_mois).count(),
        "plans_a_valider": list(
            Plan.objects.filter(document__affectation__professeur=professeur, statut=Plan.Statut.PROPOSE)
            .select_related("document__affectation__classe", "document__affectation__matiere")
            .order_by("-date_generation")[:NB_ELEMENTS]
        ),
        "documents_recents": list(
            Document.objects.filter(affectation__professeur=professeur)
            .select_related("affectation__classe", "affectation__matiere")[:NB_ELEMENTS]
        ),
    }


def donnees_tableau_bord_administrateur():
    """Vue d'ensemble de l'établissement pour l'administration."""
    from django.db.models import Count, Q

    from apps.academique.models import Affectation, Classe
    from apps.cahier.models import SeanceHistorique
    from apps.comptes.models import Utilisateur
    from apps.documents.models import Document

    roles = dict(
        Utilisateur.objects.filter(is_active=True).values_list("role").annotate(n=Count("id"))
    )
    plans = dict(Plan.objects.values_list("statut").annotate(n=Count("id")))
    return {
        "nb_professeurs": roles.get(Utilisateur.Role.PROFESSEUR, 0),
        "nb_eleves": roles.get(Utilisateur.Role.ELEVE, 0),
        "nb_classes": Classe.objects.count(),
        "nb_affectations": Affectation.objects.count(),
        "nb_seances": Seance.objects.filter(supprime=False).count(),
        "nb_documents": Document.objects.count(),
        "nb_plans_valides": plans.get(Plan.Statut.VALIDE, 0),
        "nb_plans_en_attente": plans.get(Plan.Statut.PROPOSE, 0),
        "nb_professeurs_a_valider": Utilisateur.objects.filter(
            role=Utilisateur.Role.PROFESSEUR, en_attente_validation=True, email_verifie=True).count(),
        "nb_seances_a_viser": Seance.objects.filter(supprime=False, vu_le__isnull=True).count(),
        "affectations_sans_seance": list(
            Affectation.objects.annotate(n=Count("seances", filter=Q(seances__supprime=False)))
            .filter(n=0)
            .select_related("professeur", "classe", "matiere")[:NB_ELEMENTS]
        ),
        "eleves_sans_classe": Utilisateur.objects.filter(
            role=Utilisateur.Role.ELEVE, is_active=True, classes_suivies__isnull=True
        ).count(),
        "dernieres_modifications": list(
            SeanceHistorique.objects.select_related(
                "seance__affectation__classe", "seance__affectation__matiere", "modifie_par"
            )[:NB_ELEMENTS]
        ),
    }


def _avec_avancement(plans):
    avancements = par_plan(p.pk for p in plans)
    for plan in plans:
        plan.avancement = avancements.get(plan.pk)
    return plans
