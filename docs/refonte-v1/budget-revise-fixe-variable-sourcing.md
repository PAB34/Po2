# Budget révisé fiable = décomposition FIXE / VARIABLE des factures — sourcing

> Rapport « fil du dev » (lecture seule) — 2026-07-02. Demande utilisateur : pour obtenir un **budget
> révisé fiable** (pas un coefficient global approximatif), il faut d'abord savoir **comment on reconstitue
> le montant de chaque facture** et **ce qui y est fixe vs variable**, par fournisseur/marché. Ce rapport
> cartographie l'existant (les moteurs de reconstitution/contrôle sont **déjà construits**) avant tout code.

## 0. Le principe (validé)

Toute facture énergie se reconstitue comme :

```
Total HT = Σ parts FIXES  +  Σ parts VARIABLES
part variable = consommation × prix unitaire (le prix a lui-même une base + une variable de révision)
part fixe     = abonnement / terme fixe / forfait (révisé par un indice ou un tarif versionné)
```

Donc **budget révisé fiable** =
`Σ (part fixe × révision)  +  Σ (conso attendue × prix de référence de la période)`.
→ Le coefficient global `Σrévisé/Σbase` (mon v1 CPE) est un raccourci : correct pour un forfait pur
(P2/P3), faux dès qu'il y a une part conso (P1 gaz, ENGIE, EDF). **La bonne granularité = fixe/variable.**

## 1. Ce qui existe déjà (moteurs de reconstitution/contrôle)

### 1.1 Gaz TotalEnergies / Hérault Énergie — décomposition COMPLÈTE
`app/services/gas_invoice.py` reconstitue et contrôle (docstring : `prix conso × kWh = montant conso ;
somme des composantes = total HT ; HT + TVA = TTC`). Modèle `models/gas_invoice.py :: GasInvoice` :

| Nature | Composantes (colonnes) | Variable de prix / référence |
|---|---|---|
| **Variable** (conso) | `prix_conso_gaz` (€/kWh) × `total_conso_kwh` = `montant_conso_gaz` ; `atrd_terme_variable` ; `montant_ticgn` (accise) ; `montant_indexation` | **PEG** → `models/gas_revisable.py :: GasSupplyRevisablePrice` (prix révisable **mensuel** €/MWh, `load_revisable_prices()`) ; BPU gaz lot 7 → `gas_bpu.py :: GasBpuPrice` |
| **Fixe** | `abonnement_fournisseur` ; `atrd_terme_fixe` ; `atrt_terme_fixe` ; `montant_cta` | ATRD/ATRT → `gas_network_tariff.py :: GasNetworkTariff` ; taxes → `gas_tax.py :: GasTaxRate` |

→ Tout est déjà décomposé et référencé. Migrations 0057→0062. Doc : `Modules/Energie-Gaz.md`.

### 1.2 DALKIA P1 gaz (CPE) — prix gaz OS3 (distinct du BPU TotalEnergies)
`app/services/cpe_dpgf_p1.py` + contrôle `cpe_accounting._control_p1_gaz_pu_os3` : le P1 gaz DALKIA est une
**cotation OS3** (prix gaz du marché CPE), facturé à la conso. ⚠️ Invariant (04 §gaz) : ne pas fusionner
la cotation OS3 P1 avec la référence BPU TotalEnergies. Fixe = acompte P1 (`_control_p1_gaz_acompte_against_dpgf`).

### 1.3 DALKIA P2 / P3 — forfaits annuels (part fixe pure)
`cpe_accounting` : révision par indices **ICHT-IME / FSD2** (P2) et **ICHT-IME / BT40** (P3). base/révisé
**fournis par DALKIA** (`prix_de_base`, `prix_ou_forfait_revise`). Pas de part conso → le coefficient
Σrévisé/Σbase y est correct. (cf. `revision-trimestrielle-atterrissage-audit.md`).

### 1.4 ENGIE / EDF — élec (fourniture + acheminement TURPE + taxes)
- **Acheminement TURPE** : `app/services/turpe.py` — **tables tarifaires versionnées** (`list_turpe_versions`,
  `list_turpe_evolution_events`, `find_turpe_table(on_date)`) + reconstitution attendue par composante :
  `_expected_variable_line` (**variable** = soutirage × kWh) et **part fixe** TURPE (€/kVA/an, gestion,
  comptage). Doc : `Modules/Energie-TURPE.md` (source `saas/specs/07_referentiel_turpe_7.md`).
