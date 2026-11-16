import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.core import signing
from django.views.decorators.http import require_POST
from django.core.cache import cache
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy

from apps.academique.models import Classe
from .forms import (
    ConnexionForm,
    DemandeReinitialisationForm,
    GestionUtilisateurForm,
    InscriptionForm,
    NouveauMotDePasseForm,
)
from .models import Utilisateur
from .classes import affecter_classe, classes_proposees
from .permissions import role_requis
from .securite import (
    adresse_ip,
    compter,
    envoi_email_possible,
    envoyer_confirmation,
    lire_jeton_confirmation,
    prevenir_administration,
    prevenir_compte_existant,
    prevenir_professeur_valide,
)

logger = logging.getLogger(__name__)


@role_requis(Utilisateur.Role.ADMINISTRATEUR)
def utilisateurs(request):
    query = request.GET.get("q", "").strip()
    role = request.GET.get("role", "")
    classe_id = request.GET.get("classe", "")
    comptes = Utilisateur.objects.annotate(
        nombre_classes=Count("classes_suivies", distinct=True)
    ).order_by("last_name", "first_name", "email")
    if query:
        comptes = comptes.filter(
            Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(username__icontains=query)
            | Q(email__icontains=query)
        )
    if role in dict(Utilisateur.Role.choices):
        comptes = comptes.filter(role=role)
    if classe_id.isdigit():
        comptes = comptes.filter(classes_suivies__id=classe_id)

    selected = None
    if request.method == "POST":
        user_id = request.POST.get("user_id")
        if user_id:
            selected = get_object_or_404(Utilisateur, pk=user_id)
        form = GestionUtilisateurForm(request.POST, instance=selected)
        if form.is_valid():
            form.save()
            messages.success(request, "Le profil utilisateur a été enregistré.")
            return redirect("utilisateurs")
    else:
        user_id = request.GET.get("modifier")
        if user_id:
            selected = get_object_or_404(Utilisateur, pk=user_id)
        elif request.GET.get("nouveau") != "1":
            selected = comptes.first()
        form = GestionUtilisateurForm(instance=selected)

    return render(
        request,
        "comptes/utilisateurs.html",
        {
            "comptes": comptes,
            "selection": selected,
            "form": form,
            "q": query,
            "role_filtre": role,
            "classe_filtre": classe_id,
            "classes": Classe.objects.select_related("annee"),
            "roles": Utilisateur.Role.choices,
            "nombre_total": Utilisateur.objects.count(),
            "inscriptions": (
                selected.inscription_set.select_related("classe__annee")
                if selected and selected.est_eleve else []
            ),
        },
    )


LIMITE_INSCRIPTIONS_PAR_HEURE = 5


def inscription(request):
    """Inscription publique : l'adresse e-mail est confirmée par un lien, et un compte
    professeur doit en plus être validé par l'administration avant la première connexion."""
    if request.user.is_authenticated:
        return redirect("tableau_de_bord:accueil")

    form = InscriptionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if compter(f"inscription-ip-{adresse_ip(request)}", 3600) > LIMITE_INSCRIPTIONS_PAR_HEURE:
            form.add_error(None, "Trop d’inscriptions depuis cette connexion. Réessayez dans une heure.")
        elif form.adresse_deja_utilisee:
            # Même réponse qu'une inscription réussie ; le vrai titulaire est prévenu par e-mail.
            prevenir_compte_existant(request, form.cleaned_data["email"])
            request.session["inscription_email"] = form.cleaned_data["email"]
            request.session["inscription_professeur"] = form.cleaned_data.get("role") == Utilisateur.Role.PROFESSEUR
            return redirect("inscription_envoyee")
        else:
            utilisateur = form.save(commit=False)
            # Sans service d'e-mail (préversions), la confirmation est impossible : on la saute.
            utilisateur.email_verifie = not envoi_email_possible()
            utilisateur.en_attente_validation = utilisateur.role == Utilisateur.Role.PROFESSEUR
            utilisateur.save()
            if utilisateur.role == Utilisateur.Role.ELEVE:
                affecter_classe(utilisateur, form.cleaned_data["classe"])
            if not utilisateur.email_verifie:
                try:
                    envoyer_confirmation(request, utilisateur)
                except Exception:
                    logger.exception("Envoi de l'e-mail de confirmation impossible")
            elif utilisateur.en_attente_validation:
                prevenir_administration(request, utilisateur)
            request.session["inscription_email"] = utilisateur.email
            request.session["inscription_professeur"] = utilisateur.en_attente_validation
            return redirect("inscription_envoyee")

    return render(request, "comptes/inscription.html", {"form": form, "classes_existantes": classes_proposees()})


def inscription_envoyee(request):
    return render(request, "comptes/inscription_envoyee.html", {
        "email": request.session.get("inscription_email"),
        "professeur": request.session.get("inscription_professeur"),
        "confirmation": envoi_email_possible(),
    })


def confirmer_email(request, jeton):
    """Lien reçu par e-mail. Pas de connexion automatique : un antivirus de messagerie
    qui « clique » sur le lien ne doit pas ouvrir de session."""
    try:
        compte_id, email = lire_jeton_confirmation(jeton)
    except signing.SignatureExpired:
        return render(request, "comptes/email_confirme.html", {"statut": "expire"})
    except signing.BadSignature:
        return render(request, "comptes/email_confirme.html", {"statut": "invalide"})
    compte = Utilisateur.objects.filter(pk=compte_id, email__iexact=email).first()
    if compte is None:
        return render(request, "comptes/email_confirme.html", {"statut": "invalide"})
    if not compte.email_verifie:
        compte.email_verifie = True
        compte.save(update_fields=["email_verifie"])
        if compte.en_attente_validation:
            prevenir_administration(request, compte)
    statut = "attente" if compte.en_attente_validation else "ok"
    return render(request, "comptes/email_confirme.html", {"statut": statut})


