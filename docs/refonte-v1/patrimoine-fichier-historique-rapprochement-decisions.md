---
type: decisions
statut: cadrage — questions ouvertes
sujet: Rapprochement du fichier patrimoine historique de la collectivité (CODE_BIEN) avec le référentiel Po2 (/buildings/list)
créé: 2026-08-18
related:
  - Modules/Patrimoine.md
  - Decisions/008-referentiel-patrimoine-et-rapprochements.md
---

# Fichier patrimoine historique ↔ référentiel Po2 — audit & décisions

> Règle « fil du dev » : ce document est écrit **avant** de coder. Il recense ce qui existe
> **déjà vérifié** (backend + frontend + données prod), les mesures réelles, et les questions
> ouvertes numérotées à trancher.

## 1. Le besoin exprimé (2026-08-18)

La collectivité dispose d'un **second référentiel patrimoine**, historique, tenu hors Po2
(`V:\CTM\Public\CTM BATIMENTS\SOEM\PATRIMOINE\Liste BATIMENTS TRAITES.xlsx`). Il est la clé
d'entrée métier des agents (le fameux **CODE_BIEN**), mais il n'a **ni n° de voirie fiable,
ni cadastre, ni géolocalisation**, et ses libellés (`DESIGNATION`, `NOMCOURT`) ne coïncident
pas exactement avec ceux de Po2. Il contient aussi des biens **sortis d'usage jamais supprimés**.

Cible demandée :

1. **Importer** ce fichier dans Po2 ;
2. **Reconnaissance automatique des noms** avec **validation utilisateur** (comme le mapping
   des équipements DALKIA vers les bâtiments) ;
3. **Afficher ces biens sur la carte** avec une **couleur dédiée**, pouvoir **sélectionner le
   point et le déplacer** → l'adresse se recalcule ;
4. Bouton **« Attribuer IGN »** → on lui attribue un bâtiment IGN et **adresse + n° + cadastre**
   sont récupérés, exactement comme l'attachement IGN existant de `/buildings/list`.

## 2. Le fichier source — ce qu'il contient réellement (analysé le 2026-08-18)

Export type **CIRIL / gestion de patrimoine** : 317 colonnes, 2 feuilles.

| Feuille | Lignes | Remarque |
|---|---|---|
| `Feuil1` | 866 | **`CODE_BIEN` est rempli** (ex. `ADMIANMAI02`) |
| `BAT` | 444 | `CODEBIEN` vide, mais **`CODBAR` porte le même code** |

> ⚠️ **Le code bien n'est pas perdu.** Il est présent en colonne A de `Feuil1` **et** dans la
> colonne `CODBAR` des deux feuilles (863/866 lignes où `CODBAR == CODE_BIEN`).
> Un nouvel export reste utile pour confirmer, mais **il ne bloque pas le chantier**.

**Répartition (`GENRE` × `HORSPARC`)**

| GENRE | Actifs (`HORSPARC=N`) | Sortis (`HORSPARC=O`) |
|---|---|---|
| `BATI` (bâtiments) | **399** | 43 |
| `EV` (espaces verts) | 285 | 0 |
| `CPTEL` (compteurs élec) | 0 | 126 |
| `AIRJE` (aires de jeux) | 9 | 0 |
| `SITE` / `TER` / `CPTEA` | 2 | 2 |

→ **`HORSPARC` est déjà le drapeau « n'est plus utilisé »** : 171 lignes au total, dont 43 bâtiments.
Le fichier n'a donc pas besoin d'un nettoyage manuel préalable, il suffit de filtrer.

**Catégories des 399 bâtiments actifs** : ADMINISTRATIF 129 · SOCIAL 87 · SPORTS 41 ·
SANITAIRES ET PLAGES 37 · CULTUREL 27 · SCOLAIRE 27 · RESTAURANT 21 · ENFANCE ET LOISIRS 12 ·
CULTUEL 7 · VOIE 7.

**Qualité des colonnes utiles au rapprochement** (sur 866 lignes)

