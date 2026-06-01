# Référentiel contractuel DALKIA — Import Excel et rattachements plateforme

tags: #CPE #DALKIA #référentiel #import #architecture #données

> Statut : ✅ Import opérationnel (commit `1428f4f` + fix `d10ea95`)  
> Date : 2026-06-01  
> Lien implementation : [[11-Implémentation-Po2]]

---

## 1. Contexte

Le fichier contractuel DALKIA (`01_24BT039_L1_AE_ANNEXES_OFFRE_FINALE.xlsx` et `L2`) est le **document de référence unique** du marché CPE Ville. Il est mis à jour à chaque avenant (entrée/sortie de sites, révision de cibles) et contient les montants contractuels, les cibles de consommation, et les travaux planifiés sur toute la durée du marché (2025-2033).

La page `/cpe/dalkia-import` permet d'importer ce fichier en base (tables `cpe_dalkia_ref_*`) pour que les fonctionnalités de contrôle puissent s'appuyer sur ces données de référence.

---

## 2. Données importées vs fonctionnalités existantes — Mapping complet

### 2.1 Périmètre des sites (`cpe_dalkia_ref_sites`)

| Colonne importée | Valeur exemple | Connecté à | Statut |
|-----------------|----------------|------------|--------|
| `code_site` | `VDS-ENS 01` | `cpe_sites.code_site` | ⚠️ Tables parallèles — pas de FK |
| `nom_batiment` | `Maternelle AGNES VARDA` | `cpe_sites.nom_site` | ⚠️ Non synchronisé |
| `lot` | 1 (ou 2) | Non modélisé dans cpe_sites | ❌ Absent |
| `entite` | `Lot 1` | Non modélisé | ❌ Absent |

**Situation actuelle** : `cpe_sites` est peuplé via un script seed (`seed_cpe_sites.py`) avec 65 sites saisis manuellement. L'import DALKIA identifie 72 sites Lot 1 + 4 sites Lot 2. Des sites du seed peuvent manquer dans le fichier DALKIA (périmètre partiel) ou apparaître sous un code différent.

**Action à implémenter** :
- Endpoint `POST /api/cpe/dalkia-ref/imports/{id}/sync-sites` qui aligne `cpe_sites` (nom, lot, actif) depuis l'import actif, en utilisant `code_site` comme clé de jointure.
- Ajout colonne `lot` (Integer, nullable) sur `cpe_sites` pour distinguer Lot 1 / Lot 2 dans les filtres.

---

### 2.2 P2 (maintenance) et P3 (travaux programmés) (`cpe_dalkia_ref_p2p3`)

| Colonne importée | Valeur exemple (site ENS02, 2026) | Connecté à | Statut |
|-----------------|-----------------------------------|------------|--------|
| `p2_total_ht` | 4 785 € | `cpe_contract_references.annual_amount_ht` | ⚠️ Non connecté automatiquement |
| `p3_total_ht` | 18 429 € | `cpe_contract_references.annual_amount_ht` | ⚠️ Non connecté automatiquement |
| `p2_1_ht` | 4 283 € | — (sous-poste P2.1) | ❌ Non stocké dans references |
| `p3_4_ht` | travaux obligatoires (NULL = S.O.) | — | ❌ Non utilisé |
| `period_year` | 2026 | `cpe_contract_references.year` | ⚠️ |

**Situation actuelle** : `cpe_contract_references` est un référentiel éditable (Codex) pour stocker des montants contractuels par `(city_id, contract_code, reference_kind, year, market, billed_item)`. Il est actuellement rempli manuellement.

Le contrôle finance P2/P3 (`cpe_finance_controls`) compare chaque ligne facturée au montant attendu. Si `cpe_contract_references` n'est pas peuplé, le contrôle reste `blocked`.

