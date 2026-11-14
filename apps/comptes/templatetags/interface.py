"""Petits outils d'affichage communs à toutes les pages.

{% load interface %}
{% icone "accueil" %}        -> icône SVG (traits, couleur du texte)
{{ octets|taille }}         -> « 4 Mo », « 512 Ko », « 1,5 Mo »
"""
from django import template
from django.utils.html import format_html
from django.utils.safestring import mark_safe

register = template.Library()

# Tracés au format 24 x 24 (style « lignes »), sans dépendance externe.
TRACES = {
    "accueil": '<rect x="3" y="3" width="7" height="9" rx="1.5"/><rect x="14" y="3" width="7" height="5" rx="1.5"/><rect x="14" y="12" width="7" height="9" rx="1.5"/><rect x="3" y="16" width="7" height="5" rx="1.5"/>',
    "cahier": '<path d="M4 19.5V5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2.5z"/><path d="M8 7h7M8 11h7"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "documents": '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M9 13h6M9 17h4"/>',
    "cloche": '<path d="M18 8a6 6 0 1 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.7 21a2 2 0 0 1-3.4 0"/>',
    "affectations": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M19 8v6M22 11h-6"/>',
    "utilisateurs": '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.9M16 3.1a4 4 0 0 1 0 7.8"/>',
    "referentiels": '<path d="M3 6h18M3 12h18M3 18h12"/>',
    "historique": '<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5M12 7v5l3 3"/>',
    "crayon": '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/>',
    "etincelle": '<path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z"/>',
    "eleve": '<path d="M22 10L12 5 2 10l10 5 10-5z"/><path d="M6 12v5c3 2 9 2 12 0v-5"/>',
    "envoi": '<path d="M12 16V4M7 9l5-5 5 5"/><path d="M5 20h14"/>',
    "telecharger": '<path d="M12 4v12M7 11l5 5 5-5"/><path d="M5 20h14"/>',
    "plan": '<path d="M8 6h13M8 12h13M8 18h13"/><circle cx="4" cy="6" r="1"/><circle cx="4" cy="12" r="1"/><circle cx="4" cy="18" r="1"/>',
    "valider": '<path d="M20 6L9 17l-5-5"/>',
    "retour": '<path d="M15 18l-6-6 6-6"/>',
    "suivant": '<path d="M9 18l6-6-6-6"/>',
    "cle": '<circle cx="7.5" cy="15.5" r="4.5"/><path d="M10.7 12.3L21 2M16 7l3 3M14 9l2 2"/>',
    "sortie": '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="M16 17l5-5-5-5M21 12H9"/>',
    "echange": '<path d="M16 3l4 4-4 4"/><path d="M20 7H4M8 21l-4-4 4-4"/><path d="M4 17h16"/>',
}


@register.simple_tag
def icone(nom, taille=18):
    trace = TRACES.get(nom, "")
    return format_html(
        '<svg class="icone" width="{0}" height="{0}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">{1}</svg>',
        taille, mark_safe(trace),
    )


def taille_lisible(octets):
    """Taille en Ko / Mo / Go à la française (virgule décimale, sans « Mio »)."""
    try:
        valeur = float(octets)
    except (TypeError, ValueError):
        return ""
    for unite in ("octets", "Ko", "Mo", "Go"):
        if valeur < 1024 or unite == "Go":
            break
        valeur /= 1024
    if unite == "octets":
        return f"{int(valeur)} octet{'s' if int(valeur) > 1 else ''}"
    texte = f"{valeur:.1f}".rstrip("0").rstrip(".").replace(".", ",")
    return f"{texte} {unite}"


register.filter("taille", taille_lisible)
