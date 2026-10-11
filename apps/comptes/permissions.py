from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied


def role_requis(*roles):
    """Réserve une vue aux utilisateurs ayant l'un des rôles indiqués.

    - non connecté          -> redirigé vers la page de connexion
    - connecté, mauvais rôle -> erreur 403 (accès interdit)
    """

    def decorateur(vue):
        @wraps(vue)
        def vue_protegee(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if request.user.role not in roles:
                raise PermissionDenied
            return vue(request, *args, **kwargs)

        return vue_protegee

    return decorateur