**Action à implémenter** :
- Endpoint `POST /api/cpe/dalkia-ref/imports/{id}/sync-contract-references` qui, pour chaque site × année, crée/met à jour des `CpeContractReference` avec :
  - `contract_code` = lot contractuel (ex : `C00190116O` pour Lot 1)
  - `reference_kind` = `P2_site` ou `P3_site`
  - `billed_item` = `code_site`
  - `year` = période (2025 partiel, 2026, …)
  - `annual_amount_ht` = `p2_total_ht` ou `p3_total_ht`
  - `installment_count` = 4 (acomptes trimestriels)
  - `tolerance_pct` = 1 %
- Cela permettrait aux contrôles finance de comparer **poste par poste et site par site** les factures DALKIA aux montants contractuels.

---

### 2.3 Cibles de consommation GAZ et ELEC (`cpe_dalkia_ref_cibles`)

| Colonne importée | Valeur exemple (ENS02, GAZ, 2026) | Connecté à | Statut |
|-----------------|-----------------------------------|------------|--------|
| `qt_global_mwhpci` | 103,5 MWh | `cpe_sites.nb_mwh_pci` | ⚠️ Statique vs multi-années |
| `nb_mwhpci` | 103,5 MWh | `cpe_sites.nb_mwh_pci` | Même valeur |
| `dju_reference` | 1 426 | `cpe_sites.dju_reference` | ✅ Cohérent (fixe contractuel) |
| `q_ecs` | 84 (kWh/m³) | `cpe_sites.q_ecs_mwh_pci_per_m3` | ⚠️ Non synchronisé |
| `qt_global_mwhpci` (fluid=ELEC) | 33,5 MWh | `cpe_sites.cible_elec_mwh` | ⚠️ Non synchronisé |
| `period_year` | 2027, 2028, … | — | ❌ Non modélisé (NB annuel variable) |

**Situation actuelle** : `cpe_sites.nb_mwh_pci` est un **scalaire unique** (le NB contractuel). Or le contrat prévoit des NB différents chaque année : les travaux APE réduisent les cibles à partir de l'année de leur réalisation (ex. ENS08 : NB 2026 = 56,1 MWh → NB 2028 = ~18 MWh après PAC). Le moteur d'intéressement utilise toujours le NB de `cpe_sites`, donc il calcule mal les exercices post-APE si ce champ n'est pas mis à jour manuellement.

**Action critique à implémenter** :
- **Nouveau modèle** `CpeSiteNbAnnuel` (ou colonne JSON dans `cpe_sites`) pour stocker le NB contractuel **par année** :
  ```
  (cpe_site_id, annee) → nb_mwh_pci, q_ecs_mwh_pci_per_m3, cible_elec_mwh
  ```
- Alimenté automatiquement depuis `cpe_dalkia_ref_cibles` lors du sync.
- La fonction `calculer_resultat_site()` lit d'abord `CpeSiteNbAnnuel` pour l'année demandée, puis `cpe_sites.nb_mwh_pci` en fallback.

