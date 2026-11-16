# Cahier de texte numérique

Application web de gestion du cahier de texte d'un établissement scolaire.
Les professeurs enregistrent leurs séances, importent leurs cours (DOCX, PDF, TXT, PPTX, XLSX),
et une intelligence artificielle propose automatiquement un plan de cours
(titres et sous-titres) que le professeur peut modifier et valider.

## Fonctionnalités

| Rôle | Ce qu'il peut faire |
|---|---|
| **Professeur** | Saisir, modifier et supprimer ses séances (contenu, travail à faire, points du plan abordés) · importer ses cours · générer un plan par IA, le corriger puis le valider ou le rejeter · tableau de bord de ses classes |
| **Élève** | Choisir sa classe à l'inscription · consulter les séances et le travail à faire de sa classe · télécharger les cours · lire les plans validés · recevoir des notifications |
| **Administrateur** | Gérer utilisateurs, années, classes, matières et affectations · valider les comptes professeurs · consulter et viser les séances, cours et plans · consulter l'historique des modifications · tableau de bord de l'établissement |

## Technologies

- Python 3.12 et Django 5.2
- PostgreSQL (production) · MySQL (développement)
- Google Gemini (génération du plan de cours)
- HTML, CSS et JavaScript (interface adaptée aux téléphones)

## Équipe

- Oladokou
- Kablan
- Gogo
- Zana
- Souleymane

Projet réalisé à l'ESATIC, filière Systèmes Informatiques et Génie Logiciel.
