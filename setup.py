"""Installation automatique du projet (Windows / Linux / macOS).

Usage :  python setup.py            (installe puis propose de lancer le serveur)
         python setup.py --no-run   (installe sans lancer le serveur)

Prérequis : Python 3 + MySQL démarré (XAMPP : bouton « Start » à côté de MySQL).
"""
import os
import secrets
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RACINE = Path(__file__).resolve().parent
os.chdir(RACINE)
VENV = RACINE / ".venv"
PY = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")

ADMIN_USER, ADMIN_MAIL = "admin", "admin@example.com"
# Mot de passe tiré au hasard à chaque installation : jamais écrit dans le code.
ADMIN_PASS = secrets.token_urlsafe(12)


def etape(n, texte):
    print(f"\n[{n}/6] {texte}")


def lancer(*cmd, **kw):
    return subprocess.run([str(c) for c in cmd], check=True, **kw)


def erreur(msg):
    print(f"\nERREUR : {msg}")
    sys.exit(1)


# 1. Environnement virtuel
etape(1, "Création de l'environnement virtuel (.venv)")
if not PY.exists():
    lancer(sys.executable, "-m", "venv", VENV)
print("OK")

# 2. Paquets
etape(2, "Installation des paquets (Django, PyMySQL, ...) - patience, 1 à 2 minutes")
try:
    lancer(PY, "-m", "pip", "install", "-q", "--upgrade", "pip")
    lancer(PY, "-m", "pip", "install", "-q", "-r", "requirements.txt")
except subprocess.CalledProcessError:
    erreur("l'installation des paquets a échoué (connexion Internet ?). "
           "Copie le message d'erreur ci-dessus et envoie-le à Claude.")
print("OK")

# 3. Fichier .env
etape(3, "Fichier de configuration .env")
env = RACINE / ".env"
if env.exists():
    print("Déjà présent : conservé tel quel.")
else:
    modele = (RACINE / ".env.example").read_text(encoding="utf-8")
    # Réglages XAMPP par défaut : utilisateur root sans mot de passe
    modele = modele.replace("DB_USER=cahier_user", "DB_USER=root")
    # Clé secrète propre à ce poste (le mode développement est déjà activé dans le modèle)
    modele = modele.replace("DJANGO_SECRET_KEY=changez-moi", f"DJANGO_SECRET_KEY={secrets.token_urlsafe(50)}")
    env.write_text(modele, encoding="utf-8")
    print("Créé avec les réglages XAMPP (root, sans mot de passe).")

# 4. Création de la base
etape(4, "Création de la base de données MySQL")
creer_base = (
    "import os, sys\n"
    "from dotenv import load_dotenv\n"
    "load_dotenv('.env')\n"
    "import pymysql\n"
    "try:\n"
    "    c = pymysql.connect(host=os.environ.get('DB_HOST','127.0.0.1'), port=int(os.environ.get('DB_PORT','3306')),\n"
    "                        user=os.environ.get('DB_USER','root'), password=os.environ.get('DB_PASSWORD',''))\n"
    "except Exception as e:\n"
    "    print('CONNEXION_IMPOSSIBLE', e); sys.exit(2)\n"
    "nom = os.environ.get('DB_NAME','cahier_texte')\n"
    "c.cursor().execute('CREATE DATABASE IF NOT EXISTS `%s` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci' % nom)\n"
    "print('Base prête :', nom)\n"
)
r = subprocess.run([str(PY), "-c", creer_base], capture_output=True, text=True)
print(r.stdout.strip())
if r.returncode != 0:
    erreur("impossible de se connecter à MySQL.\n"
           "  -> Ouvre XAMPP et clique sur « Start » à côté de MySQL (ligne verte), puis relance ce script.\n"
           f"  Détail : {r.stdout.strip() or r.stderr.strip()[-300:]}")

# 5. Migrations
etape(5, "Création des tables (migrations)")
try:
    lancer(PY, "manage.py", "migrate", "-v", "0")
except subprocess.CalledProcessError:
    erreur("les migrations ont échoué. Copie le message ci-dessus et envoie-le à Claude.")
print("OK : toutes les tables sont créées.")

# 6. Compte administrateur
etape(6, "Compte administrateur")
creation = (
    "import django, os\n"
    "os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings'); django.setup()\n"
    "from apps.comptes.models import Utilisateur as U\n"
    "nom, mail, mdp = os.environ['ADMIN_USER'], os.environ['ADMIN_MAIL'], os.environ['ADMIN_PASS']\n"
    "if U.objects.filter(username=nom).exists(): print('DEJA_EXISTANT')\n"
    "else:\n"
    "    U.objects.create_superuser(nom, mail, mdp, role='administrateur')\n"
)
r = subprocess.run([str(PY), "-c", creation], capture_output=True, text=True, check=True,
                   env={**os.environ, "ADMIN_USER": ADMIN_USER, "ADMIN_MAIL": ADMIN_MAIL, "ADMIN_PASS": ADMIN_PASS})
compte_existant = "DEJA_EXISTANT" in r.stdout
print("Compte déjà existant : mot de passe inchangé." if compte_existant else "Compte créé.")

print(f"""
==================================================================
 INSTALLATION TERMINÉE
 Site        : http://127.0.0.1:8000/
 Administration : http://127.0.0.1:8000/admin/
 Identifiant : {ADMIN_USER}      Mot de passe : {"(inchangé)" if compte_existant else ADMIN_PASS}
 (notez ce mot de passe : il n'est affiché qu'une seule fois)
 Pour relancer le site plus tard : double-clic sur lancer.bat
==================================================================""")

if "--no-run" not in sys.argv:
    print("\nLancement du serveur (Ctrl+C pour arrêter)...")
    try:
        lancer(PY, "manage.py", "runserver")
    except KeyboardInterrupt:
        pass
