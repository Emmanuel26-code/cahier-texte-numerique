"""Déclencheurs : quand notifier ? (tâche 50)

- nouveau travail à faire : une séance est créée avec un travail, ou un travail est ajouté
  à une séance qui n'en avait pas (une simple modification ne renvoie PAS de notification) ;
- nouveau plan de cours : un plan PASSE à « validé » (jamais pour un brouillon ou un rejet,
  cohérent avec le tableau de bord qui ne montre que les plans validés).

Ce fichier est le seul à connaître les modèles Seance / Plan : à adapter si leurs noms diffèrent.
Remarque : un `bulk_create` de séances ne déclenche pas ces signaux.
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.academique.models import Affectation
from apps.cahier.models import Seance
from apps.plans.models import Plan

from .models import Notification
from .services import extrait, notifier_eleves_de_la_classe


def _affectation(instance):
    return Affectation.objects.select_related("matiere").get(pk=instance.affectation_id)


@receiver(pre_save, sender=Seance)
def memoriser_ancien_travail(sender, instance, **kwargs):
    ancien = ""
    if instance.pk:
        ancien = Seance.objects.filter(pk=instance.pk).values_list("travail_a_faire", flat=True).first() or ""
    instance._ancien_travail = ancien


@receiver(post_save, sender=Seance)
def notifier_nouveau_travail(sender, instance, **kwargs):
    if not instance.travail_a_faire.strip() or instance._ancien_travail.strip():
        return
    aff = _affectation(instance)
    message = f"Nouveau travail à faire en {aff.matiere.nom} : {extrait(instance.travail_a_faire)}"
    notifier_eleves_de_la_classe(aff.classe_id, Notification.Type.TRAVAIL, message)


@receiver(pre_save, sender=Plan)
def memoriser_ancien_statut(sender, instance, **kwargs):
    ancien = None
    if instance.pk:
        ancien = Plan.objects.filter(pk=instance.pk).values_list("statut", flat=True).first()
    instance._ancien_statut = ancien


@receiver(post_save, sender=Plan)
def notifier_nouveau_plan(sender, instance, **kwargs):
    if instance.statut != Plan.Statut.VALIDE or instance._ancien_statut == Plan.Statut.VALIDE:
        return
    aff = _affectation(instance)
    message = f"Nouveau plan de cours en {aff.matiere.nom} : {extrait(instance.titre)}"
    notifier_eleves_de_la_classe(aff.classe_id, Notification.Type.PLAN, message)
