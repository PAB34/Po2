# Session - Spec execution refonte Factures Decisions V1

Date : 2026-06-26  
Objet : cadrer la prochaine etape concrete de refonte de l interface, en prenant `Factures & decisions` comme premiere tranche verticale.

## Travail realise

- Creation de `docs/49-Spec-execution-refonte-Factures-Decisions-V1.md`.
- Rappel des sources relues : docs 35, 38, 40, 41, 48, maquette statique et code React/backend existant.
- Identification des briques a reutiliser : imports ENGIE/EDF, gaz TotalEnergies, CPE/DALKIA, decisions facture, matrices versionnees, snapshots et exports finance.
- Definition du parcours cible : page d arrivee, KPI comptabilite, file de factures, fiche facture, statuts, donnees/API et phases de developpement.
- Ajout du document dans `docs/00-Index.md`.

## Decisions prises

- `Factures & decisions` devient la premiere tranche verticale de refonte definitive.
- La Phase 1 doit etre une hygiene/alignement visuel du React V1 avant raccord backend plus profond.
- La page React devra conserver les hooks actuels au debut, mais clarifier fallback/API et remplacer les KPI par la logique comptabilite.

## Handoff suivant

Prochaine action recommandee : commencer la Phase 1 du document 49.

1. Nettoyer l encodage de `saas/frontend/src/features/invoices/*` et des commentaires mojibake dans `saas/frontend/src/lib/api.ts`.
2. Aligner `InvoicesDecisionPageV1.tsx` sur la maquette statique corrigee.
3. Remplacer les KPI par la logique comptabilite.
4. Garder les hooks actuels mais rendre explicite le mode API/fallback.
5. Lancer `tsc -b` avec le Node portable.

## Avance Phase 1 - 26/06/2026

Apres creation de cette spec, un premier correctif React a ete applique :

- `saas/frontend/src/features/invoices/InvoicesDecisionPageV1.tsx` utilise maintenant les KPI comptabilite cibles : `À contrôler`, `Conformes`, `Avec anomalie`, `Prêtes à transmettre`.
- Verification TypeScript : `tsc -b` OK avec le Node portable.

Reste pour Phase 1 : aligner davantage le layout React sur la maquette statique et expliciter visuellement le mode API/fallback.

## Avance Phase 1 bis - 26/06/2026

La page React `saas/frontend/src/features/invoices/InvoicesDecisionPageV1.tsx` a ete alignee plus fortement sur la maquette statique :

- ajout d'un entete avec actions `Rapports d'import` et `Importer des factures` ;
- ajout d'un bandeau visible indiquant le mode de donnees : API, synchronisation ou demonstration ;
- ajout d'une chaine de traitement `Importer -> Dedoublonner -> Controler -> Imputer -> Decider -> Exporter` ;
- conservation de la file factures et du drawer existants ;
- ajout de styles dedies dans `saas/frontend/src/design-system/tokens.css` ;
- verification encodage sur les fichiers modifies : pas de marqueurs mojibake detectes ;
- validation TypeScript : `tsc -b` OK.

Prochaine action : raccorder le calcul des KPI aux vraies lignes agregees au lieu de valeurs statiques, puis enrichir le drawer detail facture par source.

## Suite du raccord React - KPI calcules

- Remplacement des KPI statiques de l'ecran React `Factures & decisions` par des KPI calcules depuis la file agregee des factures.
- Ajout de helpers de formatage/somme pour afficher les montants agreges en euros.
- Les factures CPE/DALKIA contribuent maintenant au total agrege via leur total HT, en attendant une normalisation HT/TTC plus robuste.
- Controle Unicode realise sur les fichiers React touches : pas de marqueurs mojibake `U+00C3`, `U+00C2`, `U+00EF`, `U+FFFD`.
- Validation : `npx tsc -b` OK.

## Suite du raccord React - drawer contextualise

- Ajout d'une fiche source dans le drawer facture.
- Le contenu s'adapte a `energy-import`, `gas-totalenergies`, `cpe-dalkia` ou `mock`.
- But UX : que l'utilisateur comprenne immediatement quel controle metier est attendu selon le type de facture, avant de lire la trace ligne par ligne.
- Styles ajoutes dans `tokens.css` via `.po2-invoice-source-profile`.
- Validation : `npx tsc -b` OK.
