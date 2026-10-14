import logging

from django.conf import settings
from django.core.cache import cache
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from apps.comptes.models import Utilisateur
from apps.documents.models import Document

from .models import Titre
from .services.erreurs import ConfigurationIAError, ExtractionError, GenerationPlanError, LLMError
from .services.generation import generer_plan_pour_document

logger = logging.getLogger(__name__)

_FENETRE_QUOTA_SECONDES = 3600


def _arbre_en_dict(plan):
    """Les titres du plan sous forme d'arbre imbriqué (libelle, niveau, enfants)."""
    titres = list(Titre.objects.filter(plan=plan).order_by("ordre"))
    enfants_de = {}
    for titre in titres:
        enfants_de.setdefault(titre.parent_id, []).append(titre)

    def construire(parent_id):
        return [
            {"id": t.id, "niveau": t.niveau, "libelle": t.libelle, "enfants": construire(t.id)}
            for t in enfants_de.get(parent_id, [])
        ]

    return construire(None)


def _quota_depasse(utilisateur) -> bool:
    """Compte un appel IA (payant) pour cet utilisateur ; True si la limite horaire est dépassée.

    Les tentatives échouées comptent aussi : elles peuvent déjà avoir coûté un appel.
    """
    cle = f"ia-generations-{utilisateur.id}"
    cache.add(cle, 0, timeout=_FENETRE_QUOTA_SECONDES)
    try:
        nombre = cache.incr(cle)
    except ValueError:  # la clé a expiré entre add() et incr()
        cache.set(cle, 1, timeout=_FENETRE_QUOTA_SECONDES)
        nombre = 1
    return nombre > settings.IA_MAX_GENERATIONS_PAR_HEURE


@require_POST
def generer_plan(request, document_id):
    """Génère par IA un plan « proposé » pour un document (POST /plans/documents/<id>/generer-plan/).

    Réservé au professeur propriétaire du document et aux administrateurs. Le plan
    reste en statut « proposé » : la validation par le professeur est obligatoire.
    """
    if not request.user.is_authenticated:
        return JsonResponse({"erreur": "Connexion requise."}, status=401)

    document = get_object_or_404(Document.objects.select_related("affectation"), pk=document_id)
    est_admin = request.user.role == Utilisateur.Role.ADMINISTRATEUR
    est_proprietaire = (
        request.user.role == Utilisateur.Role.PROFESSEUR
        and document.affectation.professeur_id == request.user.id
    )
    if not (est_admin or est_proprietaire):
        # 404 (et non 403) : on ne révèle pas l'existence des documents des autres.
        raise Http404("Document introuvable.")

    if _quota_depasse(request.user):
        return JsonResponse(
            {"erreur": "Trop de générations de plan en peu de temps. Réessayez dans une heure."},
            status=429,
        )

    try:
        plan = generer_plan_pour_document(document)
    except ExtractionError as exc:
        return JsonResponse({"erreur": str(exc)}, status=422)
    except ConfigurationIAError as exc:
        # Détail pour l'équipe dans les logs ; message neutre pour l'utilisateur.
        logger.error("Module IA non configuré : %s", exc)
        return JsonResponse({"erreur": "Le service d'IA n'est pas disponible pour le moment."}, status=503)
    except LLMError as exc:
        return JsonResponse({"erreur": str(exc)}, status=502)
    except GenerationPlanError as exc:  # filet de sécurité pour toute future erreur du module
        logger.exception("Erreur inattendue de génération : %s", exc)
        return JsonResponse({"erreur": "La génération du plan a échoué."}, status=500)

    return JsonResponse(
        {
            "plan_id": plan.id,
            "statut": plan.statut,
            "document_id": document.id,
            "titres": _arbre_en_dict(plan),
        },
        status=201,
    )
