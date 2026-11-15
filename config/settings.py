"""
Réglages Django du projet « Cahier de texte numérique ».

Tout ce qui change entre le poste de développement et la production se règle par
variables d'environnement (fichier .env en local, tableau de bord Vercel en production).
Voir .env.example pour la liste complète.
"""

import os
import warnings
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Charge le fichier .env (jamais versionné) s'il existe. DJANGO_ENV_FILE permet d'en
# choisir un autre, ex. .env.production pour lancer une commande sur la base Neon.
load_dotenv(BASE_DIR / os.environ.get("DJANGO_ENV_FILE", ".env"))


def env_bool(nom, defaut=False):
    return os.environ.get(nom, str(defaut)).strip().lower() in ("1", "true", "yes", "oui")


def env_liste(nom, defaut=""):
    return [v.strip() for v in os.environ.get(nom, defaut).split(",") if v.strip()]


# --- Sécurité de base ------------------------------------------------------------------
# DEBUG est désactivé par défaut : il faut l'activer explicitement en développement.
DEBUG = env_bool("DJANGO_DEBUG", False)

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured(
            "DJANGO_SECRET_KEY est obligatoire en production (DJANGO_DEBUG=False)."
        )
    SECRET_KEY = "dev-only-cle-a-remplacer"

ALLOWED_HOSTS = env_liste("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_liste("DJANGO_CSRF_TRUSTED_ORIGINS")

# Vercel fournit automatiquement le domaine du déploiement : on l'autorise.
for _variable in ("VERCEL_URL", "VERCEL_BRANCH_URL", "VERCEL_PROJECT_PRODUCTION_URL"):
    _domaine = os.environ.get(_variable)
    if _domaine:
        ALLOWED_HOSTS.append(_domaine)
        CSRF_TRUSTED_ORIGINS.append(f"https://{_domaine}")


# --- Applications ----------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Apps du projet
    "apps.comptes",
    "apps.academique",
    "apps.cahier",
    "apps.documents",
    "apps.plans",
    "apps.notifications",
    "apps.tableau_de_bord",
]

AUTH_USER_MODEL = "comptes.Utilisateur"
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "tableau_de_bord:accueil"  # oriente chaque rôle vers son tableau de bord
LOGOUT_REDIRECT_URL = "login"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # sert les fichiers statiques en production
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.academique.context_processors.annee_scolaire_courante",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# --- Base de données -------------------------------------------------------------------
# En production : DATABASE_URL (ex. postgres://… fourni par Neon/Vercel, ou mysql://…).
# En local : les variables DB_* (MySQL de XAMPP).
if os.environ.get("DATABASE_URL"):
    DATABASES = {
        "default": dj_database_url.config(conn_max_age=60, conn_health_checks=True)
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": os.environ.get("DB_NAME", "cahier_texte"),
            "USER": os.environ.get("DB_USER", "cahier_user"),
            "PASSWORD": os.environ.get("DB_PASSWORD", ""),
            "HOST": os.environ.get("DB_HOST", "localhost"),
            "PORT": os.environ.get("DB_PORT", "3306"),
        }
    }
if DATABASES["default"]["ENGINE"].endswith("mysql"):
    DATABASES["default"].setdefault("OPTIONS", {})["charset"] = "utf8mb4"
if DATABASES["default"]["ENGINE"].endswith("postgresql"):
    # Le pooler de Neon (PgBouncer, mode transaction) ne supporte pas les curseurs serveur.
    DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = True


# --- Cache -----------------------------------------------------------------------------
# Cache en base : partagé entre tous les processus / fonctions serverless (quota IA).
# La table est créée par la migration plans.0002_table_cache.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "cache_django",
    }
}


# --- Mots de passe ---------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# --- Langue et fuseau ------------------------------------------------------------------
LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Africa/Abidjan"
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# --- Fichiers statiques et fichiers importés -------------------------------------------
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
# WhiteNoise lit directement les dossiers static/ : pas besoin de collectstatic
# (utile sur Vercel, où le système de fichiers est en lecture seule).
WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = DEBUG
# Sans collectstatic, le dossier staticfiles/ n'existe pas : c'est voulu.
warnings.filterwarnings("ignore", message="No directory at: .*staticfiles")

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Stockage des documents importés : disque local par défaut, ou stockage objet
# compatible S3 (Cloudflare R2, Supabase Storage, AWS S3…) si S3_BUCKET est défini.
# Obligatoire sur Vercel : le disque des fonctions serverless n'est pas conservé.
if os.environ.get("S3_BUCKET"):
    STOCKAGE_DOCUMENTS = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": os.environ["S3_BUCKET"],
            # Noms S3_* (R2, S3…) ou noms AWS standard injectés par Neon (`neon env pull`).
            "endpoint_url": os.environ.get("S3_ENDPOINT_URL") or os.environ.get("AWS_ENDPOINT_URL_S3") or None,
            "access_key": os.environ.get("S3_ACCESS_KEY_ID") or os.environ.get("AWS_ACCESS_KEY_ID"),
            "secret_key": os.environ.get("S3_SECRET_ACCESS_KEY") or os.environ.get("AWS_SECRET_ACCESS_KEY"),
            "region_name": os.environ.get("S3_REGION") or os.environ.get("AWS_REGION") or None,
            # Neon Object Storage exige l'adressage « path-style » et SigV4 (R2 et S3 l'acceptent aussi).
            "addressing_style": "path",
            "signature_version": "s3v4",
            "default_acl": None,
            "querystring_auth": True,  # liens signés et temporaires : fichiers jamais publics
            "file_overwrite": False,
        },
    }