- **Fourniture** : `bpu.py` / `invoice_bpu.py` / `billing_bpu_sync.py` — composantes de prix BPU (timeline
  des prix d'achat marchés Hérault Énergies) → prix × kWh (**variable**) + éventuel abonnement (**fixe**).
  Contrôle facture : `invoice_analysis.py`. Doc : `Modules/Energie-BPU.md` (« pipeline complet en prod »).
- **Coût réel élec par PRM** : `power_real_costs.py` (prix × conso reconstitué depuis les factures).
- **Imports** : `engie_xlsx_import.py` (ENGIE), `edf_csv_import.py` + `invoice_parsers/edf_csv.py` (EDF).
- **Conso de référence** : **ENEDIS** (distributeur), pas les factures fournisseur (cf. stratégie §4).

## 2. Fixe vs variable — synthèse par marché

| Marché | Part FIXE | Part VARIABLE | Variable de révision | Conso réf. |
|---|---|---|---|---|
| Gaz TotalEnergies | abo fournisseur, ATRD/ATRT fixe, CTA | conso×prix, ATRD variable, accise | PEG mensuel, ATRD versionné | factures / GRDF |
| DALKIA P1 gaz | acompte P1 | conso×prix OS3 | cotation OS3 (prix gaz) | factures CPE |
| DALKIA P2/P3 | forfait annuel (tout fixe) | — | ICHT-IME/FSD2/BT40 | — |
| ENGIE élec | abo fourniture + TURPE fixe (€/kVA) | fourniture×kWh + TURPE soutirage×kWh | BPU + TURPE versionnés | **ENEDIS** |
| EDF éclairage | idem ENGIE (fixe abo/TURPE) | idem (fourniture+soutirage ×kWh) | BPU + TURPE versionnés | **ENEDIS** |

## 3. Ce qui existe vs ce qui manque

| Brique | État |
|---|---|
| Décomposition facture gaz (fixe/variable) | ✅ complète (`GasInvoice` + `gas_invoice.py`) |
| Références prix gaz (PEG, BPU, ATRD, taxes) | ✅ modèles + loaders |
| TURPE versionné (fixe/variable) + événements | ✅ `turpe.py` |
| BPU élec (composantes de prix) | ✅ `bpu.py` (pipeline prod) |
| Coût réel élec reconstitué par PRM | ✅ `power_real_costs.py` |
| Imports ENGIE / EDF | ✅ `engie_xlsx_import`, `edf_csv_import` |
| Conso ENEDIS rattachée aux sites CPE/marchés | 🟡 socle ENEDIS + rapprochement, rattachement à finaliser |
| **Couche BUDGET RÉVISÉ / atterrissage** qui consomme tout ça | ❌ **à construire** (n'existe que pour CPE, en coefficient global) |
| Cible EDF éclairage | ❌ à définir (historique) |
| Table de suivi des indices/variables + graphes | ❌ à construire (TURPE versionné = point de départ) |

## 4. Conséquence pour un budget révisé fiable (proposition d'archi)

Un **moteur générique « facture attendue »** par marché/site/période :
```
budget_revisé(période) = Σ parts fixes révisées (abo, TURPE fixe, forfait indexé)
                        + Σ (conso attendue × prix de référence de la période)
```
- **parts fixes** : révisées via l'indice/tarif versionné (TURPE, ATRD, indices DALKIA).
- **part variable** : `conso attendue × prix de référence` — le prix de référence est **déjà** dispo
  (PEG mensuel, BPU, TURPE soutirage) ; la conso attendue vient de la **cible** (DALKIA), de l'**historique**
  (EDF) ou de l'**extrapolation DJU** (thermosensible).
- **Réalisé** = factures (déjà décomposées). **Atterrissage** = réalisé à date + reste estimé (mêmes prix).

→ On **ne recode pas** les prix ni les contrôles : on **branche** l'atterrissage dessus. C'est la
généralisation du service CPE `accounting_contract_budget`, en remplaçant le coefficient global par la
reconstitution fixe/variable.

## 5. Questions ouvertes (numérotées)

1. **Maille du budget révisé** : par marché+poste (comme aujourd'hui) ou par **site/PRM** (nécessaire pour
   brancher la conso ENEDIS et les parts fixes par point de livraison) ?
2. **Conso attendue** (part variable) : source par marché — cible contractuelle (DALKIA), historique N-1
   (EDF), extrapolation DJU (gaz/chauffage) ? On acte une source par marché ?
3. **Périmètre du 1er incrément** : (a) fiabiliser P1 gaz DALKIA via PEG/OS3 (petit, complète le CPE), ou
   (b) poser le moteur générique fixe/variable et l'appliquer d'abord au gaz TotalEnergies (le mieux outillé) ?
4. **Table de suivi des indices** : on la construit sur quelles variables en priorité (PEG, ICHT/FSD/BT40,
   TURPE) et alimentée comment (saisie manuelle vs import) ?
5. **EDF** : maille de cible éclairage public (ville / armoire / secteur) et méthode (historique N-1, N-2) ?

## 6. Ce que je NE fais pas sans validation
- Choisir la maille (Q1) et les sources de conso attendue (Q2) — structurant.
- Remplacer le coefficient global CPE par la reconstitution fixe/variable avant de valider le périmètre (Q3).
