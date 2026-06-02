# OS N°3 — Prix fixe gaz 5 ans (2026-2030)

tags: #CPE #gaz #prix #contrat #facturation #OS3

> **Ordre de Service n°3** — signé le **15 janvier 2026**  
> Marché **24BT039** — Lot 1 Bâtiments communaux + CCAS, Ville de Sète  
> Titulaire : **DALKIA S.A.**  
> Fichier source : `saas/energie/DALKIA/OS N°3 cotation gaz 01012026 - 5 ans.xlsx`

---

## Prix unitaires fixes 2026-2030

Les prix molécule gaz ont été **fixés pour 5 ans** (01/01/2026 au 31/12/2030).  
Les autres composantes (acheminement, CEE, TICGN) restent variables et révisables selon la formule P1.

| Tarif | Prix (€HT/MWhPCS) | Prix converti PCI (€HT/MWhPCI) | Sites concernés |
|-------|-------------------|-------------------------------|-----------------|
| **T1** | **107,03** | **118,50** | ENS 09, ENS 10, ENS 13, BAM 12 (4 sites) |
| **T2** | **74,17** | **82,13** | Majorité des sites (environ 50) |
| **T3** | **70,78** | **78,42** | CCAS 04 (Résidence LE THONNAIRE) |

> Conversion PCS → PCI : **ratio PCS/PCI = 1,1068** (gaz naturel GRDF zone Languedoc-Roussillon)  
> Formule : `Pu_PCI = Pu_PCS × 1,1068`  
> Ce ratio est stable à ±0,5% sur la zone. À affiner avec les bulletins de qualité GRDF.

### Décomposition par composante

| Composante | T1 | T2 | T3 | Note |
|-----------|-----|-----|-----|------|
| Prix molécule CPB (fixe 5 ans) | 38,62 | 38,62 | 38,62 | Identique tous tarifs |
| Acheminement TVD (variable) | 44,94 | 12,08 | 8,69 | Révision formule P1 |
| Obligation CEE (variable) | 7,63 | 7,63 | 7,63 | |
| TICGN (variable) | 15,43 | 15,43 | 15,43 | |
| Contribution Biométhane CPB (variable) | 0,41 | 0,41 | 0,41 | |
| **Total au 01/01/2026** | **107,03** | **74,17** | **70,78** | |

### Anomalie BAM 09

> ⚠️ **VDS-BAM 09** (Crématorium RAYMOND FÉLICES) est **labellisé T3** dans l'OS N°3 mais le **prix indiqué est 74,17 €/MWhPCS (= T2)**.  
> À vérifier avec DALKIA : erreur de tarification ou reclassement T3→T2 non acté ?  
> Dans Po2, BAM 09 est stocké `tarif='T3'` → le calcul utilisera le Pu T3 (78,42 €/MWhPCI).  
> Si DALKIA confirme facturation au T2, modifier le champ `tarif` de BAM 09 via l'API.

---

## Formule de révision P1 (rappel)

Applicable aux composantes variables (hors molécule fixe 2026-2030) :

```
Pu_GAZ = Pu_0 × (a + b×CPB/CPB0 + c×TVD/TVD0 + d×CEE/CEE0 + e×TICGN/TICGN0)
```

### Coefficients par tarif

> ⚠️ **Corrigé 2026-06-02** — valeurs **parsées depuis l'Annexe 6 (offre finale)**, désormais en base
> dans `cpe_dalkia_ref_p1_tarifs`. Les valeurs précédemment notées ici (a=0,36083…) étaient erronées
> (brouillon ou transcription). Invariant vérifié : **a+b+c+d+e = 1** par tarif.

| Coef | T1 | T2 | T3 | T4 |
|------|-----|-----|-----|-----|
| a | 0,03272 | 0,04782 | 0,05112 | 0,08037 |
| b | 0,39065 | 0,53384 | 0,55422 | 0,59183 |
| c | 0,36996 | 0,13591 | 0,10145 | 0,01468 |
| d | 0,05684 | 0,07768 | 0,08064 | 0,08612 |
| e | 0,14983 | 0,20475 | 0,21257 | 0,22700 |

