"""Validation et normalisation de la réponse JSON de l'IA.

La réponse d'un LLM n'est jamais fiable : on ne l'écrit en base qu'après l'avoir
vérifiée et nettoyée ici.

Format attendu (récursif) :

    {
      "titre_cours": "Introduction aux réseaux",
      "plan": [
        {"libelle": "Chapitre 1", "enfants": [{"libelle": "1.1 ...", "enfants": []}]}
      ]
    }

Pour rester compatible avec le premier prototype, les clés `titre` (au lieu de
`libelle`) et `sous_titres` (liste de textes simples) sont aussi acceptées.

Le niveau d'un nœud est déduit de sa profondeur (1 = Partie ... 4 = Sous-titre) et
non de la valeur donnée par l'IA : c'est ce qui garantit que `niveau` reste
cohérent avec le `parent` enregistré en base.
"""
import json
import re
from dataclasses import dataclass, field

from .erreurs import LLMError

NIVEAU_MAX = 4  # Partie > Chapitre > Titre > Sous-titre (voir plans.models.Titre)
LIBELLE_MAX = 255  # longueur de Titre.libelle
NOEUDS_MAX = 500  # garde-fou contre une réponse démesurée


@dataclass
class Noeud:
    libelle: str
    enfants: list["Noeud"] = field(default_factory=list)


@dataclass
class ArbrePlan:
    titre_cours: str
    racines: list[Noeud]

    def nombre_noeuds(self) -> int:
        def compter(noeuds):
            return sum(1 + compter(n.enfants) for n in noeuds)
        return compter(self.racines)


_CLOTURE_MARKDOWN = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


def parser_json(texte: str) -> dict:
    """Transforme la réponse brute de l'IA en dictionnaire."""
    if not texte or not texte.strip():
        raise LLMError("L'IA a renvoyé une réponse vide.")
    nettoye = _CLOTURE_MARKDOWN.sub("", texte.strip())
    try:
        donnees = json.loads(nettoye)
    except (json.JSONDecodeError, RecursionError) as exc:  # RecursionError : JSON imbriqué à l'excès
        raise LLMError("L'IA a renvoyé une réponse qui n'est pas un JSON valide.") from exc
    if not isinstance(donnees, dict):
        raise LLMError("L'IA a renvoyé un JSON de forme inattendue.")
    return donnees


def _nettoyer_libelle(valeur) -> str:
    if not isinstance(valeur, str):
        return ""
    return re.sub(r"\s+", " ", valeur).strip()[:LIBELLE_MAX]


def _construire_noeud(brut, profondeur: int, compteur: list[int]):
    """Retourne un Noeud, ou None si l'entrée est inutilisable."""
    if isinstance(brut, str):  # ancien format : sous-titre sous forme de simple texte
        brut = {"libelle": brut}
    if not isinstance(brut, dict):
        return None

    libelle = _nettoyer_libelle(brut.get("libelle", brut.get("titre")))
    if not libelle:
        return None

    compteur[0] += 1
    if compteur[0] > NOEUDS_MAX:
        raise LLMError("Le plan renvoyé par l'IA est démesuré ; génération annulée.")

    noeud = Noeud(libelle=libelle)
    if profondeur >= NIVEAU_MAX:
        return noeud  # niveau le plus fin : les éventuels descendants sont ignorés

    enfants_bruts = brut.get("enfants", brut.get("sous_titres")) or []
    if not isinstance(enfants_bruts, list):
        enfants_bruts = []
    for enfant_brut in enfants_bruts:
        enfant = _construire_noeud(enfant_brut, profondeur + 1, compteur)
        if enfant is not None:
            noeud.enfants.append(enfant)
    return noeud


def valider_arbre(donnees: dict) -> ArbrePlan:
    """Valide le dictionnaire de l'IA et le convertit en ArbrePlan propre."""
    racines_brutes = donnees.get("plan")
    if not isinstance(racines_brutes, list):
        raise LLMError("La réponse de l'IA ne contient pas de plan.")

    compteur = [0]
    racines = []
    for brut in racines_brutes:
        noeud = _construire_noeud(brut, 1, compteur)
        if noeud is not None:
            racines.append(noeud)

    if not racines:
        raise LLMError("L'IA n'a trouvé aucun titre dans ce document.")

    return ArbrePlan(titre_cours=_nettoyer_libelle(donnees.get("titre_cours")), racines=racines)
