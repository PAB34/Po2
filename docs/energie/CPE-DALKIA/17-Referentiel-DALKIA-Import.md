# Référentiel contractuel DALKIA — Import Excel et rattachements plateforme

tags: #CPE #DALKIA #référentiel #import #architecture #données

> Statut : ✅ Import opérationnel + preview classifiée complète  
> Date : 2026-06-02  
> Commits : `1428f4f` (base) · `d10ea95` (fix cibles) · `4136225` (RECAP MARCHE) · dernier commit (preview classifiée)  
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

**✅ Implémenté (Phase A, 2026-06-02)** — approche retenue, plus simple que le plan initial :
- **Aucune nouvelle table.** La fonction `resolve_nb_for_year(db, site, annee)` (`services/cpe.py`)
  lit directement le NB de la cible GAZ dans `cpe_dalkia_ref_cibles` de l'**import DALKIA actif**
  pour `(code_site, period_year=annee)`, scopé par `city_id`.
- **Fallback** sur `cpe_sites.nb_mwh_pci` si aucune cible (pas d'import actif, site hors périmètre,
  ou NB nul/0) → comportement strictement identique à l'historique en l'absence de données DALKIA.
- Branchée dans `calculer_resultat_site()` (N'B, écart_pct, et `nb` persisté dans `cpe_resultats_annuels`)
  **et** dans `get_bilan_annuel()`. La colonne `cpe_resultats_annuels.nb` reflète désormais le NB
  réellement utilisé pour l'exercice (traçabilité).
- Couverte par `tests/test_cpe_nb_annuel.py` (6 cas : cible prioritaire, fallback année absente,
  import inactif ignoré, hors périmètre, scoping commune, NB nul/0). **6/6 verts.**

> ⚠️ **À vérifier sur données réelles** : la jointure se fait sur `code_site`. Si les codes de
> `cpe_sites` (seed) et de `cpe_dalkia_ref_cibles` (import) ne sont pas strictement identiques,
> le fallback s'active silencieusement (résultat = ancien comportement, pas d'erreur). Contrôler
> après le premier import qu'un échantillon de sites résout bien le NB DALKIA et non le fallback.

---

### 2.4 Fourniture gaz P1 (`cpe_dalkia_ref_p1_gaz`)

| Colonne importée | Valeur exemple (ENS02, 2026) | Connecté à | Statut |
|-----------------|------------------------------|------------|--------|
| `pce` | `24349204040145` | `cpe_sites.pce` | ⚠️ Non synchronisé |
| `type_tarif` | `T2` | `cpe_sites.tarif` | ⚠️ Non synchronisé |
| `prix_unitaire_ht` | 92,46 €/MWhPCS | `cpe_prix_gaz.pu_eur_mwh_pci` | ⚠️ Conversion PCS→PCI à vérifier |
| `p10_total_ht` | 11 697 € (pour ENS02, 2026) | — | ❌ Non utilisé |
| `p10_fixe_ht` | 1 064 € (ATRD+CTA) | — | ❌ Non utilisé |
| SUM p10_total_ht Lot 1 2026 (Annexe 6) | ≈ 317 775 € HT | `cpe_contract_references` (en base) | ⚠️ Écart avec le seed |

**Situation actuelle** (vérifiée contre le code, voir §9.3) : le contrôle P1 acompte ne lit **aucune constante hardcodée**. Il lit sa référence en base dans `cpe_contract_references` (kind=`p1_gaz_acompte`), valeur semée par la migration `0029` : **`annual_amount_ht = 341 293,06 € HT`**, `installment_count = 4`. Cette ligne est **éditable** depuis le module CPE — elle n'est juste pas encore alimentée automatiquement depuis l'import DALKIA. ⚠️ Cette valeur seed (341 293 €, issue de la DPGF) **diffère** de la somme P1 2026 parsée depuis l'Annexe 6 / RECAP MARCHE (≈ 317 775 €) : écart à réconcilier (voir §9.4).

**Vérification prix** : `cpe_prix_gaz` stocke T2 = 82,13 €/MWhPCI pour 2026-2030 (OS N°3). L'import indique `prix_unitaire_ht = 92,46 €/MWhPCS`. Conversion : 92,46 / 1,1068 = 83,50 €/MWhPCI. L'écart (~1,37 €) s'explique par la marge d'exploitation (10,3%) incluse dans le prix DALKIA. Ces deux valeurs servent des usages différents :
- `cpe_prix_gaz.pu_eur_mwh_pci` → calcul intéressement (Pu net de fourniture)
- `cpe_dalkia_ref_p1_gaz.prix_unitaire_ht` → contrôle des factures P1 DALKIA