@require_POST
def renvoyer_confirmation(request):
    """Renvoie le lien de confirmation (même réponse que l'adresse existe ou non)."""
    email = (request.POST.get("email") or "").strip().lower()
    if email and compter(f"renvoi-confirmation-{adresse_ip(request)}", 3600) <= 5:
        compte = Utilisateur.objects.filter(email__iexact=email, email_verifie=False, is_active=True).first()
        if compte:
            try:
                envoyer_confirmation(request, compte)
            except Exception:
                logger.exception("Renvoi de l'e-mail de confirmation impossible")
    messages.success(request, "Si cette adresse attend une confirmation, un nouveau lien vient d’être envoyé.")
    return redirect("login")


@role_requis(Utilisateur.Role.ADMINISTRATEUR)
@require_POST
def valider_professeur(request, compte_id):
    compte = get_object_or_404(Utilisateur, pk=compte_id, en_attente_validation=True)
    compte.en_attente_validation = False
    compte.save(update_fields=["en_attente_validation"])
    if compte.email_verifie:
        prevenir_professeur_valide(request, compte)
    messages.success(request, "Compte professeur validé : la personne peut maintenant se connecter.")
    return redirect(f"{reverse('utilisateurs')}?modifier={compte.pk}")


@role_requis(Utilisateur.Role.ADMINISTRATEUR)
@require_POST
def refuser_professeur(request, compte_id):
    """Refuse une demande de compte professeur : le compte, qui n'a encore aucune donnée, est supprimé."""
    compte = get_object_or_404(Utilisateur, pk=compte_id, en_attente_validation=True)
    compte.delete()
    messages.success(request, "Demande de compte professeur refusée : le compte a été supprimé.")
    return redirect("utilisateurs")

# --- Connexion avec « Rester connecté » --------------------------------------------------

class Connexion(auth_views.LoginView):
    template_name = "comptes/connexion.html"
    authentication_form = ConnexionForm
    redirect_authenticated_user = True

    def get_context_data(self, **kwargs):
        contexte = super().get_context_data(**kwargs)
        form = contexte.get("form")
        contexte["email_non_verifie"] = bool(form and form.has_error("__all__", "email_non_verifie"))
        return contexte

    def form_valid(self, form):
        reponse = super().form_valid(form)
        if form.cleaned_data.get("rester_connecte"):
            self.request.session.set_expiry(settings.SESSION_COOKIE_AGE)  # 60 jours
        else:
            self.request.session.set_expiry(0)  # jusqu'à la fermeture du navigateur
        return reponse


# --- Mot de passe oublié -------------------------------------------------------------------

LIMITE_DEMANDES_PAR_HEURE = 5


def _trop_de_demandes(request, email):
    """Limite les envois (par adresse IP et par e-mail) pour éviter les abus."""
    ip = (request.META.get("HTTP_X_FORWARDED_FOR") or request.META.get("REMOTE_ADDR") or "?").split(",")[0].strip()
    depasse = False
    for cle in (f"reinit-ip-{ip}", f"reinit-email-{email.lower()}"):
        cache.add(cle, 0, timeout=3600)
        try:
            n = cache.incr(cle)
        except ValueError:
            cache.set(cle, 1, timeout=3600)
            n = 1
        depasse = depasse or n > LIMITE_DEMANDES_PAR_HEURE
    return depasse


class MotDePasseOublie(auth_views.PasswordResetView):
    template_name = "comptes/mot_de_passe_oublie.html"
    form_class = DemandeReinitialisationForm
    email_template_name = "comptes/emails/reinitialisation.txt"
    html_email_template_name = "comptes/emails/reinitialisation.html"
    subject_template_name = "comptes/emails/reinitialisation_sujet.txt"
    success_url = reverse_lazy("password_reset_done")

    def get_context_data(self, **kwargs):
        contexte = super().get_context_data(**kwargs)
        contexte["email_configure"] = settings.EMAIL_CONFIGURE or settings.DEBUG
        return contexte

    def form_valid(self, form):
        if _trop_de_demandes(self.request, form.cleaned_data["email"]):
            form.add_error(None, "Trop de demandes en peu de temps. Réessayez dans une heure.")
            return self.form_invalid(form)
        try:
            return super().form_valid(form)
        except Exception:  # serveur d'e-mail injoignable : on le dit sans révéler de détail
            logger.exception("Envoi de l'e-mail de réinitialisation impossible")
            form.add_error(None, "L’e-mail n’a pas pu être envoyé pour le moment. Réessayez plus tard.")
            return self.form_invalid(form)


class MotDePasseOublieEnvoye(auth_views.PasswordResetDoneView):
    template_name = "comptes/mot_de_passe_envoye.html"


class NouveauMotDePasse(auth_views.PasswordResetConfirmView):
    template_name = "comptes/nouveau_mot_de_passe.html"
    form_class = NouveauMotDePasseForm
    success_url = reverse_lazy("password_reset_complete")


class MotDePasseModifie(auth_views.PasswordResetCompleteView):
    template_name = "comptes/mot_de_passe_modifie.html"
