"""Installation automatique du projet (Windows / Linux / macOS).

Usage :  python setup.py            (installe puis propose de lancer le serveur)
         python setup.py --no-run   (installe sans lancer le serveur)

Prérequis : Python 3 + MySQL démarré (XAMPP : bouton « Start » à côté de MySQL).
"""
import os
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RACINE = Path(__file__).resolve().parent
os.chdir(RACINE)
VENV = RACINE / ".venv"
PY = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")

ADMIN_USER, ADMIN_MAIL, ADMIN_PASS = "admin", "admin@example.com", "Admin12345!"


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
etape(2, "Installation des paquets (Django, mysqlclient, ...) - patience, 1 à 2 minutes")
try:
    lancer(PY, "-m", "pip", "install", "-q", "--upgrade", "pip")
    lancer(PY, "-m", "pip", "install", "-q", "-r", "requirements.txt")
except subprocess.CalledProcessError:
    erreur("l'installation des paquets a échoué (souvent : mysqlclient). "
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
    modele = modele.replace("DB_USER=cahier", "DB_USER=root").replace("DB_PASSWORD=votre_mot_de_passe", "DB_PASSWORD=")
    env.write_text(modele, encoding="utf-8")
    print("Créé avec les réglages XAMPP (root, sans mot de passe).")

# 4. Création de la base
etape(4, "Création de la base de données MySQL")
creer_base = (
    "import os, sys\n"
    "from dotenv import load_dotenv\n"
    "load_dotenv('.env')\n"
    "import MySQLdb\n"
    "try:\n"
    "    c = MySQLdb.connect(host=os.environ.get('DB_HOST','127.0.0.1'), port=int(os.environ.get('DB_PORT','3306')),\n"
    "                        user=os.environ.get('DB_USER','root'), passwd=os.environ.get('DB_PASSWORD',''))\n"
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
    f"if U.objects.filter(username='{ADMIN_USER}').exists(): print('Compte déjà existant.')\n"
    f"else:\n"
    f"    U.objects.create_superuser('{ADMIN_USER}', '{ADMIN_MAIL}', '{ADMIN_PASS}', role='administrateur'); print('Compte créé.')\n"
)
lancer(PY, "-c", creation)

print(f"""
==================================================================
 INSTALLATION TERMINÉE
 Site        : http://127.0.0.1:8000/
 Administration : http://127.0.0.1:8000/admin/
 Identifiant : {ADMIN_USER}      Mot de passe : {ADMIN_PASS}
 (compte de développement : à changer plus tard)
 Pour relancer le site plus tard : double-clic sur lancer.bat
==================================================================""")

if "--no-run" not in sys.argv:
    print("\nLancement du serveur (Ctrl+C pour arrêter)...")
    try:
        lancer(PY, "manage.py", "runserver")
    except KeyboardInterrupt:
        pass
