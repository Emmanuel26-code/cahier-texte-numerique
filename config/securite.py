"""En-têtes de sécurité ajoutés à toutes les réponses.

Content-Security-Policy : le navigateur n'exécute que les scripts servis par le site
lui-même (aucun script dans les pages, aucun script d'un autre domaine). Une injection
de code HTML ne peut donc pas lancer de JavaScript.
"""
from django.conf import settings

POLITIQUE = "; ".join([
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
    "font-src 'self' https://fonts.gstatic.com",
    "img-src 'self' data:",
    "connect-src 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "object-src 'none'",
])

PERMISSIONS = "camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()"


class EnTetesSecurite:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        reponse = self.get_response(request)
        politique = POLITIQUE if settings.DEBUG else POLITIQUE + "; upgrade-insecure-requests"
        reponse.headers.setdefault("Content-Security-Policy", politique)
        reponse.headers.setdefault("Permissions-Policy", PERMISSIONS)
        return reponse
