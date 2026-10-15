"""Point d'entrée du module IA : Document -> Plan proposé."""
import logging

from django.conf import settings

from . import llm
from .builder import creer_plan
from .erreurs import ExtractionError
from .extraction import extraire_texte

logger = logging.getLogger(__name__)


def tronquer(texte: str, max_caracteres: int) -> str:
    """Limite la taille envoyée à l'IA (coût et délai), en coupant à une fin de ligne."""
    if len(texte) <= max_caracteres:
        return texte
    coupe = texte[:max_caracteres]
    derniere_ligne = coupe.rfind("\n")
    if derniere_ligne > max_caracteres * 0.8:
        coupe = coupe[:derniere_ligne]
    return coupe


def generer_plan_pour_document(document, fournisseur=None):
    """Lit le fichier du document, demande un plan à l'IA et l'enregistre (statut « proposé »).

    Lève une sous-classe de `GenerationPlanError` (message en français) en cas d'échec ;
    dans ce cas aucun Plan n'est créé. L'appel à l'IA se fait hors de toute
    transaction : seule l'écriture finale est atomique.
    """
    try:
        # Le module se protège lui-même : il ne présume pas que l'import a filtré la taille.
        if document.fichier.size > settings.IA_MAX_FILE_BYTES:
            raise ExtractionError(
                f"Ce fichier dépasse la taille maximale analysable ({settings.IA_MAX_FILE_BYTES // (1024 * 1024)} Mo)."
            )
        with document.fichier.open("rb") as fichier:
            texte = extraire_texte(fichier, document.nom_original)
    except OSError as exc:  # fichier supprimé ou illisible sur le disque
        logger.warning("Document %s : fichier inaccessible (%s)", document.pk, type(exc).__name__)
        raise ExtractionError("Le fichier de ce document est introuvable ou illisible.") from exc

    texte_envoye = tronquer(texte, settings.IA_MAX_CHARS)
    if len(texte_envoye) < len(texte):
        logger.info(
            "Document %s tronqué à %s caractères sur %s avant envoi à l'IA.",
            document.pk, len(texte_envoye), len(texte),
        )

    arbre = llm.generer_arbre(texte_envoye, fournisseur=fournisseur)
    return creer_plan(document, arbre)