**Intérim acceptable** : jusqu'à cette implémentation, mettre à jour `cpe_sites.nb_mwh_pci` = NB de l'année en cours via le sync (valeur 2026 ou 2027 selon l'exercice calculé).

---

### 2.4 Fourniture gaz P1 (`cpe_dalkia_ref_p1_gaz`)

| Colonne importée | Valeur exemple (ENS02, 2026) | Connecté à | Statut |
|-----------------|------------------------------|------------|--------|
| `pce` | `24349204040145` | `cpe_sites.pce` | ⚠️ Non synchronisé |
| `type_tarif` | `T2` | `cpe_sites.tarif` | ⚠️ Non synchronisé |
| `prix_unitaire_ht` | 92,46 €/MWhPCS | `cpe_prix_gaz.pu_eur_mwh_pci` | ⚠️ Conversion PCS→PCI à vérifier |
| `p10_total_ht` | 11 697 € (pour ENS02, 2026) | — | ❌ Non utilisé |
| `p10_fixe_ht` | 1 064 € (ATRD+CTA) | — | ❌ Non utilisé |
| SUM p10_total_ht Lot 1 2026 | ~341 293 € HT | Constante hardcodée dans service | ⚠️ Hardcodé |

**Situation actuelle** : le contrôle P1 acompte compare le total des lignes P1 importées au montant de référence **317 774 € HT** (NB : voir le doc, le montant est issu du RECAP MARCHE). Cette référence est actuellement une constante dans le code service. Cela fonctionnait pour une seule année mais ne s'adapte pas aux révisions annuelles.

**Vérification prix** : `cpe_prix_gaz` stocke T2 = 82,13 €/MWhPCI pour 2026-2030 (OS N°3). L'import indique `prix_unitaire_ht = 92,46 €/MWhPCS`. Conversion : 92,46 / 1,1068 = 83,50 €/MWhPCI. L'écart (~1,37 €) s'explique par la marge d'exploitation (10,3%) incluse dans le prix DALKIA. Ces deux valeurs servent des usages différents :
- `cpe_prix_gaz.pu_eur_mwh_pci` → calcul intéressement (Pu net de fourniture)
- `cpe_dalkia_ref_p1_gaz.prix_unitaire_ht` → contrôle des factures P1 DALKIA

**Actions à implémenter** :
- Endpoint `POST /api/cpe/dalkia-ref/imports/{id}/sync-p1-contract-reference` qui remplace la constante hardcodée par :
  - `SUM(p10_total_ht)` par lot et par année → `cpe_contract_references` (reference_kind=`P1_gaz_lot`, year, annual_amount_ht)
  - Règle d'acompte : 1/4 aux échéances 31/03, 30/06, 30/09 (règle = `1/4 du P1 annuel révisé`)
- Validation PCE : `cpe_dalkia_ref_p1_gaz.pce` vs `cpe_sites.pce` — signaler les divergences.

**Total P1 Lot 1 par année** (calculable depuis l'import) :
| Année | Total P1 HT (somme p10_total_ht) |
|-------|----------------------------------|
| 2025 (partiel) | ~108 885 € |
| 2026 | ~317 775 € |
| 2027 | ~317 775 € |
| 2028 | ~203 625 € |
| 2029→2032 | ~203 625 €/an |
| 2033 (partiel) | ~141 984 € |

> La baisse à partir de 2028 correspond aux sites sortant après travaux (ENS08 PAC = 2027).

---

### 2.5 Travaux APE (`cpe_dalkia_ref_ape`)

| Colonne importée | Valeur exemple (ENS02) | Connecté à | Statut |
|-----------------|------------------------|------------|--------|
| `description_ape` | `Installation de circulateurs à débit variable` | — | ❌ Aucun modèle |
| `annee_achevement` | 2026 | — | ❌ Aucun modèle |
| `montant_ape_ht` | 9 815 € | — | ❌ Aucun modèle |
| `gain_energetique_mwhpci` | 6,37 MWh | `cpe_sites.nb_mwh_pci` (delta) | ❌ Non connecté |
| `situation_nouvelle_mwhpci` | NB après travaux | `cpe_dalkia_ref_cibles.qt_global` (année suivante) | ✅ Cohérent |
| `annee_engagement_nouvelle_cible` | 2027 | → nouveau NB à partir de 2027 | ❌ Non connecté |
| `cee_eur` | 1 132 € | — | ❌ Non tracé |
| `emission_co2_evitee` | 6,72 Teq CO₂/an | — | ❌ Non tracé |

**Situation actuelle** : aucun modèle ni fonctionnalité de suivi APE. Les travaux APE sont contractuellement obligatoires ; DALKIA doit les réaliser aux dates prévues et fournir les justificatifs.

**Actions à implémenter (Phase 2)** :
- Nouveau modèle `CpeApeSuivi` (code_site, description, annee_prevue, annee_reelle, statut: `prevu / en_cours / realise / retard`, montant_ht, gain_effectif_mwhpci, justificatif_pdf).
- Alimenté depuis `cpe_dalkia_ref_ape` lors du sync initial.
- Lien avec `cpe_sites` pour mise à jour automatique du NB quand `statut=realise`.
- Vue dans `/cpe` → onglet "Travaux APE" : tableau des travaux prévus/réalisés avec statut, écart de date, impact cible.

---

## 3. Schéma des connexions

```
cpe_dalkia_ref_imports  (1 import actif par lot)
    │
    ├─ cpe_dalkia_ref_sites ─────────────→ cpe_sites (sync par code_site)
    │                                            │
    ├─ cpe_dalkia_ref_cibles (GAZ/ELEC) ────────┤→ cpe_sites.nb_mwh_pci (sync annuel)
    │                                            │  cpe_resultats_annuels.nb
    │
    ├─ cpe_dalkia_ref_p2p3 ──────────────→ cpe_contract_references
    │         (P2 + P3 par site × année)          (reference_kind P2_site / P3_site)
    │                                                      │
    │                                            cpe_finance_controls
    │                                            (contrôle révision P2/P3)
    │
    ├─ cpe_dalkia_ref_p1_gaz ───────────→ cpe_contract_references
    │         (P1 lot × année)                    (reference_kind P1_gaz_lot)
    │                                                      │
    │                                            cpe_finance_controls
    │                                            (contrôle acompte P1 gaz)
    │
    └─ cpe_dalkia_ref_ape ───────────────→ [À créer] CpeApeSuivi
              (travaux × site)                        │
                                               cpe_sites.nb_mwh_pci (après réalisation)
```

---

## 4. État des connexions — Tableau récapitulatif

| Données DALKIA | Table cible actuelle | Connexion | Priorité |
|---------------|---------------------|-----------|----------|
| Sites (code, nom, lot) | `cpe_sites` | ⚠️ Sync manuel (seed) | 🔴 Haute |
| NB gaz annuel par site | `cpe_sites.nb_mwh_pci` | ⚠️ Statique (seed) | 🔴 Haute |
| NB gaz par site × année | — | ❌ Absent (modèle à créer) | 🔴 Haute |
| P2 total par site × année | `cpe_contract_references` | ❌ Non alimenté auto | 🔴 Haute |
| P3 total par site × année | `cpe_contract_references` | ❌ Non alimenté auto | 🔴 Haute |
| P1 total lot × année | `cpe_contract_references` | ⚠️ Hardcodé dans service | 🟠 Moyenne |
| PCE / type tarif | `cpe_sites.pce / tarif` | ⚠️ Seed manuel | 🟠 Moyenne |
| Prix unitaire gaz (PCS) | `cpe_prix_gaz` | ⚠️ Usage différent | ℹ️ Info |
| Cibles ELEC | `cpe_sites.cible_elec_mwh` | ⚠️ Statique (seed) | 🟡 Basse |
| DJU référence | `cpe_sites.dju_reference` | ✅ Cohérent (1 426) | ✅ OK |
| Travaux APE | — | ❌ Absent | 🟠 Moyenne |

---

## 5. Plan d'implémentation recommandé

### Phase immédiate (fonctionnel maintenant)
Les données sont **stockées** dans `cpe_dalkia_ref_*` et **consultables** via l'API. La page import montre les comptages et les 5 premiers sites. Il n'y a pas encore de synchronisation automatique vers les tables CPE opérationnelles.

### Phase A — Sync sites + NB (priorité haute)
1. Créer `cpe_site_nb_annuels` : `(cpe_site_id, annee) → nb_mwh_pci, q_ecs, cible_elec_mwh`
2. Endpoint `POST /api/cpe/dalkia-ref/imports/{id}/sync-cibles` :
   - Lit `cpe_dalkia_ref_cibles` (fluid=GAZ) pour l'import actif
   - Crée/met à jour `cpe_site_nb_annuels` par site × année
   - Met aussi à jour `cpe_sites.nb_mwh_pci` avec la valeur de l'année courante (fallback)
3. Modifier `calculer_resultat_site()` pour lire `cpe_site_nb_annuels` en priorité
4. **Impact immédiat** : les calculs d'intéressement 2027, 2028, etc. utiliseront les bonnes cibles contractuelles (réduites après APE) au lieu d'une valeur fixe

### Phase B — Sync références P2/P3
1. Endpoint `POST /api/cpe/dalkia-ref/imports/{id}/sync-contract-references` :
   - Pour chaque site × année de `cpe_dalkia_ref_p2p3` : upsert `cpe_contract_references`
   - reference_kind = `P2_site` / `P3_site`, billed_item = code_site, annual_amount_ht = total
2. Adapter les contrôles finance pour utiliser ces références par site (au lieu d'un seul total lot)
3. **Impact** : le contrôle P2/P3 peut signaler non plus "montant global incorrect" mais "site ENS02 : P3 facturé 21 200€ vs contractuel 18 429€"

### Phase C — Sync P1 gaz (remplacement hardcoded)
1. Endpoint `POST /api/cpe/dalkia-ref/imports/{id}/sync-p1-reference` :
   - Calcule `SUM(p10_total_ht)` par lot × année depuis `cpe_dalkia_ref_p1_gaz`
   - Upsert `cpe_contract_references` (reference_kind=`P1_gaz_lot`, billed_item=lot_code, annual_amount_ht=total)
2. Modifier le service de contrôle P1 pour lire la référence en base au lieu de la constante
3. **Impact** : le montant de référence P1 s'adapte automatiquement aux avenants (nouveaux sites, révisions tarifaires)

### Phase D — Suivi travaux APE
1. Créer `cpe_ape_suivi` avec les colonnes de `cpe_dalkia_ref_ape` + statut/date_réelle
2. Sync initial depuis l'import DALKIA
3. Vue frontend `/cpe` → onglet "Travaux APE"
4. **Impact** : traçabilité des obligations contractuelles DALKIA, alertes si travaux en retard

---

## 6. Avenants — Workflow de mise à jour

Quand DALKIA envoie un avenant (entrée/sortie de site, révision de cible, modification APE) :

1. **Importer** le nouveau fichier dans `/cpe/dalkia-import` (Lot 1 ou Lot 2)
2. L'ancien import est **désactivé** (is_active=False) mais conservé pour audit
3. **Vérifier** le rapport de contrôle : nb_sites avant/après, warnings, aperçu
4. **Confirmer** l'import → nouvelles données dans `cpe_dalkia_ref_*`
5. **Lancer les syncs** (A, B, C ci-dessus) pour propager les changements vers les tables opérationnelles
6. **Recalculer** les bilans CPE pour les exercices affectés

L'historique des imports permet de retrouver à quelle version contractuelle correspond chaque calcul.

---

## 7. Connexion avec le patrimoine (bâtiments)

Les codes sites DALKIA (`VDS-ENS 01`, `VDS-SPORT 02.01`, etc.) correspondent aux bâtiments de la base patrimoniale. La connexion possible :

| Table CPE | Table patrimoine | Lien | Statut |
|-----------|-----------------|------|--------|
| `cpe_sites.code_site` | `buildings.nom_batiment` ou `sites.nom_site` | Lien sémantique manuel | ❌ Pas de FK |
| `cpe_sites` | `buildings` | Futur : `building_id` sur `cpe_sites` | ❌ À créer |

**Valeur ajoutée** : si le lien est créé, depuis la fiche bâtiment (`/buildings/list`) on pourrait voir directement :
- Les cibles NB gaz contractuelles par année
- Le P2/P3 annuel contractuel
- Les travaux APE prévus et leur statut

Ce rapprochement est documenté dans [[008-referentiel-patrimoine-et-rapprochements]].

---

## 8. Liens

- [[10-Roadmap-Po2]] — phases et priorités
- [[11-Implémentation-Po2]] — état des tables CPE existantes
- [[13-Export-finances-DALKIA]] — format des factures DALKIA
- [[15-Formules-indices-et-travaux-P3]] — formules de révision P2/P3
- [[16-Pilotage-financier-et-controle-global]] — vue d'ensemble des contrôles
- [[03-Cibles-et-intéressement]] — formule NB/N'B/NC
- [[04-Cibles-par-site]] — NB et qECS par site (données historiques seed)
