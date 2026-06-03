# Session 2026-06-03 — CPE contrôle factures : correction TVA + décomposition acompte trimestriel

## Contexte
Sur `/cpe` > `Contrôle factures`, l'export XLSX de la **fiche de liaison finance** (action de contrôle global
sur une facture, route `/api/cpe/finances/invoices/{id}/liaison.xlsx`) présentait deux problèmes signalés
par l'utilisateur :

1. La colonne **TVA** affichait `2000%` au lieu de `20%`.
2. Les colonnes `Prix base` / `Prix revisé` étaient utiles mais il manquait, au niveau de **l'acompte
   trimestriel**, une décomposition : montant HT avec révision, acompte hors révision, et montant de la révision.

Fichier de référence utilisateur : `fiche-liaison-dalkia-0001E2604CFN7.xlsx` (type EC, sans prix de base).
Données analysées pour la décomposition : facture **0001E2604AYP5** (lignes P3.4 avec prix de base annuel).

## Diagnostic
- **TVA 2000%** : `vat_rate` est stocké en points de pourcentage (`20.0`, depuis `taux_de_tva`), mais la
  cellule utilisait le format `"0.00%"` qui multiplie par 100 → `2000.00%`.
- **Structure DALKIA confirmée** sur 0001E2604AYP5 :
  - `prix_de_base` = montant **annuel** de base du poste ;
  - `prix_ou_forfait_revise` = montant **annuel** révisé (= base × coef. de révision) ;
  - `montant_ht` = acompte de la période = révisé / 4 (trimestriel).
  - Exemple ligne 1 : base 722 → révisé 740,32 → HT 185,08 = 740,32 / 4. ✓

## Travaux livrés
Tout dans `saas/backend/app/services/cpe_accounting.py` :

1. Nouveau helper `_line_revision_breakdown(line)` : décompose `montant_ht` en
   `(acompte hors révision, montant de la révision)` via le ratio `montant_ht / prix_revise`
   appliqué au `prix_de_base`. Robuste au /4, aux prorata partiels et aux lignes en consommation.
2. `build_detailed_finance_liaison_workbook` (onglet « Lignes finance ») :
   - format TVA `"0.00%"` → `'0.00"%"'` (affiche `20.00%`) ;
   - renommage : `Prix base` → `Prix base annuel`, `Prix revise` → `Prix revise annuel`,
     `Montant HT` → `Montant HT (avec revision)` ;
   - 2 colonnes ajoutées : **Acompte hors revision** et **Revision appliquee** (format EUR) ;
   - largeurs + auto-filtre (`A1:AM`) mis à jour.

La fiche de liaison « simple » `build_finance_liaison_workbook` n'est branchée à aucune route (laissée telle quelle).

## Validation
- `python -m compileall app/services/cpe_accounting.py` OK.
- Suite CPE : 14 tests passent ; le seul échec `test_enriched_codification_matches_finance_export_lines`
  est **préexistant** (confirmé par `git stash` sur le code de base) et concerne l'import, pas l'export.
- Test bout-en-bout temporaire sur 0001E2604AYP5 (import codification + finances → génération XLSX) :
  - TVA = `0.00"%"` / valeur 20 ✓ ;
  - décomposition réconciliée : hors révision 167 400,50 + révision 4 247,96 = HT 171 648,46 ✓.

## Handoff suivant
1. Regénérer la fiche de liaison depuis `/cpe` > `Contrôle factures` et vérifier visuellement TVA + les
   3 colonnes de décomposition.
2. Éventuellement exposer la même décomposition dans l'UI (la page ne montre pas encore le détail par ligne)
   et/ou dans le rapport « contrôle global » (`build_finance_control_report_workbook`).
3. Étendre la décomposition aux contrôles P2/P3 (afficher écart sur l'acompte hors révision vs révision).
