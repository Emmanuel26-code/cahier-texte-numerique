"""Exceptions du module IA.

Chaque erreur porte un message en français, destiné à être affiché au professeur.
"""


class GenerationPlanError(Exception):
    """Erreur de base : la génération du plan a échoué."""


class ExtractionError(GenerationPlanError):
    """Le fichier n'a pas pu être lu ou ne contient aucun texte exploitable."""


class LLMError(GenerationPlanError):
    """Le service d'IA est indisponible ou a répondu de façon inexploitable."""


class ConfigurationIAError(GenerationPlanError):
    """Le service d'IA n'est pas configuré (clé API manquante, par exemple)."""
