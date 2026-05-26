# 2026-05-26 - Facturation ENGIE XLSX et controle BPU

> IA : Codex GPT-5
> Duree approximative : session longue multi-etapes
> Precedentes sessions : `[[Sessions/2026-05-22 — Import XLSX ENGIE]]`, `[[Sessions/2026-05-22 — Rapport fournisseur agrégat et recalcul BPU]]`

## Objectif de la session

Continuer le chantier `PO2-FACT-001` : fiabiliser la facturation ENGIE sur export XLSX, les filtres de revue, le rapport fournisseur, le suivi mensuel de facturation et le controle BPU.

## Ce qui a ete fait

### Import XLSX ENGIE et stabilite

- Commit `22c7ff7` : import XLSX lance en arriere-plan pour eviter les blocages UI.
- Commit `3eba12c` : acceleration du parser XLSX ENGIE.
- Commit `01b94b1` : bascule UI vers import XLSX-only pour les nouveaux imports et upsert avec preservation des decisions utilisateur.
- Le flux cible est maintenant : export ENGIE `MesFactures_*.xlsx` -> parser `engie_xlsx.py` -> un `EnergyInvoiceImport` par bordereau -> memes controles BPU/TURPE/ENEDIS que les PDF.

### Rapport fournisseur et filtres

- Commit `b899ad3` : les points BPU non chiffrables restent inclus dans le rapport au lieu de produire un rapport vide.
- Commit `a18ef4c` : la categorie `Prix contractuels` et les types BPU restent visibles dans les filtres meme si les factures courantes n'ont plus d'ecart BPU actif.
- Types BPU forces dans l'UI :
  - `BPU_PRICE_MISMATCH` : ecart prix facture / BPU.
  - `BPU_TARIFF_POSTE_INCONSISTENCY` : incoherence tarif/poste BPU.
  - `BPU_REFERENCE_MISSING` : reference BPU manquante.
  - `BPU_PRICE_MISSING` : prix BPU manquant.

### Suivi mensuel de facturation

- Commit `e0b69ef` : endpoint mensuel consommation facturee ENGIE vs releve ENEDIS.
- Commit `6a1e1f2` : ajout au graphique de tete `/energie/factures` du nombre de factures et du nombre de PRM factures par mois.
- Le graphique sert maintenant aussi a reperer des trous potentiels de facturation : mois avec releves ENEDIS mais aucune facture rattachee avec les filtres actifs.

### Matching BPU XLSX

- Commit `56a1843` : matching des tarifs ENGIE XLSX avec le BPU 2026 Lot 1.
- Commit `9e36f19` : correction importante pour les C5 libelles "4 plages" mais factures uniquement en `BASE` :
  - version `CU` + uniquement `BASE` => `CU/base` ;
  - ne pas chercher `CU4/base`, qui n'existe pas dans le BPU.

## Controle tarifaire direct effectue

Fichier controle :

- `saas/energie/ENGIE/EXPORTS/MesFactures_20260522150740.xlsx`

BPU controle :

- `saas/energie/HERAULT ENERGIE/BPU_2026_Lots_1_2_et_7.xlsx`

Resultat contre Lot 1 - Batiment :

| Indicateur | Valeur |
|---|---:|
| Lignes tarifaires candidates | 5368 |
| Lignes OK | 5355 |
| Ecarts potentiels | 13 |
| References BPU manquantes | 0 |
| Prix BPU manquants | 0 |

Contre-epreuve Lot 2 - EP :

- 5323 ecarts sur 5368 lignes.
- Conclusion : le fichier analyse releve bien du Lot 1 - Batiment, pas du Lot 2 - EP.

Lecture metier :

- Les 13 ecarts restants sont uniquement sur `Fourniture/base`.
- 10 lignes `CU/base` ont un impact estime tres faible, souvent `0,00 EUR HT`, probablement lie a l'arrondi quand le prix facture est reconstruit depuis montant / quantite.
- 3 lignes `LU/base` concernent `BORNE FIXE MARCHE DU BARROU`, avec impacts estimes 0,04 / 0,14 / 0,23 EUR HT. A relire apres reimport force dans l'application.

Artefacts locaux generes mais non versionnes car `saas/energie/ENGIE/` est ignore :

- `saas/energie/ENGIE/RAPPORTS/rapport_ecarts_tarification_bpu_2026.md`
- `saas/energie/ENGIE/RAPPORTS/rapport_ecarts_tarification_bpu_2026_detail_lignes.csv`
- `saas/energie/ENGIE/RAPPORTS/rapport_ecarts_tarification_bpu_2026_anomalies.csv`

## Documentation mise a jour

- `docs/Backlog.md` : `PO2-FACT-001` enrichi avec l'etat XLSX/BPU.
- `docs/04-Etat-actuel-du-dev.md` : ajout de la mise a jour facturation ENGIE du 2026-05-26.
- `docs/Modules/Energie-Facturation.md` : note de consolidation avec les regles de matching et les resultats du controle direct.
- `saas/energie/HERAULT ENERGIE/SYNTHESE_FACTURATION.md` : synthese contractuelle frequence/delais/penalites/controles.

## Etat CI / prod

- CI du commit `a18ef4c` : succes.
- Les deploys OVH ont echoue au moment de la session sur un probleme externe Docker Hub :
  - `TLS handshake timeout` lors du pull metadata `nginx`, `python`, `node`.
- L'API prod restait disponible : `/api/health` => `ok`.
- Le commit `9e36f19` a ete pousse apres la correction C5 base seule ; CI/Deploy ont ete lances mais pas encore confirmes dans cette note.

## Handoff suivant

Priorite 1 - Deployer et reanalyser le XLSX :

- Relancer/attendre le workflow Deploy GitHub Actions tant que Docker Hub ne repond pas depuis le VPS.
- Apres deploy reussi, ouvrir `/energie/factures`.
- Reimporter `MesFactures_20260522150740.xlsx` avec `Forcer la mise a jour des bordereaux deja importes`.
- Verifier que les rapports stockes en BDD sont recalcules.

Priorite 2 - Valider les filtres et le rapport BPU :

- Dans `Filtrer les factures`, verifier que `Categorie de probleme = Prix contractuels` est toujours visible.
- Dans `Type de probleme`, verifier la presence de `Ecart prix facture / BPU` et `Incoherence tarif/poste BPU`.
- Filtrer sur `Prix contractuels`, puis editer le rapport.
- Verifier que le rapport affiche les ecarts chiffrables et le recalcul BPU.

Priorite 3 - Relire les 13 ecarts restants :

- Regarder si les 13 ecarts du rapport local remontent encore apres reimport.
- Les faibles impacts a 0,00 EUR HT peuvent etre classes comme arrondis si la facture ne fournit pas de prix unitaire explicite fiable.
- Les 3 lignes `BORNE FIXE MARCHE DU BARROU` en `LU/base` meritent une verification metier.

## Pour la prochaine IA - entree en matiere

```text
J'ai lu :
- docs/00-Index.md
- docs/Backlog.md
- docs/04-Etat-actuel-du-dev.md
- docs/Modules/Energie-Facturation.md
- docs/Sessions/2026-05-26 - Facturation ENGIE XLSX et controle BPU.md

Je sais que le poste utilisateur est verrouille entreprise : je ne demanderai aucune installation locale.
Je comprends que la priorite 1 est de faire passer le deploy OVH puis de reimporter le XLSX ENGIE avec force update.
Je propose de commencer par verifier GitHub Actions Deploy puis `/api/health`.
```
