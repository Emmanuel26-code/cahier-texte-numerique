# Cahier de texte numérique

[![CI](https://github.com/Emmanuel26-code/cahier-texte-numerique/actions/workflows/ci.yml/badge.svg)](https://github.com/Emmanuel26-code/cahier-texte-numerique/actions/workflows/ci.yml)

Application web de gestion du cahier de texte d'un établissement scolaire.
Les professeurs enregistrent leurs séances, importent leurs cours (DOCX, PDF, TXT),
et une intelligence artificielle propose automatiquement un plan de cours
(titres et sous-titres) que le professeur peut modifier et valider.

## Fonctionnalités

| Rôle | Ce qu'il peut faire |
|---|---|
| **Professeur** | Saisir, modifier et supprimer ses séances (contenu, travail à faire, points du plan abordés) · importer ses cours · générer un plan par IA, le corriger puis le valider ou le rejeter · tableau de bord de ses classes |
| **Élève** | Consulter les séances et le travail à faire de sa classe · télécharger les cours · lire les plans validés · recevoir des notifications |
| **Administrateur** | Gérer utilisateurs, années, classes, matières et affectations · consulter l'historique des modifications · tableau de bord de l'établissement |

Sécurité : rôles vérifiés sur chaque page, fichiers contrôlés à l'import (format réel,
taille) et jamais servis par une adresse publique, mots de passe hachés (PBKDF2),
HTTPS obligatoire en production, quota horaire de générations IA.

## Technologies

- Python 3.12 et Django 5.2
- MySQL (développement) · PostgreSQL ou MySQL (production)
- Google Gemini (génération du plan de cours)
- GitHub Actions (intégration continue) · Vercel (hébergement)

## Installation sur un poste de développement (Windows)

Prérequis : [Python 3.12+](https://www.python.org/downloads/) et
[XAMPP](https://www.apachefriends.org/) (pour MySQL).

1. Dans XAMPP, cliquer sur **Start** à côté de **MySQL**.
2. Double-cliquer sur **`installer.bat`**. Le script :
   - crée l'environnement virtuel `.venv` et installe les paquets ;
   - crée le fichier `.env` (avec une clé secrète propre à votre poste) ;
   - crée la base `cahier_texte` et ses tables ;
   - crée un compte administrateur `admin` et **affiche son mot de passe une seule fois**.
3. Ouvrir http://127.0.0.1:8000/.

Pour relancer le site plus tard : double-clic sur **`lancer.bat`**.

Pour la génération de plans par IA, renseigner `GEMINI_API_KEY` dans `.env`
(clé gratuite sur https://aistudio.google.com/apikey).

### Installation manuelle (Linux, macOS ou Windows)

```bash
python -m venv .venv
.venv/Scripts/activate        # Windows ; sous Linux/macOS : source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # puis adapter les valeurs
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### Lancer les tests

```bash
python manage.py test
```

## Intégration continue (CI)

À chaque push et à chaque Pull Request vers `develop` ou `main`, GitHub Actions
([`.github/workflows/ci.yml`](.github/workflows/ci.yml)) vérifie, **sur MySQL et sur PostgreSQL** :

1. la configuration Django (`check`) et la configuration de production (`check --deploy`) ;
2. qu'aucune migration ne manque ;
3. que tous les tests passent.

Une Pull Request dont la CI est rouge ne doit pas être fusionnée. Pour l'imposer :
GitHub > Settings > Branches > règle sur `develop` et `main` > *Require status checks to pass*.

## Déploiement sur Vercel (CD)

Vercel exécute Django en fonctions serverless. Deux conséquences :
**la base de données et les fichiers importés doivent être hébergés ailleurs**
(le disque d'une fonction Vercel n'est pas conservé).

### 1. Créer les services externes (gratuits)

| Besoin | Service conseillé | Variable(s) à récupérer |
|---|---|---|
| Base de données | **Neon** (PostgreSQL), à ajouter depuis Vercel > Storage | `DATABASE_URL` |
| Fichiers importés | **Cloudflare R2** (compatible S3, 10 Go gratuits) | `S3_BUCKET`, `S3_ENDPOINT_URL`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY` |
| IA | Google AI Studio | `GEMINI_API_KEY` |

### 2. Créer le projet Vercel

1. Sur https://vercel.com : **Add New > Project**, importer le dépôt GitHub.
2. Framework : **Other**. Laisser les commandes de build vides.
3. Dans **Settings > Environment Variables**, ajouter :

   | Variable | Valeur |
   |---|---|
   | `DJANGO_SECRET_KEY` | résultat de `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
   | `DJANGO_DEBUG` | `False` |
   | `DATABASE_URL` | adresse Neon (`postgres://…?sslmode=require`) |
   | `S3_BUCKET`, `S3_ENDPOINT_URL`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, `S3_REGION` | valeurs Cloudflare R2 (`S3_REGION=auto`) |
   | `DOCUMENT_MAX_OCTETS` | `4194304` (Vercel refuse les envois de plus de 4,5 Mo) |
   | `GEMINI_API_KEY` | votre clé |
   | `IA_TIMEOUT_SECONDS` | `50` (une fonction Vercel est coupée au bout de 60 s) |

   Le domaine `*.vercel.app` est autorisé automatiquement. Pour un domaine personnalisé,
   ajouter aussi `DJANGO_ALLOWED_HOSTS` et `DJANGO_CSRF_TRUSTED_ORIGINS`.
4. Dans **Settings > Git**, choisir `main` comme branche de production.

### 3. Préparer la base de production (une seule fois)

Depuis votre poste, avec l'adresse de la base de production :

```bash
DATABASE_URL="postgres://…" DJANGO_DEBUG=False DJANGO_SECRET_KEY=x python manage.py migrate
DATABASE_URL="postgres://…" DJANGO_DEBUG=False DJANGO_SECRET_KEY=x python manage.py createsuperuser
```

Puis, dans GitHub > Settings > Secrets and variables > Actions, créer le secret
`PRODUCTION_DATABASE_URL` avec la même adresse.

### 4. Ensuite, tout est automatique

```
Pull Request vers develop ──► CI (tests MySQL + PostgreSQL)
develop fusionnée dans main ──► GitHub Actions applique les migrations (deploiement.yml)
                            └─► Vercel publie la nouvelle version
```

Chaque Pull Request reçoit aussi une **préversion Vercel** (adresse temporaire) pour tester avant fusion.

## Équipe

- Oladokou
- Kablan
- Gogo
- Zana
- Souleymane

Projet réalisé à l'ESATIC, filière Systèmes Informatiques et Génie Logiciel.

## Contribuer

Voir le fichier [CONTRIBUTING.md](CONTRIBUTING.md).
