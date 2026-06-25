# Session - Prototype frontend V1 sans backend

> Date : 2026-06-24

## Objectif

Produire un premier jet moderne, dynamique et agreable de la refonte, sans backend et sans modifier le SaaS existant.

## Livrables

- `docs/prototype-refonte-v1/index.html` ;
- `docs/prototype-refonte-v1/styles.css` ;
- `docs/prototype-refonte-v1/app.js` ;
- `docs/prototype-refonte-v1/ouvrir-prototype.cmd` ;
- `docs/29-Prototype-frontend-V1-sans-backend.md`.

## Choix de conception

- shell sombre stable et espace de travail clair ;
- couleur menthe pour action/confiance, ambre et corail pour arbitrage/risque ;
- cockpit personnalise sans fragmenter la plateforme ;
- global vers detail par panneau lateral ;
- Site 360 comme porte d entree transversale ;
- qualite de la donnee exposee avec les indicateurs.

## Validation

- syntaxe JavaScript : OK ;
- page chargee via `http://127.0.0.1:8765/prototype-refonte-v1/index.html` ;
- cockpit Direction et Fluides : OK ;
- vue factures et six lignes simulees : OK ;
- ouverture du dossier TotalEnergies et quatre controles : OK ;
- Site 360, quatre sites et six onglets : OK ;
- recherche globale : OK ;
- aucune erreur console observee.

## Handoff suivant

Recueillir le retour utilisateur sur la direction visuelle, la densite, la navigation, le dossier facture et le Site 360. Ne pas raccorder au backend avant cette revue. Apres validation, extraire tokens et composants vers le frontend React puis cabler une tranche verticale facture.