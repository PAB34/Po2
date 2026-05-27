# Checkpoint dev CPE DALKIA — 2026-05-27

## État déployé

Commits poussés sur `main` et déployés OVH :

- `cc98b23` — `feat(cpe): add DALKIA finance reference`
- `146d5a7` — `feat(cpe): export DALKIA finance liaison`
- `391f0a0` — `feat(cpe): control DALKIA P3 revisions`
- `83fb7f0` — `feat(cpe): control DALKIA P2 revisions`

GitHub Actions vérifiés :

- CI : succès
- Deploy : succès
- Le workflow `.devcontainer/devcontainer.json` est séparé du déploiement applicatif et peut rester hors sujet.

## Fonctionnel disponible dans `/cpe`

Onglet **Référentiel finance** :

- import de `analyse_codification_dalkia.xlsx`
- stockage/édition des sites de codification finance
- stockage des règles `marché / service / poste facturé → nature comptable`
- import d'un export finances DALKIA XLSX
- archivage des lots, factures et lignes
- statut facture : `a_controler`, `valide`, `refuse`, `conteste`
- export XLSX d'une fiche liaison finance par facture
- saisie des indices trimestriels `ICHT_IME`, `FSD2`, `BT40`
- recalcul des contrôles de révision P2 et P3/P3.4

## Tables principales ajoutées

- `cpe_accounting_site_mappings`
- `cpe_accounting_nature_rules`
- `cpe_finance_import_batches`
- `cpe_finance_invoices`
- `cpe_finance_lines`
- `cpe_revision_indices`
- `cpe_finance_controls`

Migrations :

- `0024_add_cpe_finance_accounting.py`
- `0025_add_cpe_revision_controls.py`
- `0026_add_cpe_control_fsd2.py`

## Contrôles déjà codés

### Révision P2

Formule :

```text
P2 = P20 × (0,15 + 0,70 × ICHT-IME/141,4 + 0,15 × FSD2/169,8)
```

Pré-requis :

- ligne DALKIA avec `MARCHÉ = P2`
- `PRIX DE BASE`
- `PRIX OU FORFAIT RÉVISÉ`
- indices `ICHT_IME` et `FSD2` pour le trimestre de fin de période

### Révision P3 / P3.4

Formule confirmée par la mise au point OUV11 :

```text
P3 = P30 × (0,15 + 0,30 × ICHT-IME/141,4 + 0,55 × BT40/128,4)
```

Pré-requis :

- ligne DALKIA avec `MARCHÉ = P3`
- `PRIX DE BASE`
- `PRIX OU FORFAIT RÉVISÉ`
- indices `ICHT_IME` et `BT40` pour le trimestre de fin de période

## À tester manuellement

1. Aller sur `https://patrimoineaucarre.com/cpe`
2. Ouvrir **Référentiel finance**
3. Importer `saas/energie/DALKIA/COMPTABILITE/analyse_codification_dalkia.xlsx`
4. Saisir les indices nécessaires pour l'exercice/trimestre testé
5. Importer `saas/energie/DALKIA/COMPTABILITE/export_finances-20260527_1055.xlsx`
6. Sur une facture récente, cliquer **Contrôle revisions**
7. Vérifier le résumé `ok / error / blocked`
8. Cliquer **Export XLSX** et vérifier la fiche liaison

## Limites connues

- Les contrôles P2/P3 ne vérifient que la formule de révision du prix.
- Les contrôles ne valident pas encore la fréquence de facturation, l'exigibilité, les livrables ou les pièces de preuve.
- Les lignes DALKIA sans code site explicite peuvent nécessiter un mapping complémentaire `libellé DALKIA → site`.
- Les anciennes lignes importées avant les colonnes `base_price` / `revised_price` peuvent encore être contrôlées via `raw_json`, mais une réimportation propre est préférable.
- Les indices sont saisis manuellement pour l'instant.

## Prochain chantier recommandé

### 1. P2.4

Objectif :

- contrôler que le P2.4 est facturé annuellement ;
- appliquer 100% si objectifs atteints ;
- appliquer 50% si objectifs non atteints ;
- rattacher la décision aux résultats de performance énergétique déjà calculés.

À clarifier dans les pièces :

- libellés exacts DALKIA des lignes P2.4 ;
- période d'exigibilité ;
- preuve attendue avant validation ;
- articulation avec l'intéressement/pénalité énergétique.

### 2. P1

Objectif :

- contrôler les acomptes trimestriels ;
- contrôler le décompte définitif ;
- rapprocher quantités gaz, prix OS3 et éventuelles preuves GRDF.

### 3. Écran détail facture

Objectif :

- ouvrir une facture DALKIA ;
- voir les lignes ;
- voir les contrôles ;
- corriger les rattachements ;
- saisir une justification ;
- valider/refuser proprement.