**Actions à implémenter** :
- Endpoint `POST /api/cpe/dalkia-ref/imports/{id}/sync-p1-contract-reference` qui alimente (upsert) la référence en base avec :
  - `SUM(p10_total_ht)` par lot et par année → `cpe_contract_references` (reference_kind=`p1_gaz_acompte`, year, annual_amount_ht)
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

### Phase A — Sync NB par année ✅ FAIT (2026-06-02)
Implémentée par lecture directe (pas de table intermédiaire ni de sync à déclencher) :
`resolve_nb_for_year()` lit `cpe_dalkia_ref_cibles` (fluid=GAZ, import actif) avec fallback
`cpe_sites.nb_mwh_pci`, branchée dans `calculer_resultat_site()` et `get_bilan_annuel()`.
Tests : `tests/test_cpe_nb_annuel.py` (6/6). Détail : §2.3.
- **Impact** : les calculs d'intéressement 2027, 2028… utilisent désormais les cibles contractuelles
  réduites après APE, dès qu'un import DALKIA actif couvre le site (sinon fallback inchangé).
- **Reste à faire** : vérifier l'alignement des `code_site` (seed vs import) sur données réelles ;
  exposer le NB de l'année dans l'UI bilan pour rendre visible la valeur retenue.

### Phase B — Sync références P2/P3
1. Endpoint `POST /api/cpe/dalkia-ref/imports/{id}/sync-contract-references` :
   - Pour chaque site × année de `cpe_dalkia_ref_p2p3` : upsert `cpe_contract_references`
   - reference_kind = `P2_site` / `P3_site`, billed_item = code_site, annual_amount_ht = total
