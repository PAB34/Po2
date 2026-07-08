# Décisions — UI d'import de factures (`/refonte-v1/factures`)

> Doc « fil du dev » — décisions AVANT code. Fait suite au cadrage
> `import-factures-ui-cadrage.md` (2026-07-07). Branche : `feat/factures-import-ui`.

## Existant vérifié (worktree origin/main)

- **Front** : `features/invoices/InvoicesDecisionPageV1.tsx:497` — bouton « Importer des
  factures » en `variant="ghost" disabled`, title « Import à brancher… ». Aucun handler.
- **Back — endpoints d'import déjà présents, un par type** :

  | Type | Endpoint | Comportement |
  |---|---|---|
  | PDF énergie unitaire | `POST /billing/invoices/imports` | 1 fichier, dédup auto, réponse `EnergyInvoiceUploadResponse` |
  | ENGIE xlsx (N bordereaux) | `POST /billing/invoices/imports/xlsx?force_update=` | batch async (202), `EnergyInvoiceBatchDetailOut` |
  | EDF csv | `POST /billing/invoices/imports/edf-csv?force_update=` | batch async (202), idem |
  | Gaz TotalEnergies | `POST /gas/invoices/import` | import dédié |
  | DALKIA CPE | `POST /cpe/dalkia-ref/preview` + `/confirm` | **2 étapes** (aperçu → confirmation) |

  → Un **endpoint d'upload unifié back n'est pas nécessaire** : chaque type a déjà son entrée,
  avec dédoublonnage/idempotence en place.

## Décisions arrêtées (2026-07-08)

- **Q1 → Tiroir** (`Drawer`) dans la page factures. Confirmé après comparaison avec une
  variante « inline » (routage par extension) : l'utilisateur préfère le tiroir car il
  **choisit explicitement le fournisseur/destination** (« chez qui la facture atterrit »).
- **Q2 → Choix explicite** du fournisseur/type (pas de détection auto).
- **Q3 → ENGIE xlsx + EDF csv** en v1. Gaz TE et DALKIA plus tard.
- **Q4 → Endpoints existants par type** (aucun back à écrire) : réutilise
  `uploadEngieXlsxExport` / `uploadEdfCsvExport` déjà présents dans `lib/api.ts`.
- **Q5 → Ouvert à tous** (revirement du 2026-07-08 : plus de restriction admin).
- Analyse back **asynchrone** → le hook **poll** le batch pour afficher les vrais
  compteurs (créées / doublons / erreurs), pas des 0.

## Questions à trancher + recommandations (historique)

- **Q1 — Tiroir d'upload dans la page, ou page d'import dédiée ?**
  Reco : **tiroir (`Drawer`)** dans la page factures (composant `Drawer` déjà importé et utilisé
  pour les décisions). Reste dans le contexte, ferme après import, la table se rafraîchit.

- **Q2 — Point multi-format (détection auto) ou choix explicite du fournisseur/type ?**
  Reco : **choix explicite** en v1 (sélecteur type : ENGIE xlsx / EDF csv / Gaz TE / — DALKIA plus
  tard). Chaque type a son endpoint et ses contraintes d'extension ; la détection auto viendra après.

- **Q3 — Quels formats en premier ?**
  Reco : **ENGIE xlsx + EDF csv d'abord** (batch, retour riche créées/doublons/erreurs déjà prêt,
  même réponse `EnergyInvoiceBatchDetailOut`), puis **Gaz TE**. **DALKIA en dernier** (flux 2 étapes
  preview→confirm, plus lourd, sur `/cpe`).

- **Q4 — Endpoint d'upload unifié back, ou appel des endpoints existants par type ?**
  Reco : **appeler les endpoints existants par type** (aucun back à écrire pour v1). Le front route
  selon le type choisi.

- **Q5 — Droits : qui peut importer (rôle) ?**
  Reco : **même règle que les actions écrivant déjà** (Recalculer/Purger). À confirmer : réservé
  ADMIN, ou tout utilisateur rattaché à la ville ? (les endpoints exigent aujourd'hui `city_id`.)

## Plan d'implémentation (après validation)

1. Front : composant `InvoiceImportDrawer` (sélecteur type + dropzone/input fichier + case
   `force_update` pour xlsx/csv) ; activer le bouton `497`.
2. Front API client : brancher les 3 endpoints (xlsx / edf-csv / gas) + affichage compte-rendu
   (créées / doublons / erreurs) depuis la réponse batch.
3. Rafraîchir la table factures après import réussi.
4. Tests : `npx tsc -b` (front) ; pas de nouveau back → pas de nouveau pytest v1 (sauf ajustement).
5. Validation **staging** (base séparée) avant toute idée de prod.
