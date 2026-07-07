# Cadrage — UI d'import de factures (`/refonte-v1/factures`)

> Doc « fil du dev » — 2026-07-07. Chantier à prévoir. Rendre fonctionnel le bouton **« Importer des
> factures »** (aujourd'hui désactivé/placeholder) de la page factures V1.

## 1. Existant (vérifié)
- Front : `/refonte-v1/factures` = `features/invoices/InvoicesDecisionPageV1.tsx` — table **unifiée**
  (CPE DALKIA + énergie), décisions, contrôles, actions (Purger doublons, Recalculer). Le bouton
  « Importer des factures » est un **placeholder** : pas d'action, désactivé (style ghost).
- Back : les **parseurs existent déjà**, mais chacun a son entrée :
  - énergie ENGIE : parser xlsx (`invoice_parsers/engie_xlsx`) ;
  - énergie EDF : `services/edf_csv_import.import_edf_csv` (CSV) ;
  - gaz TotalEnergies : import dédié ;
  - DALKIA (CPE) : `pages/CpeDalkiaImportPage` (référentiel + factures P3, etc.).
- Il n'y a **pas d'UI d'upload unifiée** dans la refonte factures.

## 2. Cible (proposée)
Un **point d'entrée d'upload** depuis la page factures qui :
1. accepte un fichier, détecte le **fournisseur/format** (ou l'utilisateur le choisit), route vers le bon
   parseur, affiche le **compte-rendu** (créées / doublons / erreurs) — comme le renvoient déjà les
   services d'import.

## 3. Questions à trancher (avant de coder)
- Q1 — **Tiroir d'upload** dans la page, ou **page d'import dédiée** ?
- Q2 — **Un point multi-format** (détection auto) ou **choix explicite** du fournisseur/type ?
- Q3 — Quels formats **en premier** (ENGIE xlsx / EDF csv / gaz / DALKIA) ?
- Q4 — Faut-il un **endpoint d'upload unifié** back, ou on appelle les endpoints existants par type ?
- Q5 — Droits : qui peut importer (rôle) ?

## 4. Note
Les imports touchent des **écritures** (création de factures). Valider sur **staging** (base séparée) avant
prod, et **idempotence** (dédoublonnage par n° de facture) déjà en place côté services.
