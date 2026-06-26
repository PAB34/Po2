# Preview Factures & decisions V1

Date : 2026-06-25

## Objectif

Construire une preview UX avancee du futur poste de controle des factures, sans backend, avant raccordement au staging.

Route locale :

- `http://127.0.0.1:5173/refonte-v1/factures-preview`

Cette route est publique localement et ne fait aucune ecriture. Elle sert a valider l'experience utilisateur.

## Pourquoi cette preview

Le projet dispose deja de beaucoup de fonctionnalites backend et d'ecrans historiques pour les factures. Le risque de la refonte est de reconstruire un frontend joli mais trop technique, ou trop proche des endpoints.

La preview met donc en scene le workflow metier attendu :

> Import facture -> parsing -> controle -> matrice comptable -> decision -> historique -> export finance.

## Contenu de la preview

La page presente :

- une file de factures priorisee ;
- des statuts lisibles : nouvelle, a controler, litige, historique ;
- une synthese du controle ;
- l'etat de la matrice comptable ;
- une decision recommandee ;
- des actions metier ;
- une trace de controle ;
- une imputation comptable proposee ;
- un historique anti-doublon / reimport.

## Cas metier representes

### DALKIA

Cas : CPE / P1 gaz.

But UX : montrer une facture techniquement coherente mais avec ventilation comptable incomplete.

Decision attendue : corriger ou confirmer l'imputation avant export finance.

### ENGIE

Cas : electricite lot 1.

But UX : montrer une facture conforme, prete a validation comptable.

Decision attendue : valider puis exporter finance.

### TotalEnergies

Cas : gaz.

But UX : montrer une facture avec ecart fournisseur, notamment CTA.

Decision attendue : preparer un mail fournisseur ou mettre en attente.

### EDF

Cas : electricite / voirie.

But UX : montrer le traitement historique d'une facture deja importee.

Decision attendue : conserver l'historique si le reimport est identique.

## Decisions UX posees

1. La page ne doit pas seulement lister les factures : elle doit guider la decision.
2. Le controle doit etre lisible par un non-developpeur : preuve, valeur, detail, statut.
3. L'imputation comptable doit etre visible avant export finance.
4. Le reimport d'une facture deja traitee doit etre explicite.
5. Le litige fournisseur doit pouvoir produire une action claire : mail, attente, commentaire.

## Ce qui reste a raccorder

La preview doit ensuite etre connectee progressivement a :

- imports factures ENGIE/EDF ;
- factures gaz TotalEnergies ;
- factures finances DALKIA ;
- snapshots comptables `/api/accounting-matrices/invoices/{source}/{invoice_id}/snapshot` ;
- apply matrice ;
- validation snapshot ;
- export finance.

## Prochaine etape recommandee

1. Faire une revue visuelle/metier de `/refonte-v1/factures-preview`.
2. Ajuster les statuts et actions si besoin.
3. Raccorder l'ecran reel `/refonte-v1/factures` a la logique de cette preview.
4. Deployer sur staging `https://staging.135-125-152-112.sslip.io`.
5. Tester avec des factures reelles et ajuster les cas limites.

## Note importante

Cette preview ne remplace pas l'ecran reel. Elle donne la cible d'experience utilisateur. Le raccordement API devra conserver la meme logique, mais avec les donnees et statuts issus du backend.
## Correction du 25/06/2026 - alignement maquette et navigation preview

Constat : la preview React `Factures & decisions` avait ete integree dans le shell applicatif V1 (`AppShellV1`). Visuellement, elle ressemblait donc davantage a une page fonctionnelle raccordable qu'a la maquette produit validee dans `docs/prototype-refonte-v1`. Surtout, le menu lateral utilisait les vraies routes `/refonte-v1/...`, protegees par authentification, ce qui expliquait le renvoi vers l'ecran de login lors des clics sur d'autres entrees.

Correction realisee :

- `RefonteV1InvoicesPreviewPage.tsx` devient une preview autonome publique, sans `AppShellV1`.
- La structure reprend l'esprit de la maquette statique : sidebar sombre, workspace, topbar, recherche globale, page head, workflow horizontal, KPI, matrices contractuelles, tableau de factures et dossier facture lateral.
- Les entrees du menu de preview ne pointent plus vers les routes protegees. Seule `Matrices comptables` pointe vers `/refonte-v1/matrices-preview`, egalement publique.
- Les autres entrees restent des boutons de maquette non raccordes tant que leurs previews React dediees ne sont pas creees.

Decision UX : tant qu'une page est en mode preview, elle ne doit jamais utiliser la navigation authentifiee de l'application reelle. On distingue donc clairement :

- `/prototype-refonte-v1/index.html` : maquette statique globale, tres libre.
- `/refonte-v1/*-preview` : previews React publiques, sans backend, proches de la maquette.
- `/refonte-v1/*` : futures pages raccordees, protegees par authentification.

## Correctif du 26/06/2026 - protection de la maquette statique

Constat utilisateur : la page `Factures & décisions` affichait des textes corrompus du type `contrÃ´ler`, et la ligne des quatre KPI ne correspondait plus clairement aux KPI comptabilité attendus.

Corrections réalisées :

- Réparation de l'encodage UTF-8 de `docs/prototype-refonte-v1/app.js`.
- Vérification de `index.html`, `app.js` et `styles.css` : plus de marqueurs classiques de mojibake (`Ã`, `Â`, caractère de remplacement).
- La route statique `/refonte-v1/factures-preview/` reste le point d'entrée fiable tant que Vite est bloqué par le poste Windows.
- La page `Factures & décisions` ne duplique plus ses KPI : elle réutilise directement `profiles.finances.kpis`.
- À l'ouverture directe de `?view=invoices`, le profil simulé est maintenant initialisé sur `Comptable` au lieu de `Direction`.
- Les quatre cartes KPI de la ligne Factures ont une hauteur uniforme via CSS.
- Cache-buster passé en `20260626-2` pour forcer le navigateur à charger les fichiers corrigés.

Règle de prudence pour la suite : ne jamais réécrire les fichiers de maquette statique avec des commandes PowerShell qui peuvent interpréter l'UTF-8 comme ANSI. Pour les modifications ciblées, utiliser Python en lecture/écriture UTF-8 explicite ou l'éditeur applicatif habituel.