| Colonne | Rempli | Verdict |
|---|---|---|
| `DESIGNATION` / `NOMCOURT` | 866 | seul axe de matching fiable |
| `LIBELVOIE` (nom de voie) | 615 | exploitable en **départage**, pas en clé |
| `NORUE` (n° voirie) | 114 | quasi inutilisable (le reste vaut `0`) |
| `CODPOST` / `VILLE` | 651 / 652 | utile pour filtrer la commune |
| `REFCAD` (cadastre) | **2** | inexploitable |
| `INVARIANT`, `GEOLOC`, `CADSURF`, `SHON` | **0** | vides |
| `LATITUDE` / `LONGITUDE` | **1** | vides |
| `CODE_PARENT` | 274 (dont 80 `BATI`) | hiérarchie interne (ex. logement de fonction ⊂ école) |

**Périmètre communal** : 345 bâtiments à SÈTE, **24 hors Sète** (Frontignan 8, Mèze 4,
Marseillan 3, Balaruc-les-Bains 3, Bouzigues 2, Villeveyrac 2, Balaruc-le-Vieux 1, Montbazin 1
— principalement des déchetteries, donc du périmètre **Agglo**), **71 sans commune**.
Ces lignes n'ont aucune contrepartie possible dans la base DGFIP de la Ville de Sète.

## 3. L'existant Po2 — vérifié dans le code, pas supposé

### 3.1 Ce qui est DÉJÀ construit et fonctionnel

| Besoin exprimé | Existant | Emplacement |
|---|---|---|
| Attribuer IGN → récupère adresse/cadastre | **`POST /api/buildings/{id}/ign-attachment`** + mode « attachement IGN » sur la carte (polygones jaunes cliquables) | `api/routes/buildings.py:345`, `services/buildings.py:317`, `pages/BuildingsListPage.tsx` (`attachMode`) |
| Rattacher une adresse DGFIP complète (n° + section + parcelle) | **`POST /api/buildings/{id}/geo-attachment`** + `GET /{id}/nearby-dgfip` | `services/buildings.py:243`, `building_naming.py:1410` |
| Géocoder une adresse libre → point + parcelles + bâtiments IGN | **`POST /api/buildings/lookup/free-address`** | `building_naming.py:1124` (`lookup_free_address_candidates`) |
| Importer un fichier de biens (aperçu + géocodage en masse) | **`POST /api/buildings/import/preview`** — gère déjà typologie SITE/BÂTIMENT/LOCAL, parent, parcelle, **code bâtiment**, étage, porte | `building_naming.py:961` (`preview_building_import_file`) |
| Moteur de rapprochement avec file d'attente + validation | **`PatrimoineMatchItem`** (statuts `a_traiter` / `lie` / `ignore` / `a_creer`, candidat + score + `bulk-link ≥ 90`) | `models/patrimoine_match.py`, `services/patrimoine_match.py`, `pages/PatrimoineMatchPage.tsx` |
| Reconnaissance de noms avec garde-fous sémantiques | **`_site_similarity()`** : refuse « STADE X » ↔ « RESTAURANT X », et « CIMETIERE MARIN » ↔ « CIMETIERE LE PY » | `services/cvc.py:308` |
| Table de mapping « libellé source → bâtiment » validée par l'utilisateur | **`CvcSourceBuildingMapping`** (`status=to_review`, `match_score`, `match_method`) + écran dédié | `models/cvc.py:110`, `pages/CvcSiteMappingPage.tsx` — **c'est le précédent cité par l'utilisateur** |
| Carte Leaflet du parc | **`BuildingPortfolioMap.tsx`** (579 l.) : `circleMarker` par bâtiment, polygones IGN attachés, mode attachement | `components/BuildingPortfolioMap.tsx` |

### 3.2 Ce qui MANQUE réellement

1. **Aucun champ `code_bien`** sur le modèle `Building` (le `source_building_code` de l'import
   n'est aujourd'hui pas persisté ; il finit dans `majic_building_values_json`).
2. **`PatrimoineMatchItem` ne connaît que 2 sources** : `ENEDIS_PRM`, `GRDF_PCE`. Il faut une
   source de type « bien du référentiel historique ».
