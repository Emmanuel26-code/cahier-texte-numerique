from django.apps import AppConfig


class ComptesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.comptes"
    label = "comptes"

    def ready(self):
        from . import securite  # noqa: F401  (branche le comptage des échecs de connexion)
