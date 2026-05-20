# 2026-05-20 — Ajout chantiers OPERAT et contrats de maintenance

## Objectif

Ajouter au cockpit Obsidian deux fonctionnalités manquantes signalées par l'utilisateur :

- connexion OPERAT / décret éco tertiaire ;
- gestion des contrats de maintenance avec affectation aux bâtiments concernés.

## Ce qui a été fait

- [[Backlog]] : ajout de `PO2-OPERAT-001` et `PO2-MAINT-001` en priorité P1.
- [[03-Roadmap-fonctionnalites]] : ajout d'une section "Nouveaux besoins utilisateur — 2026-05-20".
- [[00-Index]] : ajout des deux nouvelles notes module.
- [[Modules/Conformite-OPERAT]] : cadrage EFA, consommations annuelles, trajectoire réglementaire, API OPERAT à valider.
- [[Modules/Maintenance-Contrats]] : cadrage modèle `MaintenanceContract`, affectation multi-bâtiments, pièces PDF, échéances.
- [[Modules/Gestion-technique]] : ajout d'une section contrats de maintenance et du lien métier avec équipements/bâtiments.

## Points de vigilance

- La documentation API OPERAT détaillée n'a pas été trouvée publiquement via sources officielles rapides. Le chantier doit commencer par cadrer les accès et la documentation ADEME/OPERAT.
- Ne pas développer l'écriture directe vers OPERAT avant d'avoir validé authentification, endpoints, environnement de test et responsabilité de déclaration.
- Le MVP recommandé pour OPERAT est d'abord un suivi local + export annuel, puis API.
- Des changements BPU sont en cours dans la worktree par une autre IA : éviter de mélanger les commits.

## Handoff suivant

Prochaine fonctionnalité hors BPU/ENEDIS :

1. solder/déployer `PO2-GT-001` si le split CVC/Enveloppe n'est pas encore en production ;
2. choisir entre `PO2-MAINT-001` et `PO2-OPERAT-001`.

Recommandation : commencer par `PO2-MAINT-001`, car il dépend seulement du patrimoine existant et de la gestion technique. `PO2-OPERAT-001` doit d'abord attendre le cadrage d'accès API OPERAT, mais un MVP export local peut être lancé sans API.
