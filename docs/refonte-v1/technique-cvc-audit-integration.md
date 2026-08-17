# Technique & CVC — audit de l'existant et trajectoire d'intégration

> Rapport d'audit préalable (règle « fil du dev »). Écrit **avant** toute ligne de code.
> Date : 2026-08-17. Objectif visé : exploiter l'inventaire CVC pour obtenir un
> **état du patrimoine technique**, intégré à la refonte V1.

---

## 1. Résumé exécutif

Le chantier CVC est **beaucoup plus avancé que prévu côté acquisition** (import, référentiel de
durées de vie, moteur de cycle de vie par équipement, conformité F-Gas) mais **il n'existe
aucune vue « état du parc »** et **rien n'est branché dans la refonte V1**.

Trois constats structurants :

| # | Constat | Impact |
|---|---------|--------|
| **A** | **La base contient 3 399 équipements fantômes.** L'inventaire DALKIA a été importé **4 fois** les 3-5 juin 2026 (4 lots × 1 133 items, **empreintes de contenu identiques** `edec938b…`). Le parc réel est de **1 422 équipements**, pas 4 821. Une fois les doublons écartés, le rattachement est de **74,5 %** (DALKIA **88 %**, SPIE **22 %**) — et non 29,6 %. | **Prioritaire mais simple** : purge des 3 lots obsolètes. Sans elle, **tout compte est faux d'un facteur 3,4** sur le périmètre DALKIA. |
| **B** | Le moteur de cycle de vie existe **par équipement** (âge, durée restante, criticité %, référence SYPEMI) mais **n'est jamais agrégé** au niveau du parc. | L'état du patrimoine technique est à **construire**, pas à recoder : la matière est là. |
| **C** | La nav refonte contient déjà l'entrée **« Technique & CVC » → `/refonte-v1/technique`** marquée *comingSoon*, mais **aucune route n'existe** : le lien pointe dans le vide. Un profil « Technicien CVC » est déjà défini. | L'emplacement d'accueil est décidé, il reste à le remplir. |

⚠️ Point de vocabulaire important : la page existante `/buildings/cvc-rapport-technique`
(« rapport technique ») est en réalité un **rapport de couverture / qualité de rattachement**
(ce qui est rattaché ou non, mappings à revoir). **Ce n'est pas** un état du patrimoine technique.

---

## 2. Ce qui existe — backend

### 2.1 Modèle de données (`app/models/cvc.py`, 8 migrations 0014 → 0052)

| Table | Rôle | Volume prod |
|---|---|---|
| `cvc_inventory_items` | Inventaire des équipements CVC (multi-prestataires) | **4 821** |
| `cvc_refrigerant_items` | Volet fluides frigorigènes / F-Gas | **298** |
| `cvc_source_building_mappings` | Table de correspondance « libellé source → bâtiment » | 426 |
| `equipment_references` | **Référentiel SYPEMI** : nomenclature 5 niveaux + durées mini/référence/maxi + fiche CEE | **310** |
| `building_equipments` | Table de la migration 0014 — **vide, jamais utilisée** | **0** |

Champs déjà présents et pertinents pour un état technique : `provider` (DALKIA/SPIE),
`famille`, `type_equipement`, `marque`, `modele`, `numero_serie`, `puissance`,
`puissance_frigorifique`, `puissance_calorifique`, `capacite`, `date_mis_en_service`,
`etat_sante`, `statut`, `duree_vie_restante` (+ `_source`), `quantite_fluide_frigorigene`,
`equipment_ref_id`, `building_id` / `site_id` / `local_id`.

### 2.2 Moteur de cycle de vie — **la brique clé, déjà écrite**