Composants de base (période 0, 13/10/2025), par tarif (€HT/MWhPCS) — aussi parsés :
PEG₀ = 44,74 (tous tarifs) · CEE₀ = 6,51 · TICGN₀ = 17,16 · acheminement (TVD₀) = 42,37 (T1) / 11,39 (T2) /
8,19 (T3) / 1,11 (T4) · Pu₀ = 126,35 (T1) / 92,46 (T2) / 89,06 (T3) / 83,40 (T4).

### ✅ Contrôle « prix unitaire gaz vs OS N°3 » (2026-06-02)

Implémenté : `_control_p1_gaz_pu_os3` (control_type `p1_gaz_pu_os3`, `services/cpe_accounting.py`).
Pour 2026-2030, le `base_price` des lignes P1 / `CHAUFFAGE` porte le **Pu gaz facturé** (€/MWhPCS) —
validé sur prod (CCAS 04 facture 70,78 en 2026 = OS N°3 T3). Le contrôle compare ce Pu au prix OS N°3
du tarif du site (`cpe_prix_gaz`, PCI → converti en PCS via ÷ `PCS_PCI_RATIO`), tolérance 0,3 €/0,5 %.
Tarif résolu via `cpe_dalkia_ref_p1_gaz` (import actif). Statuts : `ok` / `error` / `blocked` (tarif
ou prix OS N°3 absent). Seules les lignes dont `base_price ∈ [30, 250]` sont contrôlées (les autres
lignes CHAUFFAGE portent des montants, couverts par le contrôle d'acompte P1). Tests :
`tests/test_cpe_p1_gaz_pu_os3.py` (6/6).

> **Reste pour le contrôle de révision *complet*** (au-delà du prix fixe OS N°3) : il faut les
> **valeurs de période** de PEG/TVD/CEE/TICGN (bulletins DALKIA) pour appliquer la formule Pu et
> recalculer le révisé. Les coefficients sont déjà en base (`cpe_dalkia_ref_p1_tarifs`) ; il manque
> la source des indices (cf. `cpe_revision_indices`, aujourd'hui limité à ICHT-IME/BT40/FSD2).

---

## Liste complète des sites OS N°3

### Sites T1 (4 sites)

| Code | Site | PCE |
|------|------|-----|
| VDS-ENS 09 | Maternelle LOUISE MICHEL | 24347901579996 |
| VDS-ENS 10 | Élémentaire ARAGO / Maternelle MICHELET | 24338639640741 |
| VDS-ENS 13 | Élémentaire LA RENAISSANCE + rest. scol. | 24306367441991 |
| VDS-BAM 12 | HÔTEL DE VILLE | 24359189519161 |

### Sites T3 (2 sites)

| Code | Site | PCE | Note |
|------|------|-----|------|
| VDS-BAM 09 | Crématorium RAYMOND FÉLICES | GI091897 | ⚠️ Anomalie prix T2 |
| CCAS 04 | Résidence autonomie LE THONNAIRE | GI091902 | Prix = 70,78 ✓ |

### Sites absents de l'OS N°3 (présents dans Annexe 5.1)

Ces sites figuraient dans l'offre initiale mais sont absents de l'OS N°3 — **statut à clarifier** (avenant 1 ?) :

| Code | Site |
|------|------|
| VDS-SPORT 02.02 | LE BARROU — Halle LOUIS MARTY |
| VDS-SPORT 02.03 | LE BARROU — TENNIS CLUB |
| VDS-CULT 01 | École des BEAUX-ARTS |
| VDS-BAM 10 | CSU — PÔLE SÉCURITÉ |
| VDS-BAM 11 | Direction des SPORTS |
| VDS-BAM 13 | LES HALLES |
| VDS-BAM 15 | Salle polyvalente GEORGES BRASSENS |

---

## Nouveaux sites identifiés dans l'OS N°3

Ces sites **n'étaient pas dans l'Annexe 5.1 initiale** (ou ont été ajoutés lors de la mise au point) :

| Code | Site | PCE | Tarif | NB (à compléter) |
|------|------|-----|-------|-----------------|
| VDS-CULT 02.01 | Ex conservatoire JEAN MOULIN | 24310130064611 | T2 | 0,0 → à saisir |
| VDS-CULT 02.02 | Logement de fonction n°13 | 24331693186390 | T2 | 0,0 → à saisir |
| VDS-CULT 02.03 | Logement de fonction n°15 | 24331259032936 | T2 | 0,0 → à saisir |
| VDS-CULT 05 | Musée PAUL VALERY | 24370766943113 | T2 | 0,0 → à saisir |
| CCAS 01 | EMACF FRANCOISE DOLTO | 24350361643410 | T2 | 0,0 → à saisir |
| CCAS 04 | Résidence autonomie LE THONNAIRE | GI091902 | T3 | 0,0 → à saisir |
| CCAS 05 | Structure Multi Accueil CHÂTEAU VERT | 24327206834125 | T2 | 0,0 → à saisir |
| CCAS 07 | Structure Multi Accueil QUARTIER HAUT | 24362807464172 | T2 | 0,0 → à saisir |
| CCAS 08 | Structure Multi Accueil VICTOR HUGO | 24347901530753 | T2 | 0,0 → à saisir |
| CCAS 09 | Structure Multi Accueil LACAN | 24367293715978 | — | Pas de gaz |

> **Action requise** : récupérer les NB (cibles gaz) pour les 9 nouveaux sites dans l'Annexe 5.1 CCAS du marché, puis les saisir via PATCH `/api/cpe/sites/{id}`.

---

## Impact sur Po2

### Changements de modèle (migration 0020)

- **`cpe_sites`** : nouveau champ `tarif` (T1/T2/T3) + `pce` (PCE GRDF)
- **`cpe_prix_gaz`** : nouveau champ `tarif`, contrainte unique `(annee, tarif)` (à la place de `annee` seul)

### Mise en service

```bash
# 1. Migrer la base
alembic upgrade head   # applique 0020_add_cpe_tarif_pce

# 2. Mettre à jour les sites existants (ajoute tarif + pce) + créer les 10 nouveaux
python -m app.scripts.seed_cpe_sites --city-id 1

# 3. Charger les prix OS N°3 pour 2026-2030 (T1/T2/T3)
python -m app.scripts.seed_cpe_prix_gaz

# Prévisualiser :
python -m app.scripts.seed_cpe_prix_gaz --dry-run
```

### Conversion PCS/PCI dans le code

```python
# services/cpe.py
PCS_PCI_RATIO = 1.1068

# seed_cpe_prix_gaz.py :
# T1 : 107,03 × 1,1068 = 118,50 €/MWhPCI
# T2 :  74,17 × 1,1068 =  82,13 €/MWhPCI
# T3 :  70,78 × 1,1068 =  78,42 €/MWhPCI
```

Le calcul d'intéressement utilise `pu_eur_mwh_pci` — déjà en PCI, pas de conversion à faire dans `calcul_interessement()`.

### Lookup du prix par tarif

```python
# services/cpe.py : calculer_resultat_site()
prix = get_prix_gaz(db, annee, site.tarif)  # T1 | T2 | T3 | None
pu_mwh = prix.pu_eur_mwh_pci if prix else None
```

Si un site n'a pas de tarif (`tarif=None`), le lookup tente un Pu global (`tarif=None` en base).

---

## Liens

- [[11-Implémentation-Po2]] — modèles DB, calculs, API
- [[03-Cibles-et-intéressement]] — formules NB/N'B/NC et intéressement
- [[06-Facturation-et-indices]] — formule complète révision P1
- [[04-Cibles-par-site]] — NB et qECS par site
