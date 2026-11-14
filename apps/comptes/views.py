import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import views as auth_views
from django.core.cache import cache
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy

from apps.academique.models import Classe
from .forms import (
    ConnexionForm,
    DemandeReinitialisationForm,
    GestionUtilisateurForm,
    InscriptionForm,
    NouveauMotDePasseForm,
)
from .models import Utilisateur
from .permissions import role_requis

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


def inscription(request):
    if request.user.is_authenticated:
        return redirect("tableau_de_bord:accueil")

    if request.method == "POST":
        form = InscriptionForm(request.POST)
        if form.is_valid():
            utilisateur = form.save() 
            login(request, utilisateur)  
            return redirect("tableau_de_bord:accueil")
    else:
        form = InscriptionForm()

    return render(request, "comptes/inscription.html", {"form": form})

# --- Connexion avec « Rester connecté » --------------------------------------------------

class Connexion(auth_views.LoginView):
    template_name = "comptes/connexion.html"
    authentication_form = ConnexionForm
    redirect_authenticated_user = True

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
