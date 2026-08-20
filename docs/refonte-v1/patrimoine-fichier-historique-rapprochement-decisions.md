---
type: decisions
statut: en cours — ecran ASTECH en prod ; cible du rattachement (Q15-Q17) a trancher
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

## 8. Questions ouvertes restantes *(repondues — voir §9)*

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

## 9. Décisions complémentaires — 2e passe (2026-08-18)

| # | Question | Décision |
|---|---|---|
| Q9 | `BISTER` au réexport | **Bis/ter uniquement, quand l'information existe.** La colonne retrouve son usage légitime. |
| Q10 | `LIBELVOIE` | **On normalise tout** — y compris les lignes déjà remplies. |
| Q11 | Nom ASTECH vs nom IGN | **Le nom IGN gagne et est réécrit dans ASTECH** (`EX TRIBUNAL` → `EX TRIBUNAL D'INSTANCE`). Objectif assumé : la plateforme met ASTECH à jour. |
| Q12 | Format du réexport | **En attente** — exemple concret fourni §9.3, à valider avec la référente ASTECH en même temps que Q2. |
| Q13 | Bâtiments Po2 absents d'ASTECH | **Lignes à créer** — ils remontent dans l'export sans `CODE_BIEN`, à créer côté ASTECH. |

### 9.1 Règle d'adresse dérivée de Q9 + Q10

Q9 vide `BISTER` de son contenu actuel (le type de voie). Ce type doit donc aller
**dans `LIBELVOIE`** — c'est la seule colonne qui puisse l'accueillir. Cette règle est
**imposée par Q9**, elle n'est pas un choix supplémentaire.

Usage constaté dans le fichier (615 lignes renseignées) : `LIBELVOIE` écrit le type de voie
**en toutes lettres** dans **425 cas** — `RUE` 177, `QUAI` 46, `AVENUE` 43, `PLACE` 37,
`BOULEVARD` 36, `CHEMIN` 28, `PROMENADE` 18, `IMPASSE` 17, `CORNICHE` 9, `ROUTE` 7.
Les 190 lignes restantes sont précisément celles où `BISTER` portait l'abréviation.

**Règle de normalisation retenue :**

| Colonne | Contenu après normalisation | Exemple |
|---|---|---|
| `NORUE` | numéro de voirie seul | `17` |
| `BISTER` | `BIS` / `TER` uniquement, sinon vide | *(vide)* |
| `LIBELVOIE` | **type de voie en toutes lettres + nom** | `RUE LACAN` |

Avant / après sur des lignes réelles :

| `NORUE` | `BISTER` | `LIBELVOIE` | → | `NORUE` | `BISTER` | `LIBELVOIE` |
|---|---|---|---|---|---|---|
| `17` | `RUE` | `ANDRE PORTES` | → | `17` | | `RUE ANDRE PORTES` |
| `81` | `BD` | `CAMILLE BLANC` | → | `81` | | `BOULEVARD CAMILLE BLANC` |
| `10` | `AVE` | `MARX DORMOY` | → | `10` | | `AVENUE MARX DORMOY` |
| `15` | `RUE` | `BIS LUCIEN SALETTE` | → | `15` | `BIS` | `RUE LUCIEN SALETTE` |
| `17` | `RUE` | `RUE LACAN` | → | `17` | | `RUE LACAN` *(déjà bon)* |

Le DGFIP/IGN livre des abréviations (`AV`, `IMP`, `BD`, `QUAI`) — une table d'expansion vers
les formes longues d'ASTECH est nécessaire : `AV`/`AVE` → `AVENUE`, `BD` → `BOULEVARD`,
`IMP` → `IMPASSE`, `CHE` → `CHEMIN`, `QUA` → `QUAI`, `PRO` → `PROMENADE`, `RTE` → `ROUTE`,
`PL` → `PLACE`, `ALL` → `ALLEE`.

### 9.2 Q11 : l'objection que j'avais soulevée tombe

J'avais recommandé de conserver le nom ASTECH, au motif qu'un renommage casserait la
reconnaissance au prochain import. **Cette objection ne tient plus** compte tenu de Q1 :
le `CODE_BIEN` est stocké en base comme clé pivot, donc les imports suivants rapprochent
**par code, pas par nom**. Le matching par nom ne sert qu'au **premier cycle**. Renommer est
donc sans risque — et fait même converger les deux référentiels cycle après cycle.

### 9.3 Q12 expliqué — les deux formats de réexport

Prenons une ligne réelle, `ADMIANMAI02` (annexe mairie de la Corniche), aujourd'hui sans
cadastre ni coordonnées. Après traitement dans Po2, on connaît son adresse exacte, sa parcelle
et son point GPS. La question est : **à quoi ressemble le fichier qu'on rend à ASTECH ?**

**Option A — le classeur complet, modifié en place**

On rend le **même fichier** : 866 lignes × 317 colonnes, à l'identique, sauf les cellules
enrichies qui ont été mises à jour. Les 300 colonnes qui ne nous concernent pas
(`ERP_*`, `AMORT_*`, `PRIX_ACHAT`…) sont **recopiées telles quelles**.