2. Adapter les contrôles finance pour utiliser ces références par site (au lieu d'un seul total lot)
3. **Impact** : le contrôle P2/P3 peut signaler non plus "montant global incorrect" mais "site ENS02 : P3 facturé 21 200€ vs contractuel 18 429€"

### Phase C — Sync P1 gaz (alimentation auto de la référence en base)
1. Endpoint `POST /api/cpe/dalkia-ref/imports/{id}/sync-p1-reference` :
   - Calcule `SUM(p10_total_ht)` par lot × année depuis `cpe_dalkia_ref_p1_gaz` (ou lit `cpe_dalkia_ref_recap` metric `p1_total_ht`)
   - Upsert `cpe_contract_references` (reference_kind=`p1_gaz_acompte`, billed_item=`P1_GAZ_LOT{n}`, annual_amount_ht=total)
2. Le service de contrôle P1 lit **déjà** la référence en base (`_find_contract_reference`) — **aucune modification** du contrôle nécessaire (cf. §9.3, il n'y a pas de constante à remplacer)
3. ⚠️ Trancher au préalable l'écart seed DPGF (341 293 €) vs RECAP parsé (≈ 317 775 €) — cf. §9.4
4. **Impact** : le montant de référence P1 s'adapte automatiquement aux avenants (nouveaux sites, révisions tarifaires)

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

## 7bis. Audit de couverture du parsing (2026-06-01)

Audit complet des 13 feuilles du fichier DALKIA. État après ajout du parsing RECAP MARCHE (commit `4136225`).

| Feuille | Lignes | Parsing | Table cible |
|---|---|---|---|
| Annexe 3.1 - P2 - A | 81 | ✅ complet | `cpe_dalkia_ref_p2p3` |
| Annexe 4 - P3 | 87 | ✅ complet | `cpe_dalkia_ref_p2p3` |
| Annexe 2bis - Travaux APE | 329 | ✅ complet | `cpe_dalkia_ref_ape` |
| Annexe 5.1 - Cibles GAZ | 78 | ⚠️ partiel | `cpe_dalkia_ref_cibles` |
| Annexe 5.2 - Cibles ELEC | 87 | ⚠️ partiel | `cpe_dalkia_ref_cibles` |
| Annexe 6 - P1 GAZ | 84 | ⚠️ partiel | `cpe_dalkia_ref_p1_gaz` |
| **RECAP MARCHE** | 52 | ✅ **complet (ajouté)** | `cpe_dalkia_ref_recap` |
| Annexe 1 - Coefficients | 21 | ❌ non parsé | — |
| Annexe 2 - Travaux obligatoires P3.4 | 193 | ❌ non parsé | — |
| Annexe 3.2 - P2 - B (sensibilisation) | 7 | ❌ non parsé | partiellement dans recap |
| Annexe 7 - B.P.U - D.Q.E | 184 | ❌ non parsé | — |
| Annexe 8 - Moyens opérationnels | 9 | ❌ non parsé (peu de données) | — |
| Annexe 9 - Plan de progrès | 6 | ❌ non parsé (quasi vide) | — |

### Données RECAP MARCHE désormais capturées

`cpe_dalkia_ref_recap` (format long, métrique × période) — validé :
- **L1** : 227 lignes — P1 2026 = 317 775 € HT, **bilan total marché = 9 756 895 € HT** (P1 1,9M / P2 2,2M / P3 5,5M / sensibilisation 99k)
- **L2** : 156 lignes — bilan 1 252 054 € HT (piscines, sans P1 gaz)

Sections : `engagement` (GAZ/ELEC/PV/GLOBAL : QT réf/cible, % économie, CO2), `redevance_p1`, `redevance_p2p3`, `sensibilisation`, `travaux`, `bilan`.

> **Impact direct** : la référence P1 du contrôle d'acompte (en base, `cpe_contract_references` — **pas** une constante de code, cf. §9.3) pourra être alimentée automatiquement depuis `cpe_dalkia_ref_recap` (metric=`p1_total_ht`, période=année), sous réserve de réconcilier l'écart avec la valeur seed DPGF (cf. §9.4). Voir Phase C.

### Gaps de couverture restants (non parsés)

| Feuille / colonne | Donnée | Priorité |
|---|---|---|
| Annexe 2 - Travaux obligatoires P3.4 | 193 travaux obligatoires détaillés (montant, dates, devis, CEE) par site | 🟠 Moyenne |
| Annexe 7 - BPU/DQE | Bordereau prix unitaires opérations (codes ENT-xxx) | 🟡 Basse (structure très hétérogène) |
| Annexe 1 - Coefficients | Taux horaires main d'œuvre + coefficients entreprise | 🟡 Basse |
| Annexe 6 (en-tête) | Prix unitaires gaz T1-T4 + coefficients formule révision Pu (a,b,c,d,e) | 🟠 Moyenne (contrôle révision prix gaz) |
| Annexe 5.x (colonnes) | Référence consommation ECS m3, identifiants compteurs | 🟡 Basse |
| Annexe 3.2 - P2 - B | Détail actions sensibilisation (totaux déjà dans recap) | 🟢 Couvert partiellement |

---

## 8. Architecture du parseur — points de modification

### Fichiers à modifier pour étendre le parsing

| Fichier | Rôle | Modifier pour… |
|---------|------|----------------|
| `saas/backend/app/services/cpe_dalkia_import.py` | **Parseur principal** — lit l'Excel, produit `DalkiaParseResult` | Ajouter une feuille, corriger un décalage de colonne, modifier la logique de détection de section |
| `saas/backend/app/services/cpe_dalkia_db.py` | Persistance — écrit `DalkiaParseResult` en base | Ajouter la persistance d'une nouvelle table de référence |
| `saas/backend/app/models/cpe_dalkia.py` | Modèles ORM SQLAlchemy | Ajouter une table `cpe_dalkia_ref_*` (+ migration Alembic) |
| `saas/backend/app/api/routes/cpe_dalkia.py` | Routes FastAPI | Ajouter un endpoint (ex. `/recap`, `/sync-*`) ou enrichir les réponses |
| `saas/frontend/src/pages/CpeDalkiaImportPage.tsx` | UI d'import et preview | Modifier l'affichage de la preview, ajouter un onglet dans `ClassifiedPreview` |

### Structure interne du parseur (`cpe_dalkia_import.py`)

> ⚠️ Arbre vérifié ligne par ligne contre le code (2026-06-02). Tous les sous-parseurs reçoivent
> `rows: list[tuple]` (les lignes brutes de la feuille via `ws.iter_rows(values_only=True)`),
> **pas** un worksheet, et renvoient un **tuple `(données, warnings)`**.

```
parse_dalkia_file(raw_bytes: bytes, filename: str, lot: int) → DalkiaParseResult
│   (ouvre le classeur, _get_rows(sheet_name) lit chaque feuille en list[tuple])
│
├── _parse_p2(rows, lot) → (sites, p2_rows, warnings)
│     Annexe 3.1 - P2 - A (57 col) — headers ligne 9, data ligne 10
│     PERIOD_STARTS = [5, 11, 17, 23, 29, 35, 41, 47, 53]  (offset 6)
│
├── _parse_p3(rows, p2_rows) → (p2p3_rows, warnings)
│     Annexe 4 - P3 — P3 FUSIONNÉ dans les lignes P2 existantes (même objet DalkiaP2P3Row)
│
├── _parse_cibles(rows, fluid, lot) → (cibles, warnings)   [appelé 2× : "GAZ" puis "ELEC"]
│     Annexes 5.1 / 5.2 (54 col) — headers ligne 8, data ligne 9
│     PERIOD_STARTS = [10, 15, 20, 25, 30, 35, 40, 45, 50]  (offset 5)
│
├── _parse_p1_gaz(rows, lot) → (p1_rows, warnings)
│     Annexe 6 - P1 GAZ (38 col) — ligne de headers trouvée dynamiquement (cherche "LOT"+"ENTITE"/"PROG")
│     PERIOD_STARTS = [12, 15, 18, 21, 24, 27, 30, 33, 36]  (offset 3) ; code_site en col 3 (N° PROG)
│
├── _parse_ape(rows, lot) → (ape_rows, warnings)
│     Annexe 2bis - Travaux APE (20 col) — header trouvé dynamiquement (cherche "CODE"+"SITE")
│
└── _parse_recap(rows) → (recap_rows, warnings)        [PAS de paramètre lot]
      RECAP MARCHE — format long (1 DalkiaRecapRow par métrique × période)
      Détection de section inline : c1.startswith("2.6"…"2.10") OU mots-clés (robuste L1/L2)
      Colonnes de période détectées par _recap_period_map(header_row, start_col)
      6 valeurs possibles de DalkiaRecapRow.section :
        engagement, redevance_p1, redevance_p2p3, sensibilisation, travaux, bilan
      (5 marqueurs current_section ; "sensibilisation" émise spécialement dans la section 2.8)

build_import_preview(result: DalkiaParseResult) → DalkiaImportPreview   [dataclass, pas dict]
│
├── Comptages (nb_sites, nb_p2p3_rows, nb_cibles_rows, nb_p1_gaz_rows, nb_ape_rows, nb_recap_rows)
├── recap_summary : bilan_marche_ht, by_year {p1/p2/p3_total_ht}, facteurs CO2 (via _recap_value)
├── period_labels, sample_sites (5 premiers sites avec données 2026)
└── classified : _build_classified(result) → dict[str, Any] — données pivotées par catégorie
      ├── years
      ├── p2p3 : [{code_site, nom_batiment, by_year: {2025…2033: {p2, p3}}}]
      ├── cibles_gaz / cibles_elec : [{code_site, ref_globale, dju, by_year}]   (via _pivot_cibles)
      ├── p1_gaz : [{code_site, pce, type_tarif, prix_unitaire_ht, by_year}]
      ├── ape : [{code_site, description_ape, annee_achevement, montant_ape_ht, …}]
      └── recap_engagement / recap_redevances / recap_travaux / recap_bilan   (via _recap_pivot)
```

### Constantes et invariants à connaître

- `PERIOD_YEARS = [2025, 2026, 2027, 2028, 2029, 2030, 2031, 2032, 2033]` et `N_PERIODS = 9` — périodes fixes (haut de fichier)
- **Détection d'une ligne de site** : `_is_site_row(val)` — n'utilise **aucune regex**. Retourne vrai si la cellule col 1 est non vide et ne commence **ni** par `TOTAL` **ni** par `SOUS` (insensible à la casse). Le `code_site` n'est donc pas validé sur un format type `VDS-…`.
- **Noms de feuilles** : littéraux inline dans `parse_dalkia_file` via `_get_rows("Annexe 3.1 - P2 - A")`, etc. Il n'existe **pas** de constantes `SHEET_*`. En cas de renommage à l'avenant, modifier directement ces chaînes dans `parse_dalkia_file`. `_get_rows` renvoie `[]` si la feuille est absente (pas d'erreur).
- **RECAP MARCHE** : la structure change selon la section. La détection est **inline** dans `_parse_recap` (`c1.startswith("2.6")` … `"2.10"` + mots-clés de repli). Les colonnes de période sont (re)calculées par `_recap_period_map` à chaque ligne d'en-tête (`Paramètre`, `Energie`). Les métriques sont mappées par sous-chaîne de libellé via la table `METRIC_DEFS`.
- **P1 gaz / APE** : la ligne d'en-tête est trouvée **dynamiquement** (recherche de mots-clés), pas à un index fixe — robuste aux décalages de lignes entre L1/L2.

### Ajouter une nouvelle feuille non parsée (ex. Annexe 2 — Travaux P3.4)

1. Définir un `@dataclass DalkiaTravauxP3Row` dans `cpe_dalkia_import.py`
2. Créer `_parse_travaux_p3(rows, lot) → tuple[list[DalkiaTravauxP3Row], list[str]]` (signature cohérente avec les autres : `rows` + retour `(données, warnings)`)
3. Ajouter le champ `travaux_p3: list[DalkiaTravauxP3Row]` à `DalkiaParseResult`
4. Dans `parse_dalkia_file` : `tp3_raw = _get_rows("Annexe 2 - …"); travaux_p3, w = _parse_travaux_p3(tp3_raw, lot); all_warnings.extend(w)` puis passer `travaux_p3=travaux_p3` au constructeur `DalkiaParseResult(...)`
5. Créer le modèle ORM dans `models/cpe_dalkia.py` (+ l'exporter dans `models/__init__.py`) + migration Alembic
6. Ajouter la persistance dans `cpe_dalkia_db.py` (pattern identique aux autres tables)
7. Exposer dans `_build_classified` + ajouter un onglet dans `ClassifiedPreview` (frontend)
8. Documenter le gap couvert dans la section 7bis de ce fichier

---

## 9. Connexions opérationnelles — état réel (vérifié contre le code 2026-06-02)

> ⚠️ Section re-vérifiée ligne par ligne contre `cpe_dalkia.py`, `cpe_dalkia_db.py`,
> `cpe_accounting.py` et la migration `0029`. Distinction nette entre *câblé* (consommé par
> un frontend) et *disponible* (endpoint existe mais aucun appelant).

### 9.1 Connexions réellement câblées (frontend ↔ API ↔ base)

Seuls 4 endpoints sont consommés par `CpeDalkiaImportPage.tsx` :

| Source (table) | → | Destination (UI) | Endpoint / champ | Persisté ? |
|---|---|---|---|---|
| `cpe_dalkia_ref_imports` | → | Historique des imports | GET `/cpe/dalkia-ref/imports` | ✅ |
| `cpe_dalkia_ref_sites` | → | Bouton « Voir les sites » | GET `/cpe/dalkia-ref/imports/{id}/sites` | ✅ |
| Données **parsées** (pas encore en base) | → | Résumé financier + `ClassifiedPreview` (6 onglets) | POST `/cpe/dalkia-ref/preview` → `recap_summary` + `classified.{p2p3,cibles_gaz,cibles_elec,p1_gaz,ape,recap_*}` | ❌ preview seul |
| `DalkiaParseResult` complet | → | Écriture en base à la validation | POST `/cpe/dalkia-ref/confirm` → `persist_dalkia_import()` | ✅ écrit les 6 tables |
| `cpe_dalkia_ref_cibles` (NB GAZ, import actif) | → | **Moteur d'intéressement** (N'B, écart, bilan) | `resolve_nb_for_year()` dans `services/cpe.py` → `calculer_resultat_site` / `get_bilan_annuel` | ✅ lit la base (fallback scalaire) |

**Précisions importantes** :
- `recap_summary` et `classified` ne sont renvoyés **que par `/preview`**. La réponse de `/confirm` (`ImportBatchResponse`) ne contient **que des comptages** (`nb_*_rows`), pas le détail. La preview classifiée travaille donc sur les données *parsées en mémoire*, avant toute écriture en base.
- `/confirm` persiste bien les 6 tables (`cpe_dalkia_db.py:127-230`), y compris `cpe_dalkia_ref_recap` (lignes 218-230).
- Après confirmation, **aucune UI ne ré-affiche** le détail P2P3 / cibles / P1 / APE / recap depuis la base : seuls les sites sont consultables.

### 9.2 Endpoints disponibles mais NON câblés (API prête, aucun appelant frontend)

| Endpoint | Service | Statut |
|---|---|---|
| GET `/cpe/dalkia-ref/imports/{id}/p2p3` (`?period_year=`) | `get_p2p3_for_import` | ⚠️ jamais appelé par le frontend |
| GET `/cpe/dalkia-ref/imports/{id}/cibles` (`?fluid=&period_year=`) | `get_cibles_for_import` | ⚠️ jamais appelé |
| GET `/cpe/dalkia-ref/imports/{id}/ape` | `get_ape_for_import` | ⚠️ jamais appelé |
| GET `/cpe/dalkia-ref/imports/{id}/recap` (`?section=`) | `get_recap_for_import` | ⚠️ jamais appelé |

Ces endpoints permettront de rebrancher la preview classifiée sur les données **persistées** (relecture d'un import actif sans re-uploader le fichier) — câblage frontend à faire.

### 9.3 Contrôle de facture P1 — connexion existante (et le mythe de la « constante hardcodée »)

| Source | → | Destination | Emplacement |
|---|---|---|---|
| `cpe_contract_references` (kind=`p1_gaz_acompte`) | → | `_control_p1_gaz_acompte_against_dpgf()` | `cpe_accounting.py:1733` |
| `.annual_amount_ht / .installment_count` | → | Acompte attendu = `annual / installments` | `cpe_accounting.py:1804` |
| `.expected_amount_ht` (si fourni, prioritaire) | → | Acompte attendu direct | `cpe_accounting.py:1802` |

> ❗ **Correction d'une affirmation erronée** : il n'existe **aucune constante hardcodée**
> (`317774`, `341293`…) dans `cpe_accounting.py` ni ailleurs dans le backend (`grep` → vide).
> Le contrôle P1 lit **déjà** sa référence en base via `_find_contract_reference()`.
> La valeur de référence provient de la **migration seed `0029`** :
> `contract_code='C00190116O'`, `year=2026`, `billed_item='P1_GAZ_LOT1'`,
> **`annual_amount_ht = 341293.06`**, `installment_count = 4` → acompte attendu **85 323,27 € / trimestre**
> aux échéances 31/03, 30/06, 30/09 (`expected_period_months='3,6,9'`), tolérance 1 % ou 100 €.

### 9.4 Connexion à activer (Phase C) — réconciliation, pas remplacement

L'objectif n'est donc **pas** de « remplacer une constante » mais d'**alimenter automatiquement**
`cpe_contract_references` depuis l'import DALKIA, et de **réconcilier un écart réel** :

| Origine | Valeur P1 Lot 1 2026 |
|---|---|
| Seed `0029` (DPGF, en base aujourd'hui) | **341 293,06 € HT** |
| RECAP MARCHE parsé (`cpe_dalkia_ref_recap`, metric `p1_total_ht`, période 2026) | **≈ 317 775 € HT** |
| Somme `p10_total_ht` Annexe 6 (`cpe_dalkia_ref_p1_gaz`) | à recouper (≈ même ordre) |

> Ces deux sources **diffèrent d'environ 23 500 €** : avant tout branchement automatique, il faut
> trancher laquelle fait foi (DPGF contractuelle vs RECAP) — c'est un point à clarifier avec DALKIA,
> pas une simple substitution de code.

**Travail Phase C** :
1. Endpoint `POST /cpe/dalkia-ref/imports/{id}/sync-p1-reference` qui lit `cpe_dalkia_ref_recap`
   (ou la somme `cpe_dalkia_ref_p1_gaz.p10_total_ht`) par lot × année.
2. Upsert `cpe_contract_references` (kind=`p1_gaz_acompte`, year, `annual_amount_ht`).
3. Le contrôle existant `_control_p1_gaz_acompte_against_dpgf` consomme **sans modification** la
   nouvelle valeur (il lit déjà la base) → auto-adaptatif aux avenants.
4. Conserver une trace de la source (`notes`) pour l'audit de la valeur retenue.

---

## 10. Liens

- [[10-Roadmap-Po2]] — phases et priorités
- [[11-Implémentation-Po2]] — état des tables CPE existantes
- [[13-Export-finances-DALKIA]] — format des factures DALKIA
- [[15-Formules-indices-et-travaux-P3]] — formules de révision P2/P3
- [[16-Pilotage-financier-et-controle-global]] — vue d'ensemble des contrôles
- [[03-Cibles-et-intéressement]] — formule NB/N'B/NC
- [[04-Cibles-par-site]] — NB et qECS par site (données historiques seed)

**Fichiers sources** :
- `saas/backend/app/services/cpe_dalkia_import.py` — parseur + preview builder
- `saas/backend/app/services/cpe_dalkia_db.py` — persistance
- `saas/backend/app/models/cpe_dalkia.py` — modèles ORM
- `saas/backend/app/api/routes/cpe_dalkia.py` — routes FastAPI
- `saas/frontend/src/pages/CpeDalkiaImportPage.tsx` — UI import + ClassifiedPreview
