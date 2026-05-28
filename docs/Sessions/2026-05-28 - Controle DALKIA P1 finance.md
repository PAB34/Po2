# 2026-05-28 - Controle DALKIA P1 finance

## Contexte

Le module `/cpe` doit d'abord maitriser le premier marche CPE DALKIA Ville, avant d'etendre le controle aux autres contrats visibles dans l'export finances DALKIA.

Point utilisateur important :
- le contrat `C00032657J` correspond au CREM Piscine Fonquerne et ne fait pas partie du marche cible actuel ;
- l'absence de site VDS/CCAS sur ce contrat est donc normale ;
- les formules de total facture peuvent differer sur ces contrats hors perimetre.

## Travaux realises

Commit pousse :

```text
add8d71 feat(cpe): control DALKIA P1 acompte scope
```

Travaux deja pousses dans la meme sequence CPE finance :

```text
695c0bd feat(cpe): clarify finance navigation
5b0ecbf feat(cpe): improve DALKIA finance exports
25e6bba feat(cpe): strengthen DALKIA invoice controls
2419f9d fix(cpe): show all archived DALKIA invoices
```

### Perimetre contrats

Ajout d'une distinction de controle :
- contrats CPE Ville cible : `C00190116O`, `C00190155J` ;
- contrats hors perimetre courant : CREM Piscine, thalassothermie, anciens marches, autres contrats DALKIA.

Effet :
- une ligne hors perimetre n'est plus bloquee uniquement parce qu'elle n'a pas de site finance VDS/CCAS ;
- les lignes du CPE Ville cible restent controlees strictement sur le rattachement site.

### Controle P1 gaz Lot 1

Controle ajoute : `p1_gaz_acompte_dpgf`.

Perimetre :
- contrat `C00190116O` ;
- marche `P1` ;
- postes inclus : `P1`, `ABT`, `CTA`, `CPB`, `LOCATION`, `STOCKAGE`, `TERME FIXE`.

Reference :
- DPGF Lot 1 2026, synthese `P1 gaz Rev Temp` ;
- total annuel 2026 = `341 293,06 EUR HT` ;
- acompte trimestriel attendu = `85 323,27 EUR HT`.

Regle :
- acomptes attendus aux 31/03, 30/06, 30/09 ;
- tolerance = `1%` ou `100 EUR` ;
- controle agrege sur toutes les lignes du lot importe avec meme contrat/periode/postes P1 gaz.

### Export finance

L'export XLSX fiche liaison est maintenant enrichi avec :
- `Synthese` ;
- `Lignes finance` ;
- `Controles` ;
- `Donnees source`.

Le type de facture est conserve pour le service finance :
- `AC` : acompte ;
- `AJ` : ajustement / avoir ;
- `DE` : facture definitive ;
- `EC` : echeance / facture courante ;
- `RE` : regularisation.

## Validation

- Compilation backend : `python -m compileall app` OK.
- Tests unitaires locaux non executes : environnement Codex sans `pytest`/`sqlalchemy` installes.
- GitHub Actions `CI` : succes sur `add8d71`.
- GitHub Actions `Deploy` : succes sur `add8d71`.
- Healthcheck prod : `https://patrimoineaucarre.com/api/health` retourne `status: ok`.

## Fichiers touches

- `saas/backend/app/services/cpe_accounting.py`
- `saas/backend/tests/test_cpe_accounting_import.py`
- `docs/energie/CPE-DALKIA/13-Export-finances-DALKIA.md`
- `docs/energie/CPE-DALKIA/11-Implémentation-Po2.md`
- `docs/04-Etat-actuel-du-dev.md`
- `docs/Backlog.md`

## Points d'attention

- Les donnees locales `saas/energie/DALKIA/` restent non suivies par Git.
- Deux fichiers sans rapport CPE restent modifies localement et n'ont pas ete touches dans ce chantier :
  - `saas/backend/app/api/routes/buildings.py`
  - `saas/backend/app/services/buildings.py`
- Le workflow `.devcontainer/devcontainer.json` etait encore en cours lors de la derniere verification, mais `CI` et `Deploy` etaient verts.

## Prochaines etapes

1. Reimporter dans `/cpe` la matrice `analyse_codification_dalkia_enrichie_par_code_contrat (1).xlsx`.
2. Supprimer/reprendre l'historique finance si necessaire, puis reimporter `export_finances-20260527_1055.xlsx`.
3. Relancer les controles sur les factures `C00190116O`.
4. Verifier l'acompte P1 gaz T1 2026 : attendu `85 323,27 EUR HT`.
5. Confirmer avec DALKIA le perimetre exact de `C00190155J` et ses regles de controle.
6. Sortir les references P1 DPGF des constantes code vers un referentiel editable en base.
7. Ajouter un ecran de reconciliation pour les lignes CPE Ville sans site rattache : code detecte, detail DALKIA, candidat site, statut.
8. Construire le controle P1 definitif : volumes GRDF/DALKIA, pieces fournisseur, prix gaz, decompte definitif, ecart acompte/solde.

## Handoff suivant

Reprendre par `PO2-CPE-001` dans `docs/Backlog.md`.

Priorite immediate : reimporter les donnees depuis `/cpe`, verifier une vraie facture `C00190116O`, puis transformer la reference P1 gaz DPGF en table editable plutot qu'en constante applicative.