3. **Pas de marqueur déplaçable** sur la carte : `BuildingPortfolioMap` n'utilise que
   `circleMarker` (aucun `draggable` / `dragend` dans le code). Le « déplacer le point →
   l'adresse se met à jour » est **à construire** (mais le back existe : `free-address` en
   sens inverse, et `_resolve_point_and_parcels` sait déjà partir d'un point).
4. **Le pipeline d'import crée, il ne réconcilie pas** : `preview_building_import_file` ne
   compare jamais les lignes du fichier au parc déjà en base.

## 4. Mesure réelle du taux de reconnaissance (fait le 2026-08-18, pas estimé)

Simulation en rejouant **l'algorithme `_site_similarity` déjà en production** :
399 bâtiments actifs du fichier historique × 363 cibles Po2 (**212 bâtiments + 151 sites**,
comptés en base prod le 2026-08-18).

| Score du meilleur candidat | Lignes | Part |
|---|---|---|
| ≥ 0,90 — rattachement automatique proposé | **92** | 23 % |
| 0,70–0,90 — à valider à l'œil | **112** | 28 % |
| 0,50–0,70 — douteux | 102 | 26 % |
| < 0,50 — aucun candidat | 93 | 23 % |

Exemples corrects : `CIMETIERE LE PY` → `CIMETIERE LE PY` (1,0) · `EX TRIBUNAL` →
`EX TRIBUNAL D'INSTANCE` (1,0) · `MARCHE DES HALLES` → `HALLES CENTRALES` (0,87).
Faux amis typiques : `DECHETTERIE MEZE` → `DECHETTERIE SETE` (0,88) — la commune départagerait ;
`LOCAL 8 RUE JEAN VILAR` → `LOCAL ASSOCIATIF 24 RUE HENRI BARBUSSE` (0,53) — l'adresse départagerait.

**Test complémentaire** : mélanger le nom et la voie dans un score pondéré (0,65 × nom +
0,35 × voie) **dégrade** le résultat (92 → 60 auto), parce que 69 lignes n'ont pas de voie et
que les adresses Po2 sont écrites autrement. ⇒ **l'adresse et la commune doivent servir de
bonus/départage entre candidats ex æquo, jamais de moyenne pondérée.**

### Conséquence structurante

Le parc Po2 (212 bâtiments) est **plus petit** que le fichier historique (399 bâtiments actifs).
Le chantier n'est donc **pas** « rapprocher deux listes de même taille » : c'est
**« rapprocher ce qui existe, et créer/localiser le reste »**. Environ la moitié des lignes
n'aura pas de contrepartie et devra passer par le parcours carte + attachement IGN.
C'est exactement ce que l'utilisateur a décrit — le besoin est bien posé.

## 5. Architecture proposée (à valider)

Réutilisation maximale, **zéro réécriture** :

```
Excel historique ──▶ [1] Import & normalisation
                       (réutilise preview_building_import_file, + colonnes CIRIL)
                             │
                             ▼
                   [2] Table `patrimoine_legacy_assets`
                       code_bien (clé), designation, nomcourt, genre, categ,
                       horsparc, voie/ville, code_parent, building_id?, lat/lon?
                             │
                             ▼
                   [3] Moteur de candidats  ── réutilise `_site_similarity`
                       + départage commune/voie          (cvc.py, déjà en prod)
                             │
                             ▼
                   [4] File de validation ── réutilise le pattern
                       `PatrimoineMatchItem` (nouvelle source `LEGACY_CODE_BIEN`)
                       ou une table jumelle de `CvcSourceBuildingMapping`
                             │
              ┌──────────────┴───────────────┐
              ▼                              ▼
   [5a] « C'est ce bâtiment »       [5b] « Aucun candidat »
        → code_bien rattaché             → point posé sur la carte (couleur dédiée),
                                            déplaçable, puis « Attribuer IGN »
                                            → réutilise POST /ign-attachment
                                              et /geo-attachment tels quels
```

Les briques [1], [3], [5b] existent déjà ; l'effort réel porte sur [2], [4] et le
**marqueur déplaçable** de la carte.

