"""Classe choisie par l'élève à l'inscription.

Si la classe existe déjà, l'élève y est inscrit tout de suite. Sinon le nom est
gardé (Utilisateur.classe_demandee) et l'élève est inscrit automatiquement dès que
l'administration crée une classe portant ce nom.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from apps.academique.models import Classe, Inscription


def normaliser(nom):
    """« 6e  a » et « 6E A » désignent la même classe."""
    return " ".join((nom or "").split())


def classes_proposees():
    """Noms des classes de l'année en cours (ou de la plus récente), pour les suggestions."""
    aujourd_hui = timezone.localdate()
    classes = Classe.objects.filter(annee__date_debut__lte=aujourd_hui, annee__date_fin__gte=aujourd_hui)
    if not classes.exists():
        derniere = Classe.objects.order_by("-annee__date_debut").values_list("annee_id", flat=True).first()
        classes = Classe.objects.filter(annee_id=derniere)
    return sorted({c.nom for c in classes})


def trouver_classe(nom):
    """Classe portant ce nom, de l'année en cours en priorité, sinon la plus récente."""
    nom = normaliser(nom)
    if not nom:
        return None
    aujourd_hui = timezone.localdate()
    candidates = Classe.objects.filter(nom__iexact=nom).select_related("annee")
    en_cours = candidates.filter(annee__date_debut__lte=aujourd_hui, annee__date_fin__gte=aujourd_hui).first()
    return en_cours or candidates.order_by("-annee__date_debut").first()


def affecter_classe(eleve, nom):
    """Inscrit l'élève dans sa classe si elle existe, sinon mémorise sa demande."""
    classe = trouver_classe(nom)
    if classe:
        Inscription.objects.get_or_create(eleve=eleve, classe=classe)
        eleve.classe_demandee = ""
    else:
        eleve.classe_demandee = normaliser(nom)
    eleve.save(update_fields=["classe_demandee"])
    return classe


@receiver(post_save, sender=Classe)
def inscrire_eleves_en_attente(sender, instance, **kwargs):
    """Dès qu'une classe est créée (ou renommée), on y inscrit les élèves qui l'avaient demandée."""
    from .models import Utilisateur

    eleves = Utilisateur.objects.filter(
        role=Utilisateur.Role.ELEVE, classe_demandee__iexact=normaliser(instance.nom)
    )
    for eleve in eleves:
        Inscription.objects.get_or_create(eleve=eleve, classe=instance)
    eleves.update(classe_demandee="")