else:
    STOCKAGE_DOCUMENTS = {"BACKEND": "django.core.files.storage.FileSystemStorage"}

STORAGES = {
    "default": STOCKAGE_DOCUMENTS,
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

# Taille maximale d'un document importé (Vercel limite le corps d'une requête à 4,5 Mo).
DOCUMENT_MAX_OCTETS = int(os.environ.get("DOCUMENT_MAX_OCTETS", str(10 * 1024 * 1024)))
FILE_UPLOAD_MAX_MEMORY_SIZE = DOCUMENT_MAX_OCTETS


# --- Sessions : rester connecté ----------------------------------------------------------
# Avec « Rester connecté » (coché par défaut), la session dure 60 jours ; sinon elle
# se termine à la fermeture du navigateur (voir apps.comptes.views.Connexion).
SESSION_COOKIE_AGE = 60 * 24 * 3600
SESSION_COOKIE_SAMESITE = "Lax"


# --- E-mails (réinitialisation du mot de passe) ------------------------------------------
# Production : un serveur SMTP (Gmail avec mot de passe d'application, Brevo, Resend…).
# Sans EMAIL_HOST, les e-mails sont affichés dans la console (développement) et la page
# « Mot de passe oublié » indique que l'envoi n'est pas disponible.
EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
EMAIL_CONFIGURE = bool(EMAIL_HOST)
if EMAIL_CONFIGURE:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
    EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
    EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
    EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", EMAIL_PORT == 587)
    EMAIL_USE_SSL = env_bool("EMAIL_USE_SSL", EMAIL_PORT == 465)
    EMAIL_TIMEOUT = 15
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "Cahier de texte numérique <no-reply@cahier-texte.local>")
PASSWORD_RESET_TIMEOUT = 2 * 3600  # le lien de réinitialisation est valable 2 heures


# --- HTTPS (production) ----------------------------------------------------------------
if not DEBUG:
    SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", True)
    SESSION_COOKIE_SECURE = True  # le cookie de session ne circule qu'en HTTPS
    CSRF_COOKIE_SECURE = True  # idem pour le cookie CSRF
    SECURE_HSTS_SECONDS = 31536000  # le navigateur retiendra « HTTPS obligatoire » 1 an
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")  # derrière un proxy (Vercel, Nginx…)
    # Le préchargement HSTS est un engagement définitif sur le domaine : on ne l'active pas.
    SILENCED_SYSTEM_CHECKS = ["security.W021"]


# --- Journaux --------------------------------------------------------------------------
# Tout part sur la sortie standard : visible dans les logs Vercel ou du serveur.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"simple": {"format": "{asctime} {levelname} {name} : {message}", "style": "{"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "simple"}},
    "root": {"handlers": ["console"], "level": os.environ.get("DJANGO_LOG_LEVEL", "INFO")},
    "loggers": {"django.request": {"handlers": ["console"], "level": "WARNING", "propagate": False}},
}


# --- Module IA (plan de cours) — Google Gemini ------------------------------------------
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
# gemini-2.5-flash a été retiré par Google ; les modèles les plus récents (3.7, 3.8)
# sont souvent saturés pour les comptes gratuits. Modèles de secours essayés dans l'ordre.
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")
GEMINI_MODELES_SECOURS = env_liste("GEMINI_MODELES_SECOURS", "gemini-3.5-flash,gemini-3.1-flash-lite")
IA_TIMEOUT_SECONDS = int(os.environ.get("IA_TIMEOUT_SECONDS", "60"))
IA_MAX_CHARS = int(os.environ.get("IA_MAX_CHARS", "60000"))  # taille max du texte envoyé à l'IA
IA_MAX_FILE_BYTES = int(os.environ.get("IA_MAX_FILE_BYTES", str(10 * 1024 * 1024)))  # fichier max analysé
IA_MAX_PAGES = int(os.environ.get("IA_MAX_PAGES", "200"))  # pages de PDF lues au maximum
IA_MAX_GENERATIONS_PAR_HEURE = int(os.environ.get("IA_MAX_GENERATIONS_PAR_HEURE", "20"))
