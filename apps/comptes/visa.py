"""Visa de la direction : l'administrateur marque une séance, un cours ou un plan comme « vu »."""
from django.contrib import messages
from django.utils import timezone


def marquer_vu(request, objet):
    """Enregistre la date et l'auteur du visa (une seule fois : le premier visa est conservé)."""
    if objet.vu_le is None:
        objet.vu_le = timezone.now()
        objet.vu_par = request.user
        objet.save(update_fields=["vu_le", "vu_par"])
    messages.success(request, "Marqué comme vu.")
