"""Sécurité des comptes.

1. Limitation des tentatives de connexion : après 5 échecs en 15 minutes pour une même
   adresse e-mail ou une même adresse IP, la connexion est bloquée 15 minutes. Cela vaut
   pour la page de connexion ET pour l'administration Django (/admin/), car le blocage est
   fait dans le « backend » d'authentification.
2. Confirmation de l'adresse e-mail à l'inscription (lien signé, valable 3 jours).
3. Validation des comptes professeurs par l'administration.
"""
import logging

from django.conf import settings
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.core import signing
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.urls import reverse

logger = logging.getLogger(__name__)

# --- 1. Tentatives de connexion -------------------------------------------------------------

MAX_ECHECS = 5
FENETRE_SECONDES = 15 * 60  # 15 minutes


def adresse_ip(request):
    """Adresse IP du visiteur. Sur Vercel, l'en-tête x-real-ip est posé par la plateforme."""
    if request is None:
        return "?"
    meta = request.META
    return (
        meta.get("HTTP_X_REAL_IP")
        or (meta.get("HTTP_X_FORWARDED_FOR") or "").split(",")[0].strip()
        or meta.get("REMOTE_ADDR")
        or "?"
    )


def _cles(request, email):
    cles = [f"connexion-ip-{adresse_ip(request)}"]
    if email:
        cles.append(f"connexion-email-{email.strip().lower()}")
    return cles


def connexion_bloquee(request, email):
    return any((cache.get(cle) or 0) >= MAX_ECHECS for cle in _cles(request, email))


def compter(cle, duree):
    """Incrémente un compteur qui expire au bout de `duree` secondes ; renvoie sa valeur."""
    cache.add(cle, 0, timeout=duree)
    try:
        return cache.incr(cle)
    except ValueError:  # la clé a expiré entre add() et incr()
        cache.set(cle, 1, timeout=duree)
        return 1


@receiver(user_login_failed)
def noter_echec(sender, credentials, request=None, **kwargs):
    email = credentials.get("username") or credentials.get("email") or ""
    for cle in _cles(request, email):
        compter(cle, FENETRE_SECONDES)


@receiver(user_logged_in)
def effacer_echecs(sender, request, user, **kwargs):
    cache.delete(f"connexion-email-{user.email.lower()}")


class BackendConnexion(ModelBackend):
    """Authentification par e-mail avec trois garde-fous en plus de Django."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        email = username or kwargs.get("email")
        if connexion_bloquee(request, email):
            raise PermissionDenied  # Django arrête alors l'authentification
        return super().authenticate(request, username=username, password=password, **kwargs)

    def user_can_authenticate(self, user):
        return (
            super().user_can_authenticate(user)
            and getattr(user, "email_verifie", True)
            and not getattr(user, "en_attente_validation", False)
        )


# --- 2. Confirmation de l'adresse e-mail ----------------------------------------------------

SEL_CONFIRMATION = "comptes.confirmation-email"
VALIDITE_CONFIRMATION = 3 * 24 * 3600  # 3 jours


def jeton_confirmation(utilisateur):
    return signing.dumps({"id": utilisateur.pk, "email": utilisateur.email}, salt=SEL_CONFIRMATION)


def lire_jeton_confirmation(jeton):
    """Renvoie (id, email) ou lève signing.BadSignature / SignatureExpired."""
    donnees = signing.loads(jeton, salt=SEL_CONFIRMATION, max_age=VALIDITE_CONFIRMATION)
    return donnees["id"], donnees["email"]


def envoi_email_possible():
    return settings.EMAIL_CONFIGURE or settings.DEBUG


def _envoyer(sujet, gabarit, destinataires, contexte):
    texte = render_to_string(f"comptes/emails/{gabarit}.txt", contexte)
    html = render_to_string(f"comptes/emails/{gabarit}.html", contexte)
    send_mail(sujet, texte, None, destinataires, html_message=html)


def envoyer_confirmation(request, utilisateur):
    lien = request.build_absolute_uri(reverse("confirmer_email", args=[jeton_confirmation(utilisateur)]))
    _envoyer(
        "Confirmez votre adresse e-mail – Cahier de texte numérique", "confirmation",
        [utilisateur.email], {"user": utilisateur, "lien": lien},
    )


def prevenir_compte_existant(request, email):
    """Quelqu'un a tenté de s'inscrire avec une adresse déjà utilisée : on prévient son titulaire."""
    if not envoi_email_possible():
        return
    lien = request.build_absolute_uri(reverse("password_reset"))
    try:
        _envoyer(
            "Tentative d’inscription avec votre adresse – Cahier de texte numérique", "compte_existant",
            [email], {"lien": lien, "connexion": request.build_absolute_uri(reverse("login"))},
        )
    except Exception:
        logger.exception("Impossible de prévenir le titulaire d'une adresse déjà inscrite")


# --- 3. Validation des comptes professeurs --------------------------------------------------

def prevenir_administration(request, professeur):
    """Prévient les administrateurs qu'un compte professeur attend leur validation."""
    from .models import Utilisateur

    destinataires = list(
        Utilisateur.objects.filter(role=Utilisateur.Role.ADMINISTRATEUR, is_active=True)
        .exclude(email="").values_list("email", flat=True)
    )
    if not destinataires:
        return
    lien = request.build_absolute_uri(f"{reverse('utilisateurs')}?modifier={professeur.pk}")
    try:
        _envoyer(
            "Nouveau compte professeur à valider – Cahier de texte numérique", "professeur_a_valider",
            destinataires, {"professeur": professeur, "lien": lien},
        )
    except Exception:
        logger.exception("Impossible de prévenir l'administration d'un compte professeur à valider")


def prevenir_professeur_valide(request, professeur):
    lien = request.build_absolute_uri(reverse("login"))
    try:
        _envoyer(
            "Votre compte professeur est validé – Cahier de texte numérique", "professeur_valide",
            [professeur.email], {"user": professeur, "lien": lien},
        )
    except Exception:
        logger.exception("Impossible de prévenir un professeur de la validation de son compte")
