from django.utils import timezone

from .models import AnneeScolaire


def annee_scolaire_courante(request):
    aujourd_hui = timezone.localdate()
    return {
        "annee_scolaire_courante": AnneeScolaire.objects.filter(
            date_debut__lte=aujourd_hui,
            date_fin__gte=aujourd_hui,
        ).first()
    }
