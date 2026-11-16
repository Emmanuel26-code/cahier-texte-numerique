"""Avancement du programme : part des points des plans validés déjà traités en séance.

Un point est « traité » quand au moins une séance (non supprimée) l'a coché.
"""
from django.db.models import Count, Q

from apps.plans.models import Plan, Titre


class Avancement:
    def __init__(self, total=0, traites=0):
        self.total = total
        self.traites = traites

    @property
    def pourcentage(self):
        return round(100 * self.traites / self.total) if self.total else 0

    def __bool__(self):
        return self.total > 0


def _titres_valides():
    return Titre.objects.filter(plan__statut=Plan.Statut.VALIDE)


def par_affectation(affectation_ids):
    """{affectation_id: Avancement} pour les plans validés de ces affectations."""
    lignes = (
        _titres_valides().filter(plan__document__affectation_id__in=list(affectation_ids))
        .values("plan__document__affectation_id")
        .annotate(
            total=Count("id", distinct=True),
            traites=Count("id", distinct=True, filter=Q(seances__supprime=False)),
        )
    )
    return {l["plan__document__affectation_id"]: Avancement(l["total"], l["traites"]) for l in lignes}


def par_plan(plan_ids):
    """{plan_id: Avancement}."""
    lignes = (
        Titre.objects.filter(plan_id__in=list(plan_ids)).values("plan_id")
        .annotate(
            total=Count("id", distinct=True),
            traites=Count("id", distinct=True, filter=Q(seances__supprime=False)),
        )
    )
    return {l["plan_id"]: Avancement(l["total"], l["traites"]) for l in lignes}


def titres_traites(plan):
    """Identifiants des points de ce plan déjà traités en séance."""
    return set(
        plan.titres.filter(seances__supprime=False).values_list("id", flat=True).distinct()
    )