```
CODE_BIEN | DESIGNATION            | ... | NORUE | BISTER | LIBELVOIE           | CODPOST | VILLE | COMMUNE | REFCAD | LATITUDE   | ... (300 autres colonnes inchangées)
ADMIANMAI02 | ANNEXE MAIRIE ... MER | ... |  20   |        | CORNICHE DE NEUBURG | 34200   | SETE  |  34301  | AS023  | 43,404512  | ...
```

→ ASTECH **réimporte le fichier entier**, comme il l'a exporté.
→ Avantage : aucune ambiguïté, c'est son propre format. Inconvénient : gros fichier, et on
réécrit des colonnes qu'on n'a pas touchées (risque théorique d'écraser une modif faite dans
ASTECH entre-temps).

**Option B — une feuille réduite**

On rend **uniquement la clé et les champs qu'on a modifiés** :

```
CODE_BIEN   | NORUE | BISTER | LIBELVOIE           | CODPOST | VILLE | COMMUNE | REFCAD | LATITUDE  | LONGITUDE
ADMIANMAI02 |  20   |        | CORNICHE DE NEUBURG | 34200   | SETE  |  34301  | AS023  | 43,404512 | 3,693845
CULRMUSEE02 |  148  |        | RUE FRANCOIS DESNOYER | 34200 | SETE  |  34301  | AS023  | 43,398211 | 3,695012
```

→ ASTECH fait une **mise à jour par clé** : « pour le bien `ADMIANMAI02`, remplace ces 9 champs ».
→ Avantage : léger, lisible, ne touche à rien d'autre. **Inconvénient : ça ne marche que si
ASTECH sait faire un import de mise à jour par clé** — beaucoup d'outils de gestion patrimoniale
n'acceptent qu'un fichier au format complet.

**C'est la seule question à poser à la référente : « ASTECH sait-il réimporter une mise à jour
par CODE_BIEN, ou faut-il lui rendre le classeur complet ? »**
→ **Recommandation : partir sur (A)**, qui marche dans tous les cas, et basculer en (B)
seulement si elle confirme que l'import par clé existe.

### 9.4 Constat bloquant à lever : les champs d'adresse structurés sont vides en prod

Vérifié en base prod le 2026-08-18 sur les 212 bâtiments :

| Champ `buildings` | Rempli |
|---|---|
| `adresse_reconstituee` | 177 |
| `dgfip_reference_norm` | 163 |
| `numero_voirie`, `nature_voie`, `nom_voie` | **0** |
| `section`, `numero_plan`, `indice_repetition` | **0** |

Les bâtiments actuels viennent de l'import en masse, qui ne renseigne que l'adresse en une
seule chaîne et la référence de parcelle normalisée. **Les composants structurés dont le
réexport a besoin ne sont donc pas alimentés aujourd'hui.**

La donnée n'est pas perdue pour autant, elle est juste agrégée :

```
adresse_reconstituee  = "0002 Impasse DE LA BORDIGUE"
dgfip_reference_norm  = "34301000AI0009"
                         └INSEE┘└pfx┘└se┘└plan┘
```

Deux voies pour alimenter l'export, à trancher au moment de coder (pas bloquant pour le
cadrage) : **(i)** parser ces deux chaînes — le format est parfaitement régulier — ou
**(ii)** renseigner les champs structurés au fil de l'eau à chaque attribution IGN/DGFIP faite
dans le nouvel écran. **(ii) est plus propre et se fait naturellement** puisque chaque bien
traité passe par l'attribution ; **(i)** sert de rattrapage pour les bâtiments déjà en base.

⚠️ Point de format à confirmer : `REFCAD` fait 5 caractères dans les 2 exemples observés
(`AS023` = section sur 2 + plan sur 3), alors que Po2 stocke le plan sur **4** chiffres
(`AI0009`). Pour les parcelles dont le numéro de plan dépasse 999, il faut savoir si ASTECH
accepte un `REFCAD` plus long. **À confirmer avec la référente.**

## 10. Reste à trancher avant de coder *(mis a jour au §12)*

- **Q2** — périmètre importé (référente ASTECH).
- **Q12** — format du réexport, complet ou par clé (référente ASTECH) — cf. §9.3.
- **Largeur de `REFCAD`** (référente ASTECH) — cf. §9.4.
- **Q14** — suppression des sites : chantier séparé, destructif, non démarré.

## 11. Décisions 3e passe (2026-08-18) — format de sortie et règle d'écriture

| # | Question | Décision |
|---|---|---|
| Q12 | Format du réexport | **Feuille réduite** : clé `CODE_BIEN` + les seuls champs que Po2 maîtrise. Option A (classeur complet) conservée en **repli**, cf. §11.3. |
| Q9 | `BISTER` | **Bis/ter uniquement** — confirmé, et c'est aussi ce que livre nativement le DGFIP (`indice_repetition`). |
| Q10 | `LIBELVOIE` | **Normalisation complète** vers *type de voie en toutes lettres, en majuscules* + nom. |