## 6. Questions ouvertes — à trancher avant de coder

**Q1 — Où vit le `CODE_BIEN` une fois validé ?**
(a) nouvelle colonne `code_bien` sur `buildings` (simple, mais 1 code ↔ 1 bâtiment strict) ;
(b) table de liaison dédiée `patrimoine_legacy_assets` (permet plusieurs codes bien sur un même
bâtiment, garde la trace des biens sans contrepartie, et conserve les 317 colonnes d'origine).
→ **Recommandation : (b)**, cohérent avec `CvcSourceBuildingMapping` et avec la règle
« aucun objet introuvable ne disparaît » de l'ADR 008.

**Q2 — Quel périmètre importe-t-on ?**
(a) uniquement `GENRE=BATI` et `HORSPARC=N` (399 lignes) ;
(b) tous les `BATI` y compris sortis du parc (442), les sortis affichés grisés ;
(c) tout (866, avec espaces verts, aires de jeux, compteurs).
→ Les 126 `CPTEL` sont des compteurs électriques **tous sortis du parc** ; Po2 gère déjà les PRM
par ailleurs — a priori hors sujet. Mais les 285 espaces verts sont peut-être un vrai besoin futur.

**Q3 — La cible d'un rattachement, c'est quoi ?**
Un `Building`, un `Site`, ou les deux ? Po2 a 151 sites et 212 bâtiments ; la simulation montre
que certains codes bien collent mieux à un site (`CCAS`) qu'à un bâtiment.
→ Le moteur `patrimoine_match` sait déjà gérer `target_type = building | site`.

**Q4 — Les 24 biens hors Sète (déchetteries Agglo) : on les importe ?**
Ils n'auront jamais de contrepartie DGFIP dans le périmètre Ville. Les marquer
« hors périmètre » plutôt que les laisser en échec de rapprochement ?
(Rejoint la question ouverte « Ville seule vs Ville + Agglo » du référentiel PRM ENEDIS.)

**Q5 — Seuil d'auto-validation.**
`patrimoine_match` fait du `bulk-link` à ≥ 90. Ici cela rattacherait 92 lignes d'un coup.
Veux-tu (a) ce bouton « rattacher les évidences » d'emblée, ou (b) une validation
100 % manuelle pour le premier passage, quitte à l'activer ensuite ?
→ **Recommandation : (b) pour le premier passage** — la simulation montre des faux amis à 0,88
(`DECHETTERIE MEZE` → `DECHETTERIE SETE`), donc un seuil de 0,90 n'est pas sûr **tant que le
départage par commune n'est pas branché**.

**Q6 — Déplacement du point : quel niveau d'automatisme ?**
Quand on lâche le marqueur, on (a) recalcule seulement le couple lat/lon, (b) recalcule aussi
l'adresse par géocodage inverse et on la **propose**, (c) on l'écrase directement.
→ **Recommandation : (b)** — cohérent avec le reste de la plateforme, qui propose toujours et
fait valider (`ign_name_proposed`, `validation_message`…).

**Q7 — Où vit l'écran ?**
(a) nouvel onglet dans `/patrimoine/rapprochements` (l'écran de file existe déjà) ;
(b) nouvel onglet dans `/buildings/list` (là où vivent la carte et l'attachement IGN) ;
(c) écran dédié `/patrimoine/import-historique`.
→ La partie « valider les noms » va naturellement en (a), la partie « poser/déplacer le point +
attribuer IGN » va naturellement en (b). Un écran unique obligerait à dupliquer la carte.

**Q8 — Le nouvel export avec `CODE_BIEN`.**
Il est **déjà exploitable en l'état** (§2). Faut-il quand même attendre le nouvel export, ou
démarre-t-on sur ce fichier ? Autre question : cet export sera-t-il **rejouable
périodiquement** (donc il faut gérer les mises à jour et les nouveaux biens), ou est-ce
un **one-shot** de reprise ?

## 7. Décisions prises

*(à compléter au fil des réponses)*

| Date | Question | Décision |
|---|---|---|
| — | — | — |
