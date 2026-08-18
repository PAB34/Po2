---
type: decisions
statut: cadrage — decisions Q1-Q8 prises, Q9-Q14 ouvertes
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

## 5. Décisions prises (2026-08-18)

| # | Question | Décision |
|---|---|---|
| Q1 | Où vit le `CODE_BIEN` ? | **Table dédiée** — un bâtiment peut porter plusieurs codes bien (plusieurs locaux dans un même bâtiment). Relation **N codes bien → 1 bâtiment**. |
| Q2 | Périmètre importé | **En attente** — à valider avec la personne référente du fichier (`Feuil1` contient beaucoup de choses hors bâti). Le socle est conçu pour `GENRE=BATI`, extensible. |
| Q3 | Cible du rattachement | **`Building` uniquement.** Les `Site` ne sont pas des cibles. ⚠️ Chantier connexe pressenti : **suppression des sites** du listing plateforme (à cadrer séparément, action destructive). |
| Q4 | Biens hors Sète | **Non traités.** Exclus du périmètre de travail. |
| Q5 | Auto-rattachement | **Oui, rattachement automatique des évidences**, avec **modification manuelle toujours possible** ensuite. |
| Q6 | Déplacement du point | **Recalcul + proposition** de l'adresse par géocodage inverse ; l'utilisateur valide. Jamais d'écrasement silencieux. |
| Q7 | Écran | **Un seul écran** portant tout le parcours (liste + rapprochement + carte + attribution IGN). |
| Q8 | Nature du flux | **Aller-retour ASTECH.** Export ASTECH → import Po2 → traitement bâtiment par bâtiment → **réexport enrichi** (nom + adresse + cadastre) réinjectable dans ASTECH, **et** mise à jour de la base patrimoniale Po2. |

### Ce que Q8 change dans la conception

Ce n'est **pas un import de reprise** mais un **cycle rejouable**. Conséquences directes :

1. Le `CODE_BIEN` est la **clé pivot permanente** de réinjection — pas un simple attribut de traçabilité.
2. Il faut **conserver les 317 colonnes d'origine** de chaque ligne pour pouvoir réémettre un
   fichier au même format (ASTECH doit le relire).
3. Chaque champ enrichi doit être **écrit dans la colonne ASTECH correspondante**, pas seulement
   dans le modèle Po2.
4. Le traitement doit être **idempotent** : réimporter le même export ne doit pas dupliquer les
   biens ni perdre les rapprochements déjà validés.

### Périmètre effectif après Q4 (mesuré sur les 399 bâtiments actifs)

| Classement | Lignes | Sort |
|---|---|---|
| Sète (`COMMUNE=34301` ou `VILLE=SETE`) | **332** | traité |
| Hors Sète (Frontignan, Mèze, Marseillan, Balaruc, Bouzigues, Villeveyrac, Montbazin) | **26** | exclu (Q4) |
| Commune absente | **41** | **traité malgré tout** — voir ci-dessous |

⚠️ Les 41 lignes sans commune sont **en très grande majorité sétoises** : `WC PUBLICS SAINT CLAIR`,
`WC PUBLICS PIERRES BLANCHES`, `RESTAURATION LOUISE MICHEL`, `PARKING SOUS LE CANAL`,
`MAISON GARDE BARRIERE VILLEROY`… Appliquer Q4 littéralement (« pas de commune ⇒ on écarte »)
**supprimerait 41 bâtiments légitimes**. Règle retenue : **on n'exclut que les 26 explicitement
hors Sète** ; les 41 indéterminés entrent dans le flux et leur commune sera tranchée par
l'attribution IGN. Seules 3 d'entre elles sont douteuses (`OFFICE DU TOURISME DE MEZE`,
`HOTEL D'AGGLO`, `ISSANKA - ABANDON`) et ressortiront naturellement au traitement.

**Périmètre de travail : 373 bâtiments.**

## 6. Correspondance des colonnes pour le réexport ASTECH

Formats **relevés sur le fichier réel**, pas supposés.

| Colonne ASTECH | Format constaté | Source Po2 | Remarque |
|---|---|---|---|
| `CODE_BIEN` / `CODBAR` | `ADMIANMAI02` | *(clé pivot)* | jamais modifié |
| `DESIGNATION` / `NOMCOURT` | libellé libre | `nom_batiment` | voir **Q11** |
| `NORUE` | `'20'`, `'81'` (texte) | `numero_voirie` | `0` = non renseigné |
| `BISTER` | **`RUE`, `BD`, `AVE`, `QUA`, `IMP`, `CHE`** (185 cas) et `BIS` (3 cas) | ? | **piège — voir Q9** |
| `LIBELVOIE` | tantôt `RUE JEAN VILAR`, tantôt `JEAN JAURES` | `nature_voie` + `nom_voie` | **incohérent — voir Q10** |
| `CODPOST` | `34200` | `code_postal` | |
| `VILLE` | `SETE` | `nom_commune` | |
| `COMMUNE` | **`34301`** (code INSEE) | code INSEE | plus fiable que `VILLE` |
| `REFCAD` | **`AS023`, `AZ232`** = section (2) + n° plan (3, zéro-comblé) | `section` + `numero_plan` | concaténation directe |
| `LATITUDE` / `LONGITUDE` | **`'43,436176'` — virgule décimale, texte** | `latitude` / `longitude` | **conversion obligatoire au réexport** |
| `CADSURF`, `INVARIANT`, `GEOLOC` | vides partout | — | à alimenter ou à ignorer |

