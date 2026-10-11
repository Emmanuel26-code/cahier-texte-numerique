# Contribuer au projet

## 1. Branches

- `main` : la version stable du projet, celle qu'on rendra.
- `develop` : la branche où l'équipe regroupe son travail en cours.
- `feature-nom` : une branche par fonctionnalité, toujours créée depuis `develop`.
  Exemples : `feature-readme`, `feature-connexion`.

Règles :
- On ne commite jamais directement sur `main`.
- On ne commite pas non plus directement sur `develop` : on travaille sur une branche `feature-...`.
- Quand une fonctionnalité est terminée, on ouvre une Pull Request de `feature-...` vers `develop`, et un autre membre de l'équipe la relit avant la fusion.
- `develop` est fusionnée dans `main` par Pull Request quand une version est stable.

## 2. Messages de commit

Format : `préfixe: phrase courte à l'impératif`

| Préfixe | Quand l'utiliser |
|---|---|
| `feat:` | nouvelle fonctionnalité |
| `fix:` | correction d'un bug |
| `docs:` | documentation (README, commentaires) |
| `chore:` | configuration, outils, dépendances |
| `refactor:` | réorganisation du code sans changer son comportement |
| `test:` | ajout ou modification de tests |

Exemple : `feat: ajoute la page de connexion`

Un commit par fonctionnalité terminée, avec un message clair.