`_compute_lifecycle()` / `_read_item()` (`services/cvc.py`, ~2 250 lignes) calculent **par équipement** :
- `lifecycle_age_years` (+ `_source`, `_label` : calculé depuis la date de MES, ou déduit de l'état de santé) ;
- `duree_vie_restante` — **arbitrage déjà tranché** : valeur calculée SYPEMI si possible, sinon valeur fournie par le prestataire, avec traçabilité de la source ;
- `criticite_pct` = âge / durée de référence SYPEMI (plafonné à 100) ;
- `sypemi_reference_annees`.

➡️ **Tout le calcul unitaire d'obsolescence est disponible. Il n'est simplement jamais agrégé.**

### 2.3 API (21 routes, `api/routes/cvc.py`)

- Import : `preview`, `match-buildings`, `import`, `imports`, `imports/{batch}/items`, `recompute-references`
- Rattachement : `imports/{batch}/site-matches`, `site-mappings`, `source-building-mappings` (GET/PATCH)
- Consultation : `buildings/{id}`, `items/{id}` (PATCH/DELETE)
- F-Gas : `refrigerants/import`, `/imports`, `/dashboard`, `/items/{id}`
- Qualité : `technical-report` (= couverture, cf. §1)

### 2.4 Tests
`test_cvc_reference_matching.py`, `test_cvc_spie_inventory.py`.

---

## 3. Ce qui existe — frontend

4 pages **legacy** (2 154 lignes), toutes hors refonte, sur `/buildings/*` :

| Page | Route | Rôle |
|---|---|---|
| `CvcImportPage` | `/buildings/cvc-import` | Import inventaire (722 l.) |
| `CvcSiteMappingPage` | `/buildings/cvc-import/batiments` | Rattachement libellés → bâtiments (512 l.) |
| `CvcRefrigerantsPage` | `/buildings/cvc-fluides` | Tableau de bord F-Gas (578 l.) |
| `CvcTechnicalReportPage` | `/buildings/cvc-rapport-technique` | Rapport de **couverture** (342 l.) |

**Aucune** n'est accessible depuis le shell refonte V1.

---

## 4. État réel des données (production, 2026-08-17)

### 4.1 ⚠️ D'abord : écarter les doublons d'import

`cvc_inventory_items` contient **4 821 lignes**, mais ce n'est **pas** le parc :

| Lot | Prestataire | Créé le | Items | Rattachés | Statut |
|---|---|---|---|---|---|
| `import_a275c544` | DALKIA | 03/06/2026 15:29 | 1 133 | 122 | ❌ doublon |
| `import_6403248b` | DALKIA | 04/06/2026 06:51 | 1 133 | 122 | ❌ doublon |
| `import_d0791486` | DALKIA | 05/06/2026 08:33 | 1 133 | 122 | ❌ doublon |
| **`import_d6887607`** | **DALKIA** | **05/06/2026 11:28** | **1 133** | **996** | ✅ **lot de référence** |
| **`spie_5e6ae323`** | **SPIE** | **12/06/2026 08:11** | **289** | **63** | ✅ **lot de référence** |

Les 4 lots DALKIA ont la **même empreinte de contenu** (`md5(designation+site_raw)` = `edec938b3e4ed156`) :
ce sont 4 imports successifs du même fichier lors de la mise au point. Seul le dernier a été
travaillé (mappings résolus). **3 399 équipements fantômes** à purger.

### 4.2 Le parc réel

```
Inventaire CVC          1 422 équipements   (DALKIA 1 133 · SPIE 289)
  rattachés à un bât.   1 059   (74,5 %)    ← DALKIA 88 % · SPIE 22 %
  avec date de MES        642   (45,1 %)
  avec réf. SYPEMI        985   (69,3 %)
  avec durée de vie       573   (40,3 %)

Fluides frigorigènes      298 équipements
  rattachés à un bât.       42   (14,1 %)
  avec teqCO2              252   (84,6 %)

Couverture patrimoine      69 bâtiments / 211   (32,7 %)
  dont DALKIA              60      dont SPIE 9      les deux 0
```

> Le rattachement DALKIA est donc **déjà bon (88 %)**. Les vrais gisements sont **SPIE (22 %)**,
> les **fluides frigorigènes (14 %)** et les **mappings multi-bâtiments** (voir §4.3).

### 4.3 Deux limites structurelles identifiées

1. **Mappings multi-bâtiments non propageables.** Un libellé source peut couvrir plusieurs
   bâtiments (ex. « VDS-ENS 13 Élémentaire LA RENAISSANCE + restaurant scolaire » → `[624, 623]`).
   Ces mappings stockent leurs cibles dans `building_ids_json` et laissent `building_id` à NULL ;
   `_apply_source_mapping_to_rows` ne pose alors **aucun** `building_id` sur les équipements
   (il ne sait pas lequel choisir). 69 mappings sont dans ce cas.
2. **Les mappings ne sont pas réutilisables d'un import à l'autre.** `_apply_source_mapping_to_rows`
   filtre sur `import_batch == mapping.import_batch` : le travail de rattachement d'un lot ne
   bénéficie pas au lot suivant. C'est ce qui a laissé les 3 lots doublons à 122 rattachements.

Top familles (parc réel) : « Autre à qualifier » en tête (~15 %), Split system, Pompe, Ventilation,
Compteur, Chaudière, Armoire électrique, Vase expansion.

> ⚠️ **~15 % des équipements en « Autre à qualifier »** : famille non exploitable telle quelle
> pour un état du parc par typologie.

---

## 5. Écart entre l'existant et l'objectif « état du patrimoine technique »

| Besoin | État | Reste à faire |
|---|---|---|
| Inventaire multi-prestataires | ✅ fait | — |
| Référentiel durées de vie (SYPEMI) | ✅ fait (310 réf.) | — |
| Âge / durée restante / criticité **par équipement** | ✅ fait | — |
| Conformité F-Gas | ✅ fait | rattachement bâtiment (14 %) |
| **Hygiène des données (doublons d'import)** | ❌ 3 399 fantômes | **priorité 0** |
| **Rattachement au patrimoine** | ⚠️ **74,5 %** réel (DALKIA 88 %, SPIE 22 %) | **priorité 1** |
| **Agrégation parc** (pyramide des âges, criticité par bâtiment/famille, fin de vie) | ❌ inexistant | **priorité 2** |
| **Page refonte `/refonte-v1/technique`** | ❌ lien mort | **priorité 3** |
| Valorisation € du renouvellement | ❌ inexistant | coût de remplacement absent du modèle |
| Normalisation des familles | ⚠️ 708 « à qualifier » | à arbitrer |

---

## 6. Trajectoire proposée (4 incréments)

**Incrément 0 — Hygiène : purger les lots doublons** — ✅ **FAIT le 2026-08-17**

- 3 lots DALKIA obsolètes supprimés : **3 399 équipements + 213 mappings**, après sauvegarde CSV
  (`/home/ubuntu/backups/cvc_doublons_20260817/`, 880 Ko) et contrôles de sécurité (0 fluide
  frigorigène dépendant, lots de référence non vides). Script `cvc_purge_doublons.py` : simulation
  par défaut, `--apply` pour exécuter, idempotent.
- **Base après purge : 1 422 équipements, 1 059 rattachés (74,5 %).**
- **Aucun code n'a été nécessaire.** La protection anti-accumulation existe déjà : le git montre que
  `_clear_current_cvc_inventory` (purge scopée par `provider`, appelée à chaque import) a été
  introduite les **10-11 juin 2026**, alors que les 4 imports doublons datent des **3-5 juin** — le
  bug était déjà corrigé, il ne restait que le résidu historique. Couvert par le test
  `test_provider_purge_is_isolated` (30 tests CVC verts).

**Incrément 1a — Libellés multi-bâtiments** — ✅ **FAIT le 2026-08-17 (PR #88)**

- Règle tranchée : un libellé couvrant plusieurs bâtiments rattache ses équipements au
  **bâtiment principal** (le premier déclaré), le périmètre complet restant tracé dans
  `building_ids_json`. Le `local_id` est effacé (il ne fait sens qu'en mono-bâtiment).
- Ajout de `reapply_source_building_mappings` + route `POST /api/cvc/source-building-mappings/reapply`
  (re-propage sans toucher aux mappings). 4 tests dédiés, 34 tests CVC verts.
- **Rattachement en prod : 74,5 % → 82,6 %** (+116 équipements). **DALKIA atteint 98 %.**

### Reste : 37 libellés orphelins (247 équipements, dont 226 SPIE)

⚠️ **Le moteur de similarité automatique n'est pas exploitable tel quel sur ce reliquat** —
test en lecture seule sur les 37 libellés :

| Cas | Constat |
|---|---|
| Faux positifs **au-dessus** du seuil (0,72) | « STADE LOUIS MICHEL » → *RESTAURANT SCOLAIRE LOUISE MICHEL* ❌ · « CIMETIERE MARIN » → *CIMETIERE LE PY* ❌ · « AMITIE DE LA CORNICHE » → *QUAI DE LA CONSIGNE* ❌ (alors que « ESPACE DE L AMITIE DE LA CORNICHE » existe) |
| Vrais positifs **en dessous** du seuil | « EGLISE SAINT JOSEPH » → *EGLISE CATHOLIQUE ST JOSEPH* (0,70) ✅ · « BAINS DOUCHES » → *LES NOUVEAUX BAINS DOUCHES* (0,67) ✅ · « VDS-ENS 17.03 GS - Élémentaire PAUL LANGEVIN (SUD) » → *Élémentaire PAUL LANGEVIN* (0,67) ✅ |

La similarité pure de chaînes confond des équipements de nature différente sur un patronyme commun
(stade/restaurant « Louis Michel ») et rate des synonymes évidents (SAINT/ST, préfixes « LES NOUVEAUX »).
**Conclusion : ne pas auto-appliquer.** Ces 37 libellés doivent passer par une validation humaine
(l'écran `CvcSiteMappingPage` existe déjà) ; une passe d'alias (SAINT↔ST, retrait des préfixes de
codification `VDS-ENS nn`) améliorerait le rappel sans lever le risque de faux positifs.

De plus, **certains bâtiments n'existent pas dans le patrimoine** (VILLA SALIS, STADE LOUIS MICHEL,
ESPACE VICTOR MEYER…) : ce n'est alors pas un problème de rapprochement mais de **complétude du
référentiel patrimoine**.

**Incrément 1b — Rattachement : traiter les vrais gisements**
Le DALKIA est déjà à 88 %. Restent :
- **SPIE (22 %)** : le moteur de suggestion `_resolve_alias_reference` / `_suggest_source_building`
  est calibré sur le vocabulaire DALKIA — à étendre aux libellés SPIE ;
- **fluides frigorigènes (14 %)** ;
- **mappings multi-bâtiments** : décider comment répartir un libellé couvrant 2 bâtiments
  (rattacher au bâtiment principal ? ventiler ? introduire un rattachement multiple ?) ;
- **rendre les mappings réutilisables entre imports** (clé `source_site_raw` au niveau ville plutôt
  que par lot), pour ne plus reperdre le travail à chaque réimport.

**Incrément 1b — Fiabilisation du rapprochement** — ✅ **FAIT le 2026-08-17 (PR #90)**

`_site_similarity` : alias (ST↔SAINT, GS→GROUPE SCOLAIRE…), retrait des préfixes de codification
(« VDS-ENS 17.03 GS - », « CCAS 10 »), et surtout **garde-fou sémantique** — score forcé à 0 si les
natures de bâtiment diffèrent (stade ≠ restaurant) ou si aucun token distinctif n'est commun
(CIMETIERE **MARIN** ≠ CIMETIERE **LE PY**). Score = `max(séquence, 0.4×jaccard + 0.6×couverture)`.
Branché sur `_suggest_source_building` et `_mapping_suggestions` (noms + adresses).
**Effet mesuré sur les 37 libellés orphelins : 10 suggestions au lieu de 6, faux positifs éliminés.**
Les suggestions restent soumises à validation humaine — rien n'est auto-appliqué. 16 tests dédiés.

**Incrément 2 — Moteur « état du parc »** — ✅ **FAIT le 2026-08-17 (PR #91)**

`GET /api/cvc/parc-technique` (filtres `provider`, `building_id`, `famille`) : KPI, pyramide des
âges, criticité, par famille, par bâtiment (les plus critiques en tête), par prestataire, et
**complétude de la donnée**. N'agrège que le lot d'import courant de chaque prestataire.
Aucun recalcul : l'agrégation s'appuie sur `_read_item`/`_compute_lifecycle`. 7 tests dédiés,
57 tests CVC verts.

### Premier état du parc réel (prod, 2026-08-17)

```
Équipements            1 422        Âge moyen        9,6 ans
Rattachés              1 175 (74 bâtiments)
Durée de vie DÉPASSÉE    210        Fin de vie < 5 ans   219
```

| Pyramide des âges | | Criticité | |
|---|---|---|---|
| 0-5 ans | 289 (20,3 %) | < 50 % | 426 (30,0 %) |
| 6-10 ans | 312 (21,9 %) | 50-80 % | 228 (16,0 %) |
| 11-15 ans | 124 (8,7 %) | 80-100 % | 74 (5,2 %) |
| 16-20 ans | 74 (5,2 %) | **dépassée** | **198 (13,9 %)** |
| 21-30 ans | 112 (7,9 %) | non calculable | 496 (34,9 %) |
| 30 ans et + | 15 (1,1 %) | | |
| **non calculable** | **496 (34,9 %)** | | |

**Bâtiments les plus critiques** : PISCINE BIASCAMANO (104 éq., 24 dépassés, 32 sous 5 ans),
ÉCOLE ÉLÉMENTAIRE LA RENAISSANCE (35 éq., 16 dépassés), MUSÉE PAUL VALÉRY, CENTRE SPORTIF MAURICE
CLAVEL, HÔTEL DE VILLE.
**Familles les plus critiques** : Pompe (61 dépassés / 153), Split system (33 dépassés, 49 sous
5 ans), Chaudière (19 dépassés / 66, âge moyen 13,9 ans).

> ⚠️ **34,9 % du parc n'est pas calculable** faute de date de mise en service (complétude : date MES
> 45,1 %, référence SYPEMI 69,3 %). Tout chiffre d'âge ou de criticité doit être lu avec ce taux à
> côté — c'est pourquoi la complétude est exposée dans le rapport lui-même.
>
> Nuance : « dépassés » vaut 210 côté KPI et 198 côté criticité. Les deux ne mesurent pas la même
> chose : le KPI s'appuie sur la durée de vie restante (qui peut venir du prestataire), la criticité
> sur le rapport âge/référence SYPEMI (qui exige une date de MES **et** une référence).
Un endpoint d'agrégation (ex. `GET /api/cvc/parc-technique`) exposant, avec filtres
(bâtiment / famille / prestataire) : effectifs, **pyramide des âges**, répartition par
criticité (`< 50 %` / `50-80 %` / `80-100 %` / dépassé), équipements **en fin de vie sous 5 ans**,
taux de complétude de la donnée (date MES, référence SYPEMI). S'appuie sur `_compute_lifecycle`
existant — pas de recalcul à réinventer.

**Incrément 3 — Page `/refonte-v1/technique`**
Sur le patron `FluidsElecDetailV1` (design system po2) : KPI parc, pyramide des âges,
criticité par bâtiment, top équipements à renouveler, complétude de la donnée,
+ accès aux écrans d'import/mapping/F-Gas existants (pattern « embed » PR #42, sans réécriture).

**Incrément 4 — Plan de renouvellement (optionnel, à cadrer)**
Projection pluriannuelle des remplacements ; nécessite un **coût de remplacement** par famille,
qui n'existe pas aujourd'hui dans le modèle.

---

## 7. Arbitrages — tranchés le 2026-08-17

| # | Question | Décision |
|---|---|---|
| 1 | Ordre des travaux | ✅ **Rattachement d'abord**, puis agrégation, puis page refonte. Les indicateurs doivent être justes dès leur première version. |
| 2 | Périmètre | ✅ **CVC uniquement** (chauffage / ventilation / climatisation). Pas de généralisation du modèle à d'autres familles techniques pour l'instant. |
| 4 | Unité de l'état du parc | ✅ **Nombre d'équipements** (donnée complète à 100 %). La puissance installée n'est pas retenue comme unité de pilotage à ce stade. |

### Restent ouvertes (à trancher au moment de l'incrément 2)

3. **Les 708 « Autre à qualifier »** : les exclure des analyses par typologie, les afficher dans
   un bac « à qualifier » à traiter, ou tenter une reclassification automatique depuis la désignation ?
5. **Durée de vie** : on conserve l'arbitrage actuel (SYPEMI calculé prioritaire, valeur prestataire
   en repli) ? Faut-il pouvoir **corriger manuellement** une date de MES ou un état de santé ?
6. **F-Gas** : le volet fluides frigorigènes reste-t-il une page à part, ou devient-il un onglet
   de l'état technique ?
7. **Renouvellement chiffré** (incrément 4) : le veut-on à terme, et si oui, d'où viendraient les
   coûts de remplacement (BPU marché, ratio par famille, saisie manuelle) ?