> Deux pièges confirmés :
> **(a)** `BISTER` est **détourné de son usage** : la colonne devrait porter bis/ter, elle porte le
> **type de voie** dans 185 cas sur 188.
> **(b)** `LIBELVOIE` contient parfois le type de voie, parfois non — donc le couple
> `BISTER` + `LIBELVOIE` produit aujourd'hui aussi bien `RUE / RUE LACAN` que `RUE / JEAN JAURES`.
> Réinjecter sans règle explicite créerait des « RUE RUE LACAN ».

## 7. Architecture cible

```
   ASTECH ──export──▶ [1] Import + normalisation (GENRE, HORSPARC, commune)
                            │        réutilise preview_building_import_file
                            ▼
                      [2] Table `patrimoine_legacy_assets`
                          code_bien (clé unique) · payload 317 colonnes conservé
                          · building_id (N→1) · statut · score · lat/lon proposés
                            │
                            ▼
                      [3] Candidats ── _site_similarity (cvc.py, déjà en prod)
                          + départage commune / voie (bonus, jamais moyenne)
                            │
                            ▼
                      [4] ÉCRAN UNIQUE  (décision Q7)
                          liste à gauche · carte à droite · panneau d'action
                          ├─ évidences déjà rattachées (Q5), modifiables
                          ├─ candidats à valider / corriger
                          ├─ point posé, couleur dédiée, déplaçable (Q6)
                          └─ bouton « Attribuer IGN » → POST /ign-attachment
                                                       + /geo-attachment  (existants)
                            │
                            ▼
                      [5] Mise à jour base patrimoniale Po2
                            │
                            ▼
   ASTECH ◀──réexport── [6] Réémission du classeur au format d'origine
                            (nom + adresse + cadastre + lat/lon écrits
                             dans les colonnes ASTECH, cf. §6)
```

Briques **déjà existantes** : [1] partiellement, [3], et tout le back de [4] (`ign-attachment`,
`geo-attachment`, `free-address`, `nearby-dgfip`).
Briques **à construire** : [2], la table de rapprochement, le **marqueur déplaçable**,
l'**écran unique**, et **[6] le réexport** (entièrement neuf).

## 8. Questions ouvertes restantes

**Q9 — `BISTER` au réexport : on écrit quoi ?**
(a) le **type de voie** (`RUE`, `BD`…) pour rester cohérent avec l'usage réel de tes agents ;
(b) le **bis/ter** (usage théorique de la colonne), au risque de casser leurs habitudes ;
(c) on n'y touche pas du tout.
→ **Recommandation : (a)** — le fichier doit rester lisible par ceux qui l'utilisent au quotidien.

**Q10 — `LIBELVOIE` : avec ou sans le type de voie ?**
Aujourd'hui c'est incohérent (`RUE LACAN` vs `JEAN JAURES`). Si Q9 = (a), alors `LIBELVOIE` doit
contenir **le nom de voie seul**, sinon on produira « RUE RUE LACAN ». On **normalise donc aussi
les lignes déjà remplies**, ou on ne réécrit que celles qu'on a enrichies ?

**Q11 — Le nom : ASTECH gagne ou IGN gagne ?**
Quand l'attribution IGN propose un nom (`EX TRIBUNAL D'INSTANCE`) différent du nom ASTECH
(`EX TRIBUNAL`), on réexporte lequel dans `DESIGNATION` / `NOMCOURT` ?
→ **Recommandation : on garde le nom ASTECH** (c'est la clé de reconnaissance de tes agents) et
on stocke le nom IGN à côté dans Po2. Sinon le prochain import ne reconnaîtra plus rien.

**Q12 — Format du réexport.**
(a) le **classeur complet 317 colonnes**, colonnes enrichies mises à jour en place (réinjectable
tel quel dans ASTECH) ;
(b) une **feuille réduite** `CODE_BIEN + champs modifiés` (plus lisible, mais suppose qu'ASTECH
sache faire une mise à jour par clé).
→ **Recommandation : (a)**, sauf si la personne référente ASTECH confirme que (b) est accepté en
import. **À vérifier avec elle en même temps que Q2.**

**Q13 — Les bâtiments connus de Po2 mais absents d'ASTECH.**
Po2 a 212 bâtiments, dont certains n'auront aucun code bien. Doivent-ils **remonter dans l'export**
comme lignes nouvelles (sans `CODE_BIEN`, à créer côté ASTECH), ou l'export ne contient-il que
les biens déjà connus d'ASTECH ?

**Q14 — Suppression des sites (évoqué en Q3).**
Chantier séparé et **destructif** : 151 sites en prod, avec des bâtiments rattachés par `site_id`
et un modèle hiérarchique `SITE → BATIMENT → LOCAL` utilisé par d'autres modules (import CVC,
rapprochements compteurs). À cadrer dans son propre document avant toute suppression.