**Principe directeur retenu (formulé par l'utilisateur)** : les champs ASTECH se remplissent
**depuis ce que la plateforme récupère via l'IGN/DGFIP**. C'est donc la structure de la donnée
DGFIP qui dicte la correspondance, et non les habitudes de saisie du fichier historique.

### 11.1 Pourquoi Q9 + Q10 sont le bon choix : chaque colonne a une source unique

Le DGFIP livre l'adresse **déjà découpée** — c'est précisément la structure du modèle `Building` :

| Colonne ASTECH | Source DGFIP / Po2 | Ambiguïté |
|---|---|---|
| `NORUE` | `numero_voirie` (zéros de tête retirés : `0002` → `2`) | aucune |
| `BISTER` | `indice_repetition` (`BIS`, `TER`) — **le DGFIP a ce champ** | aucune |
| `LIBELVOIE` | `nature_voie` (développée) + `nom_voie` | aucune |

Chaque colonne ASTECH reçoit **exactement une** source DGFIP, sans arbitrage. C'est ce qui rend
la décision Q9 structurellement juste : garder le type de voie dans `BISTER` aurait obligé à
mélanger deux champs DGFIP distincts (`indice_repetition` et `nature_voie`) dans une seule
colonne, et à décider lequel sacrifier quand les deux existent (« 15 BIS RUE Lucien Salette »).

### 11.2 Constat : la source DGFIP est elle-même incohérente — la normalisation est obligatoire

Relevé en base prod le 2026-08-18 sur les 177 `adresse_reconstituee` (2ᵉ mot = type de voie) :

```
RUE 67 · BD 16 · AV 11 · QUAI 11 · CHE 7 · Rue 6 · PROM 4 · Quai 3
IMP 2 · RTE 2 · BOULEVARD 2 · Impasse 2 · PROMENADE 1 · Avenue 1 · Passage 1
```

Le même type de voie apparaît sous **trois formes** : `BD` / `BOULEVARD`, `AV` / `Avenue`,
`IMP` / `Impasse`, `RUE` / `Rue`, `PROM` / `PROMENADE`. **Recopier le DGFIP tel quel dans ASTECH
y importerait ce désordre.** Une table de normalisation n'est donc pas un confort, c'est une
condition pour ne pas dégrader leur fichier.

**Forme canonique retenue** — type en toutes lettres, majuscules, sans accent : c'est la
convention majoritaire d'ASTECH (425 lignes sur 615). Table :
`RUE` · `AVENUE` (`AV`, `AVE`) · `BOULEVARD` (`BD`) · `QUAI` (`QUA`) · `CHEMIN` (`CHE`) ·
`IMPASSE` (`IMP`) · `PLACE` (`PL`) · `PROMENADE` (`PROM`, `PRO`) · `ROUTE` (`RTE`) ·
`ALLEE` (`ALL`) · `CORNICHE` · `TRAVERSE` · `PASSAGE` · `MONTEE` · `ESPLANADE`.

⚠️ **Garde-fou obligatoire.** Le relevé contient aussi des valeurs qui ne se découpent pas :
`4674` (un numéro là où le type devrait être) et `QUAIDU` (mot collé). Règle : **on n'écrit dans
la feuille de retour que les adresses qu'on a su normaliser proprement.** Une adresse non
analysable reste **« à vérifier » dans l'écran** et n'est pas exportée. Un aller-retour
automatisé qui écrit à l'aveugle dans le référentiel métier de la collectivité est le vrai
risque de ce chantier.

### 11.3 Feuille réduite — colonnes proposées

Feuille 1, **prête à réimporter** (uniquement des colonnes ASTECH, aucune colonne inventée) :

| `CODE_BIEN` | `DESIGNATION` | `NOMCOURT` | `NORUE` | `BISTER` | `LIBELVOIE` | `CODPOST` | `VILLE` | `COMMUNE` | `REFCAD` | `LATITUDE` | `LONGITUDE` |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `ADMIANMAI02` | `ANNEXE MAIRIE DE LA CORNICHE…` | `ANNEXE MAIRIE CORNICHE` | `20` | | `CORNICHE DE NEUBURG` | `34200` | `SETE` | `34301` | `AS023` | `43,404512` | `3,693845` |

Seules les lignes **effectivement traitées** y figurent. Les biens Po2 sans `CODE_BIEN` (décision
Q13) apparaissent avec la clé vide, à créer côté ASTECH.

Feuille 2, **traçabilité** (ne sert pas à l'import, sert à la relecture humaine) : `CODE_BIEN`,
ancienne valeur → nouvelle valeur pour chaque champ modifié, origine (`IGN` / `DGFIP` / manuel),
score de rapprochement, date. Permet à la référente de contrôler avant de réinjecter.

**Repli technique** : le générateur écrit les mêmes valeurs dans les mêmes colonnes ; produire le
classeur complet (option A) revient à changer le gabarit de sortie, pas la logique. Si ASTECH ne
sait pas faire de mise à jour par clé, la bascule coûte quasiment rien. **À confirmer malgré tout
avec la référente**, car c'est elle qui subira l'échec d'import.

## 12. Reste à trancher *(mis a jour au §14)*

- **Q2** — périmètre importé (référente ASTECH).
- **Confirmation Q12** — ASTECH accepte-t-il un import de mise à jour par `CODE_BIEN` ? (repli prêt)
- **Largeur de `REFCAD`** — 5 caractères observés, Po2 stocke le plan sur 4 chiffres (référente).
- **Q14** — suppression des sites : chantier séparé, destructif, non démarré.

## 13. Contrainte de réinjection ASTECH (2026-08-18)

> **Règle donnée par l'utilisateur** : ASTECH sait modifier **toutes les valeurs** par import du
> fichier modifié, **à condition que le `CODE_BIEN` et les en-têtes de colonnes ne soient pas
> modifiés.**

Conséquences directes sur la conception :

1. **`CODE_BIEN` = clé de mise à jour**, pas seulement clé pivot interne. Il n'est **jamais**
   réécrit, ni normalisé, ni recalculé. Confirme et renforce Q1.
2. **Les en-têtes sont recopiés à l'octet près** depuis le fichier importé — **jamais retapés
   dans le code**. Un `COD_COMPTABLE` devenu `CODE_COMPTABLE`, un `0#SURF` reformaté, et l'import
   ASTECH échoue. Le gabarit d'export est donc **dérivé du fichier source**, pas une constante.
3. Le reste des colonnes étant modifiable, la décision Q11 (réécrire `DESIGNATION` / `NOMCOURT`
   avec le nom IGN) est **techniquement confirmée**.

### 13.1 ⚠️ Les deux feuilles n'ont PAS les mêmes en-têtes

Vérifié sur le fichier réel — c'est le point à ne pas manquer compte tenu de la contrainte :

| | `Feuil1` | `BAT` |
|---|---|---|
| Ligne d'en-têtes | **ligne 2** (ligne 1 vide) | **ligne 1** |
| Nombre de colonnes | **317** | **122** |
| Nom de la clé | **`CODE_BIEN`** | **`CODEBIEN`** |
| Clé renseignée | **oui** | non |
| Contenu | 866 lignes, tous `GENRE` | 444 lignes = les 442 `BATI` + 2 `SITE` |
| Autre écart d'en-tête | `DAT_FIN_AFFECT` | `COMMENTAIRE` |

Lecture retenue : **`Feuil1` est l'export natif ASTECH** (jeu de colonnes complet, clé
renseignée) et **`BAT` est une vue de travail dérivée** (filtrée sur le bâti, colonnes réduites,
clé vidée — d'où le constat initial « le CODE_BIEN est absent »).

→ **Le gabarit de réexport doit donc être construit sur `Feuil1`** : en-têtes en ligne 2, ligne 1
vide, clé orthographiée `CODE_BIEN`. Réutiliser l'orthographe de `BAT` (`CODEBIEN`) ferait
échouer l'import.

**À confirmer auprès de la référente** : c'est bien `Feuil1` qu'ASTECH exporte et réimporte ?

### 13.2 Le seul point restant est testable, sans attendre une réunion

La contrainte énoncée interdit de **modifier** les en-têtes ; elle ne dit pas si ASTECH tolère
un **sous-ensemble** de colonnes — c'est exactement ce que suppose la feuille réduite (Q12).

Plutôt qu'une question ouverte, **un test de 5 minutes tranche** : exporter **2 lignes** au format
réduit (en-têtes recopiés depuis `Feuil1`, `CODE_BIEN` intact), tenter l'import dans ASTECH, et
regarder si les deux biens sont mis à jour.

- Import accepté → **feuille réduite** confirmée (décision Q12).
- Import refusé → bascule sur le **classeur complet**, où seules les cellules enrichies changent
  et où toutes les autres colonnes sont recopiées telles quelles. Coût de bascule quasi nul :
  même écriture de valeurs, gabarit de sortie différent.

Ce test est aussi le meilleur moyen de valider la largeur de `REFCAD` et le format décimal à
virgule des coordonnées, sur des données réelles et sans risque.

## 14. Reste à trancher

- **Q2** — périmètre importé (référente ASTECH).
- **Test d'import 2 lignes** — tranche Q12, la largeur de `REFCAD` et le format des coordonnées.
- **Confirmer que `Feuil1` est bien la feuille native ASTECH** (cf. §13.1).
- **Q14** — suppression des sites : chantier séparé, destructif, non démarré.

## 15. Hypothèses de travail — la référente ASTECH est indisponible (2026-08-18)

Le test d'import et la réunion ne peuvent pas avoir lieu maintenant. On avance donc sous
hypothèses **explicites et paramétrables** : chacune est un réglage, pas une hypothèse
enfouie dans le code. Si la référente tranche autrement, rien n'est à réécrire.

| Sujet | Hypothèse retenue | Où c'est réglable |
|---|---|---|
| **Q2 — périmètre** | `GENRE=BATI` et `HORSPARC=N` → 399 biens | paramètres `genres` et `include_out_of_park` de l'import (API : `?genres=BATI&include_out_of_park=false`) |
| **Q12 — format de sortie** | feuille réduite (décision utilisateur) | le gabarit d'export dérive de `headers_json` : produire le classeur complet = changer de gabarit, pas de logique |
| **Largeur de `REFCAD`** | section + n° de plan ; si le plan dépasse 3 chiffres, la cellule **n'est pas écrite** et le bien reste « à vérifier » | garde-fou d'écriture (§11.2) |
| **Feuille native** | `Feuil1` (confirmé par l'utilisateur) | détection automatique : on retient la feuille dont la clé est **effectivement renseignée** |

> Principe de sûreté appliqué partout : **on n'écrit jamais dans le fichier de la
> collectivité une valeur qu'on n'a pas su produire proprement.** Un doute laisse le bien
> « à vérifier » dans l'écran plutôt que de partir dans ASTECH.

## 16. Incrément 1 livré — import + rapprochement (2026-08-18)

**Migration `0070`.** Deux tables :

- `patrimoine_legacy_imports` — un export chargé : feuille, **ligne d'en-têtes**, et les
  **en-têtes conservés à l'octet près** (`headers_json`). C'est le gabarit du futur
  réexport : les en-têtes ne sont jamais retapés depuis le code, ils sont recopiés.
- `patrimoine_legacy_assets` — un bien par `CODE_BIEN`, avec le **payload des 317 colonnes**
  conservé, le rattachement `building_id` (N codes bien → 1 bâtiment), le statut, le
  candidat proposé et le point de travail lat/lon.

**Détection de feuille.** Le classeur porte deux feuilles aux en-têtes divergents. Le
service retient celle dont la **clé est effectivement renseignée** — sinon on importerait
`BAT`, dont le `CODEBIEN` est vide, et le rapprochement perdrait sa clé. Si aucune feuille
n'a de clé remplie, l'import échoue avec un message explicite (« redemander un export
ASTECH avec cette colonne renseignée ») plutôt que d'importer des lignes inutilisables.

**Idempotence.** Rejouer le même export met à jour les biens existants sans dupliquer ;
un bien déjà rattaché à la main conserve son rattachement et son statut.

**Moteur de reconnaissance.** Réutilise `_site_similarity` (cvc.py, en production).
L'adresse ne sert qu'à **départager** (bonus ≤ 0,02), conformément à la mesure du §4.
Deux garde-fous, tous deux calibrés sur le fichier réel :

1. **Ambiguïté** — si le 2ᵉ candidat est à moins de 0,05 du 1ᵉʳ, on propose sans rattacher.
   *Exception* : un nom identique (≥ 0,98) reste rattaché. Sans cette exception,
   `ECOLE ELEMENTAIRE PAUL BERT` → `ECOLE ELEMENTAIRE PAUL BERT` (score 1,0) était bloqué
   à cause d'une école voisine au nom ressemblant.
2. **Concurrence** — si plusieurs biens visent le même bâtiment, aucun n'est rattaché
   automatiquement. Cas réel : `SERVICE ENSEIGNEMENT` et `SERVICE E.M.O.P. ENSEIGNEMENT`,
   ou `TENNIS CLUB DU BARROU` et `SALLES TENNIS CLUB DU BARROU`.

**Résultat mesuré sur les vraies données** (fichier réel × 212 bâtiments prod) :

| | |
|---|---|
| Lignes lues (`Feuil1`, 317 colonnes) | 866 |
| Importées (`BATI` en service) | **399** |
| Écartées (autres genres, sorties du parc) | 467 |
| Marquées hors périmètre (hors Sète) | **26** |
| Candidat proposé | 277 |
| **Rattachées automatiquement** | **78** |
| Restent à traiter | **295** |

Les 5 rapprochements à ≥ 0,90 non rattachés sont exactement les cas ambigus listés
ci-dessus — ils attendent une validation humaine, ce qui est le comportement voulu.

**API** (`/api/patrimoine/legacy`) : `POST /import`, `POST /candidates`, `GET ""`,
`GET /counts`, `PATCH /{id}`. Le `code_bien` est volontairement absent du schéma de mise à
jour : il ne doit jamais être modifié.

**Tests** : `saas/backend/tests/test_patrimoine_legacy_import.py` (9 cas verts) —
choix de feuille, en-têtes à l'octet près, périmètre (dont commune absente ≠ hors
périmètre), payload conservé, idempotence, et les deux garde-fous.

### Reste à construire

- **Incrément 2** — écran unique : liste + carte, point de couleur dédiée, marqueur
  déplaçable, bouton « Attribuer IGN » branché sur les endpoints existants.
- **Incrément 3** — réexport ASTECH : normalisation d'adresse (§11.1), `REFCAD`,
  coordonnées à virgule décimale, feuille de traçabilité.
- Alimentation des champs d'adresse structurés côté `buildings` (§9.4).

## 17. Cible du rattachement : Site / Bâtiment / Local — analyse (2026-08-19)

> Demande utilisateur : pouvoir affecter manuellement un bien ASTECH à un **site**, un
> **bâtiment** ou un **local**, et considérer les rattachements automatiques comme
> **non finalisés** tant qu'ils n'ont pas été validés.
> Question posée : « est-ce cohérent, et cela ne crée-t-il pas de conflit ? »

### 17.1 État réel du référentiel Po2 (prod, 2026-08-19)

| | Nombre | Adresse | Coordonnées | Cadastre |
|---|---|---|---|---|
| `sites` | **156** | texte libre (`adresse`) | **non** | **non** |
| `buildings` | **183** | `adresse_reconstituee` (183/183) | **oui** (183/183) | `dgfip_reference_norm` (170/183) |
| `locals` | **625** | **non** | **non** | **non** |

173 bâtiments sur 183 sont rattachés à un site ; les 625 locaux ont tous un bâtiment parent.

### 17.2 Réponse : oui, c'est cohérent — mais quatre frictions réelles

**C'est cohérent métier.** L'utilisateur l'avait d'ailleurs annoncé dès Q1 : « plusieurs
locaux dans un bâtiment ». Un `CODE_BIEN` ASTECH désigne souvent un local (logement de
fonction, salle, WC publics), pas le bâtiment entier. Restreindre la cible au bâtiment
force des rapprochements approximatifs.

**Mais quatre points doivent être tranchés, sinon le chantier se casse plus loin :**

**F1 — L'adresse et le cadastre ne vivent QUE sur le bâtiment.**
Un local n'a ni adresse, ni parcelle, ni coordonnées. Un site n'a qu'une adresse en texte
libre, sans cadastre ni position. Or l'objet du chantier est de **renvoyer adresse +
cadastre à ASTECH**. Rattacher un bien à un local sans règle lui ferait donc **perdre**
l'adresse qu'il aurait eue en visant le bâtiment.
→ **Règle nécessaire** : quel que soit le niveau visé, l'adresse et le cadastre sont
toujours résolus **sur le bâtiment porteur** — le bâtiment lui-même, ou le bâtiment
parent du local. Pour un site, il n'existe pas de bâtiment porteur évident (un site en
contient plusieurs) : voir **Q15**.

**F2 — La carte ne sait afficher que des bâtiments.**
Seuls les bâtiments ont des coordonnées. Un local ou un site n'est pas positionnable.
→ Le glisser-déposer et le point vert restent donc **réservés au niveau bâtiment** ; le
rattachement à un local ou à un site se fera **depuis la liste**, pas depuis la carte.
Ce n'est pas un conflit, c'est une asymétrie à assumer explicitement dans l'écran.

**F3 — Contradiction avec la suppression des sites (Q14).**
L'utilisateur avait annoncé vouloir **supprimer les sites** du listing (Q3/Q14). Vouloir
maintenant y rattacher des biens ASTECH est **incompatible**. À trancher : voir **Q15**.

**F4 — La double affectation n'est PAS un conflit, mais doit être assumée.**
Si un bien vise un local et un autre le bâtiment parent, les deux recevront au réexport
**la même adresse et le même cadastre**. C'est le comportement correct — plusieurs locaux
d'un même bâtiment partagent bien l'adresse. Le seul risque serait qu'un futur moteur
déduise l'inverse (« même adresse ⇒ doublon »). À ne pas faire.
La relation **N codes bien → 1 cible** reste donc valide, et la contrainte d'unicité
porte toujours sur `(city_id, code_bien)`, jamais sur la cible.

### 17.3 Le rattachement automatique n'est pas une validation — d'accord

Aujourd'hui `compute_candidates` passe directement les évidences en `lie`, statut qui
signifie aussi « validé par l'utilisateur ». Les **78 biens actuellement en `lie` n'ont
jamais été confirmés par personne**.

→ Ajouter un état intermédiaire **`propose`** : rattaché par le moteur, **à confirmer**.
`lie` devient le statut « validé par un humain ». Les 78 rattachements automatiques
existants basculent en `propose` par migration de données.

Bénéfice direct : l'écran peut afficher « 78 à confirmer », et le réexport peut refuser
d'écrire dans ASTECH un rattachement que personne n'a validé — garde-fou cohérent avec la
règle « on n'écrit jamais dans le fichier de la collectivité ce qu'on n'a pas su produire
proprement ».

### 17.4 Modèle technique proposé

Suivre le précédent déjà en production dans `PatrimoineMatchItem` : un couple
**`target_type` + `target_id`** plutôt que trois colonnes de clés étrangères.

- `target_type` ∈ `building` | `local` | `site`
- `building_id` **conservé** comme *bâtiment porteur résolu* (le bâtiment lui-même, ou le
  parent du local) : c'est lui qui alimente l'adresse, le cadastre et la carte. Cela évite
  de réécrire toute la logique d'héritage et de réexport déjà en place.

Le moteur de reconnaissance automatique continue de ne proposer que des **bâtiments** :
les noms ASTECH ressemblent à des noms de bâtiments, et rien ne permettrait aujourd'hui de
départager 625 locaux par le nom. Le niveau local/site reste un **choix manuel**.

## 18. Questions ouvertes

**Q15 — Peut-on rattacher à un SITE, et que devient alors l'adresse ?**
Un site n'a ni coordonnées ni cadastre, et en contient plusieurs bâtiments. Trois options :
(a) **ne pas autoriser le site comme cible** — seulement bâtiment et local ;
(b) l'autoriser, mais le bien n'aura **ni cadastre ni position** à renvoyer à ASTECH ;
(c) l'autoriser en désignant en plus un **bâtiment de référence** dans le site.
→ **Recommandation : (a)**. Le site est un regroupement administratif ; le référentiel
ASTECH décrit du bâti. Et cela lève la contradiction avec Q14 (suppression des sites).

**Q16 — Confirme-t-on la suppression des sites (Q14), ou les garde-t-on ?**
Les deux demandes s'excluent. Si les sites doivent disparaître, la réponse à Q15 est
mécaniquement (a).

**Q17 — Les 78 rattachements automatiques actuels : à confirmer un par un, ou validés en
bloc une fois relus ?**
→ **Recommandation** : les basculer en « à confirmer », avec un bouton « tout confirmer »
sur la liste filtrée, pour ne pas imposer 78 clics.

## 19. Hiérarchie bâtiment / local — décisions 2026-08-20

> Question posée : « un bâtiment Po2 doit pouvoir héberger un ou plusieurs points ASTECH
> et vice versa ; le bâtiment est le point principal et les points qui s'y attachent
> deviennent soit des bâtiments soit des locaux. Comment est-ce géré ? »

### 19.1 Ce qui était déjà en place — et le trou constaté

Le modèle portait déjà la cible à deux niveaux (`target_type` + `local_id`, §17.4), le
bâtiment porteur restant toujours renseigné pour l'adresse et le cadastre.

**Mais l'écran ne savait viser qu'un local *déjà existant*.** Aucun moyen de créer un
local depuis un bien ASTECH. Mesure en prod le 2026-08-20 : **0 bien sur 79** rattaché
au niveau local, pour 626 locaux en base.

C'est pourtant le cas de figure normal dès que plusieurs biens visent un bâtiment. Les
deux seuls cas réels en prod le montrent :

| Bâtiment | Biens ASTECH | Locaux Po2 existants |
|---|---|---|
| 1004 — SALLE TENNIS CLUB DU BARROU | `TENNIS CLUB DU BARROU` + `SALLES TENNIS CLUB DU BARROU` | `SALLE TENNIS CLUB DU BARROU` |
| 1021 — ECOLE MATERNELLE SUZANNE LACORE | `ECOLE MATERNELLE SUZANNE LACORE` + `RESTAURATION SCOLAIRE ANATOLE FRANCE` | `ECOLE MATERNELLE SUZANNE LACORE` |

Pour 1004 le local existait et personne ne l'a visé ; pour 1021 il aurait fallu le créer,
ce qui était impossible. (Le rattachement du restaurant scolaire à 1021 est par ailleurs
douteux : il a son propre bâtiment, 1020.)

### 19.2 Décisions

| # | Question | Décision |
|---|---|---|
| Q18 | Un bien devenu local garde-t-il ce qu'il renvoie à ASTECH ? | **Oui.** Passer au niveau local **précise** la structure, il ne retire rien : l'adresse, le cadastre et la position restent ceux du bâtiment porteur. Le local créé en hérite aussi, pour ne rien perdre si on lui donne plus tard une adresse propre. |
| Q19 | Un bien ASTECH couvrant **plusieurs** bâtiments Po2 ? | **Non traité.** On ne sait pas encore si le cas existe réellement dans le fichier. La relation reste **N codes bien → 1 cible**. À rouvrir seulement sur un cas constaté : ce serait un changement de modèle (table de liaison), pas un réglage. |

### 19.3 Ce qui est livré

- `convert_asset_to_local()` + `POST /patrimoine/legacy/{id}/to-local` : crée le local
  dans le bâtiment porteur et y rattache le bien. **Réutilise un local homonyme** s'il
  existe déjà (cas 1004) plutôt que de créer un doublon. Idempotent.
- Bouton **« En faire un local de ce bâtiment »** dans le panneau d'action.
- **La fratrie affichée** : les biens ASTECH qui visent le même bâtiment, avec leur
  niveau (bâtiment entier / local), et une alerte quand **plusieurs visent le bâtiment
  entier** — en principe un seul le désigne, les autres sont des locaux ou l'un d'eux
  est mal rattaché.
- La bulle du point fusionné sur la carte dit le **niveau** de chaque bien, là où elle
  n'affichait qu'un compteur.

## 20. Nouvel export ASTECH (2026-08-20) — audit avant de coder

Fichier fourni par le référent ASTECH :
`saas/energie/ASTECH/OPUS_Patrimoine20260707.xlsx`. Il remplace l'export analysé au §2.

### 20.1 Ce qu'il contient réellement

Une seule feuille `Worksheet`, **en-têtes en ligne 1**, **12 colonnes** (contre 317 sur
deux feuilles). **1 501 lignes**, soit tout ASTECH et non plus le seul bâti.

| `GENRE` | Lignes |
|---|---|
| `VOIE / VOIE` | 781 |
| **`BATI / BATIMENT`** | **378** |
| `ESVE / ESPACES VERTS` | 286 |
| `EVEF / EVENEMENT / FESTIVITE` | 43 |
| `ARJE / AIRE DE JEUX` | 10 |
| `SITE / SITE` · `TERR / TERRAIN` | 2 · 1 |

Deux colonnes sont **composites**, au format `CODE / LIBELLÉ` :
`Genre` = `BATI / BATIMENT`, `Commune` = `34301 / 34301 SETE`. Il faut n'en garder que
le code, sinon le filtre de périmètre et le champ `COMMUNE` sortiraient faux.

### 20.2 ⚠️ Le CODE_BIEN a changé de schéma — **zéro code commun**

C'est le point structurant. L'ancien export codait `ADMICIMET02`, `SCOLMATER11` ; le
nouveau code `BATI00272`, `BATI00140`.

**Intersection mesurée entre les 444 biens en base et les 378 `BATI` du nouveau
fichier : 0 code commun.**

Or le `CODE_BIEN` est la **clé pivot permanente** de l'aller-retour (Q1, §13). En
conséquence :

- réimporter par-dessus ne mettrait rien à jour — les clés ne se rencontrent jamais —
  et **créerait 378 biens de plus** à côté des 444 existants ;
- le réexport renverrait des codes qu'ASTECH ne connaît plus ;
- les **81 rattachements** actuels (6 validés, 75 proposés) pendent dans le vide.

**Un pont par le nom existe** : 564 libellés (nom court ou désignation) sont identiques
de part et d'autre, soit **81 % des noms de l'ancien import**. Exemples mesurés :
`CULRMUSEE01` → `BATI00177` (`M.I.A.M.`), `SPORGYMNA01` → `BATI00438`
(`ALFRED NAKACHE`). Les 130 sans correspondance sont surtout les déchetteries hors Sète,
déjà marquées hors périmètre.

### 20.3 Correspondance des colonnes

| Nouveau | Ancien | Remarque |
|---|---|---|
| `Code` | `CODE_BIEN` | **schéma changé**, cf. §20.2 |
| `Genre` | `GENRE` | composite → garder `BATI` |
| `Nom court` | `NOMCOURT` | |
| `Désignation` | `DESIGNATION` | |
| `Numéro(s)` | `NORUE` | 285/378 valent `0` — même défaut qu'avant |
| `Complément` | `BISTER` | **même détournement** : `RUE` 91, `BD` 19, `QUA` 13, `AVE` 9, et `BIS` 3 seulement |
| `Adresse` | `LIBELVOIE` | 309/378 renseignés |
| `Code postal` / `Ville` / `Commune` | `CODPOST` / `VILLE` / `COMMUNE` | |
| `Lien voirie` | *(aucun)* | 167/378, identique à `Adresse` dans 210 cas |
| `Adresse2` | *(aucun)* | 2/378, ignorable |

Le piège `BISTER` du §6 est donc **confirmé sur le nouveau fichier** : la colonne porte
le type de voie, pas le bis/ter. La règle de normalisation du §9.1 reste valable telle
quelle.

Colonnes de l'ancien gabarit **absentes** du nouveau : `REFCAD`, `LATITUDE`,
`LONGITUDE`, `HORSPARC`, `CODE_PARENT`. Le drapeau « sorti du parc » n'existe plus, et
le fichier n'a plus aucune colonne pour recevoir le cadastre ni les coordonnées.

### 20.4 Questions ouvertes

**Q20 — Que deviennent les 444 biens et 81 rattachements existants ?**
(a) **Repartir de zéro** : supprimer l'import, charger le nouveau, relancer la
reconnaissance. Coût réel : 6 rattachements validés à refaire, les 75 proposés étant de
toute façon recalculés.
(b) **Pont par le nom** : transposer les rattachements sur 81 % des biens.
→ **Recommandation : (a).** Le pont ferait reposer la clé pivot sur un appariement de
libellés — exactement ce que le `CODE_BIEN` sert à éviter — pour économiser six clics.

**Q21 — Le réexport porte quels en-têtes ?**
La règle §13 dit : recopiés à l'octet près depuis le fichier importé, donc `Code`,
`Genre`, `Nom court`… Or la demande est de rendre les **anciens** noms (`CODE_BIEN`,
`GENRE`, `NOMCOURT`…). C'est faisable, mais c'est précisément la contrainte qui fait
échouer un import ASTECH : à confirmer auprès du référent.

**Q22 — Où écrire le cadastre et les coordonnées ?** Le nouveau fichier n'a plus ni
`REFCAD`, ni `LATITUDE`, ni `LONGITUDE`. Soit on les ajoute en colonnes supplémentaires
(au risque du refus à l'import), soit l'enrichissement se limite à l'adresse.
