# Environnement poste entreprise

> Contrainte utilisateur : le poste local ne permet pas d'installer des bibliotheques Python, Node, npm, outils systeme ou dependances projet.

## Principe

Le PC utilisateur est un poste de pilotage :

- Obsidian pour la gestion projet ;
- navigateur pour l'application et GitHub ;
- Codex/IA pour lire, modifier, documenter et orchestrer ;
- GitHub Actions, Codespaces, VPS ou conteneurs existants pour executer les validations.

Il ne faut pas construire de workflow qui depend d'une installation locale manuelle.

## Ce qu'une IA ne doit pas demander

Ne pas demander a l'utilisateur :

- d'installer Python, Node, npm, pip, pytest, Docker, Tesseract, Poppler ou une librairie ;
- de lancer une commande locale si elle depend d'un outil non deja present ;
- de modifier son poste entreprise pour contourner les restrictions IT.

## Methode de validation recommandee

| Besoin | Methode preferee |
|---|---|
| Build frontend | GitHub Actions ou conteneur frontend |
| Tests backend | GitHub Actions ou conteneur backend |
| Migrations Alembic | Conteneur backend / VPS |
| Nouvelle dependance Python | `requirements.txt` + Dockerfile/CI, puis validation distante |
| Nouvelle dependance frontend | `package.json` + lockfile si present, puis validation CI |
| Parser PDF/OCR | Backend Docker, jamais poste utilisateur |
| Verification prod | Endpoint public ou VPS si acces autorise |

## Impacts sur les prochains chantiers

### Parser BPU

Si `pdfplumber` est retenu, il doit etre ajoute a `saas/backend/requirements.txt` et valide dans l'image backend. L'utilisateur n'a rien a installer.

### Tests

Les commandes `pytest` et `npm run build` peuvent rester les commandes de reference du projet, mais elles doivent etre executees par CI, Codespaces, conteneurs ou Codex quand l'environnement le permet.

### Documentation

Chaque note de handoff doit preciser si une commande est :

- executable localement sans installation ;
- a executer dans un conteneur ;
- a executer via CI ;
- a executer sur le VPS.

## Phrase standard pour les futures IA

```
Attention : le poste utilisateur est verrouille entreprise. Ne pas demander d'installation locale. Ajouter les dependances au repo et valider via CI/conteneur/VPS.
```

