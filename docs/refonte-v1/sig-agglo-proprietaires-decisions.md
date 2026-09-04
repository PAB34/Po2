# SIG de l'agglo — récupérer les propriétaires : audit, cadre, décisions

> Créé le **2026-09-03** (session Claude). Statut : **étapes 1 (reconnaissance) et 2 (extraction) FAITES.**
> Rien n'est encore écrit en base Po2 : reste l'étape 3 (connecteur produit).
> Portail : `https://sig.agglopole.fr/vmap2/` (vMap 2026.06, éditeur Veremes).
> Inventaire détaillé → `sig-agglo-inventaire-couches-foncieres.md`.

---

## 1. Pourquoi ce sujet

Le module Patrimoine sait **où** sont les bâtiments (IGN, adresse, référence cadastrale) mais pas
**à qui** appartient la parcelle. Le SIG de Sète Agglopôle Méditerranée, auquel l'utilisateur a un
accès nominatif, expose la donnée propriétaire (origine DGFiP/MAJIC). Question posée : peut-on
écrire un programme qui la récupère et l'analyse ?

Réponse : **oui**, l'API est propre, authentifiée et scriptable. Les vraies questions sont le
**cadre d'usage** (§5) et le **périmètre utile** (§7).

---

## 2. Existant vérifié dans Po2 (avant d'ajouter quoi que ce soit)

| Brique | État | Fichier |
| --- | --- | --- |
| Bâtiments avec référence cadastrale normalisée | **en prod** | `app/models/building.py:15-19` (`dgfip_reference_norm`, `dgfip_unique_key`, `dgfip_source_rows_json`) |
| Normalisation INSEE + préfixe + section + plan | **en prod** | `app/services/building_naming.py:444` |
| Attachement IGN (adresse + cadastre) | **en prod** | `POST /buildings/{id}/ign-attachment` |
| Adresses DGFiP/MAJIC à proximité (rayon 200 m) | **codé, mais fichier absent** | `app/core/config.py:13` `dgfip_majic_file_path` vide → l'écran affiche « le fichier DGFiP/MAJIC n'est pas configuré » (`BuildingDetailPage.tsx:939`) |
| Référentiel ASTECH (444 biens, cadastre hérité) | **en prod** | `/patrimoine/astech` |

**Constat structurant** : le produit a déjà **un trou nommé** à cet endroit — la source MAJIC était
prévue comme un *fichier* à déposer, jamais fourni. Le SIG peut devenir cette source, **en API**
plutôt qu'en fichier. Rien à réécrire : c'est un **connecteur** à brancher sur un besoin déjà
modélisé (clé de jointure = référence cadastrale / `id_par`).

---

## 3. L'API : ce qui a été établi le 2026-09-03

| Élément | Valeur |
| --- | --- |
| Base API | `https://sig.agglopole.fr/rest_vmap2/v2` (déclarée dans `/vmap2/conf/properties.json`) |
| Connexion | `POST /vitis/privatetoken`, corps JSON `{user, password, duration}` |
| Jeton | renvoyé dans `data.token`, porté **brut** dans l'en-tête `Authorization` (ni Basic ni Bearer) |
| Catalogue | `GET /vmap/layers` → **1 069 couches** |
| Attributs | `GET /vmap/layers/{layer_id}/query?limit=N&filter=<json>` |
| Filtre | `{"relation":"AND","operators":[{"column":"id_com","compare_operator":"=","value":"34301"}]}` — testé, fonctionne |
| Volumétrie | la réponse porte `total_row_number` → comptage sans télécharger |

Privilèges du compte utilisé : `vitis_user`, `vmap_cadastre_medium_user`, `vmap_user`.

**Voies fermées** (et c'est très bien ainsi) : le **WFS est désactivé** sur le service MapServer
(`wms2/private/<hash>`), et `vitis/genericqueries/columns` (SQL générique, réservé aux admins)
répond `ERROR_INSUFFICIENT_PRIVILEGE`. La seule voie ouverte est **l'API métier de consultation**,
celle qu'utilise l'application elle-même. On reste donc strictement dans l'usage prévu de l'outil.

---

## 4. Ce que le SIG contient réellement (126 couches foncières, 79 lisibles, 47 refusées)

### 4.1 Les couches décisives

| # | Table | Lignes | Contenu |
| --- | --- | ---: | --- |
| **317** | `foncier.vmp_foncier_public` | **17 040** | **Foncier présumé public (DGFP 2025)** : `id_par`, `ddenom`, `type`, `ccodro`/`l_ccodro`, `surfcad_m2`, `assimile_sam`, `nb_proprio`, `dtmajic` |
| **474** | `agglo_s_cadastre.vmp_uf_proprietaire` | **63 809** | **MAJIC nominatif complet** : `ddenom`, `dnomlp`/`dprnlp`, `dnomus`/`dprnus`, `dqualp`, `dlign3`→`dlign6` (adresse du propriétaire), `dnuper`, `dnupro`, `id_uf`, `id_com` |
| **943** | `agglo_s_cadastre.vmap_fond_cadastral_parcelle` | 173 365 | Parcelles : `id_par`, `section`, `parcelle`, `sup_m2`, `sup_fiscale`, `x`, `y`, `jdatat` |
| — | `s_cadastre.v_vmap_unite_fonciere` | 63 811 | `id_uf`, `id_dnupro`, `nb_parcelles`, `superficie` |
| — | `s_cadastre.v_vmap_batiment` | 100 722 | Bâti cadastral : `id`, `section`, `dur_code`/`dur_lib` (dur/léger) |
| **604** | `foncier.vmp_cadhist` | 91 537 | Historique de parcelle (`an_ajout`, `an_suppr`, `existe_encore`) |
| **1370** | `agglo_s_cadastre.vmp_parcelles_sans_infos_majic` | 85 | Parcelles sans information foncière — la liste des trous |
| **694** | `foncier.vmp_perimetre_competence_foncier_et_espaces_nat` | 123 | Parcelles confiées à la gestion de SAM (délibérations, dates) |

### 4.2 Le point qui oriente tout

La couche **474** (nominative, personnes physiques comprises) n'a pas de colonne nommée `id_par`.
> **Corrigé le 2026-09-03 après extraction** : son `id_uf` **porte en fait un identifiant de
> parcelle** (même format sur 14 caractères), et se joint directement au cadastre pour **97,7 %**
> des lignes. La crainte d'un « travail de rapprochement » exprimée ici lors de l'audit était
> infondée — voir §9. Reste la maille *unité foncière*, qui laisse 26 % des parcelles de l'agglo
> sans propriétaire direct.

La couche **317** porte **`id_par` ET `ddenom`** : jointure **directe** avec le cadastre de Po2 —
et elle ne contient **que des personnes morales publiques**. Typologie mesurée sur 1 000 lignes :
EPCI 66 %, État 19 %, Offices HLM 5 %, Communes 4 %, Syndicats 3 %, Région/Département, CCAS.
Le champ `l_ccodro` distingue propriétaire / gérant / emphytéote / bailleur à construction.

**Autrement dit : le chemin le plus court est aussi celui qui ne copie aucune donnée personnelle.**
Sur Sète (`id_com = 34301`) : **1 624 parcelles publiques**, mesuré par comptage sans téléchargement.

---

## 5. Cadre d'usage

La donnée de la couche **474** est une **donnée à caractère personnel** (nom, prénom, civilité,
adresse du propriétaire) dont la rediffusion est encadrée (art. **L. 107 A** du livre des
procédures fiscales, et RGPD pour finalité / minimisation / durée). La couche **317** ne contient
que des personnes morales publiques : elle ne pose pas ce problème.

Consulter est acquis (agent habilité, compte nominatif). Ce qui change avec un programme, c'est la
**copie dans une autre base**. Garde-fous proposés :

1. **Prévenir l'administrateur SIG de l'agglo** — une phrase suffit. C'est aussi le plus court
   chemin vers un **compte de service** (qui ne casse pas au départ de l'agent) et vers la
   confirmation qu'on tape la bonne couche.
2. **Minimiser** : commencer par la couche 317 seule (§7 Q1). Elle répond à « qu'est-ce que la
   Ville possède ? » sans copier une seule identité de particulier.
3. **Ne jamais exposer** de donnée nominative dans une page publique, un export libre ou un log.

---

## 6. Plan — l'étape 1 est faite

**Étape 1 — reconnaissance. ✅ FAITE (2026-09-03).**
`saas/backend/scripts/sig_agglo_recon.py`, lecture seule : se connecte, inventorie les couches,
et pour chaque couche foncière relève **colonnes + volumétrie**. Une ligne est bien demandée
(`limit=1`, seul moyen de connaître les colonnes) mais **reste en mémoire** : seuls les noms de
colonnes et les comptages sont écrits. Résultat →
`sig-agglo-inventaire-couches-foncieres.md`.

```bash
# .env à la racine du dépôt (ignoré par git, cf. .gitignore:7-9)
SIG_AGGLO_BASE_URL=https://sig.agglopole.fr/rest_vmap2/v2
SIG_AGGLO_USER=...
SIG_AGGLO_PASSWORD=...
```

```bash
python saas/backend/scripts/sig_agglo_recon.py --out sig_recon --sample
```

**Étape 2 — extraction et analyse. ✅ FAITE (2026-09-03).**
`sig_agglo_extract.py` (510 284 lignes, 6 couches, dossier hors git + manifeste daté) puis
`sig_agglo_analyse.py` (rapport `rapport-proprietaires.md`). Résultats → §9.

```bash
python saas/backend/scripts/sig_agglo_extract.py --out sig_agglo_data
python saas/backend/scripts/sig_agglo_analyse.py --data sig_agglo_data
```

**Étape 3 — connecteur produit.** Service `app/services/sig_agglo.py` + table de rapprochement
parcelle → propriété, branchés sur l'écran bâtiment qui attend déjà cette donnée. Là seulement on
écrit en base.

---

## 7. Questions — Q1 à Q3 tranchées le 2026-09-03

- **Q1 — Quelle couche ? → (c) TOUT, personnes physiques comprises.** Décision de l'utilisateur,
  prise après exposé des trois options et du cadre juridique. La proposition initiale (317 seule,
  sans donnée personnelle) n'est pas retenue : le besoin porte sur l'ensemble de la donnée
  propriétaire. **Conséquence assumée** : Po2 manipule des données à caractère personnel, ce qui
  engage §5 (information de l'admin SIG, non-rediffusion, durée de conservation).
- **Q2 / Q3 — Périmètre ? → toute l'agglo, toutes les parcelles.** 14 communes, sans restriction
  aux bâtiments déjà connus de Po2 : l'objectif inclut la découverte de patrimoine absent de Po2.
- **Q4 — Rafraîchissement ?** Extraction ponctuelle ou synchronisation ? Les fichiers fonciers sont
  millésimés annuellement (`dtmajic`) : un rafraîchissement annuel suffit sans doute.
- **Q5 — Compte utilisé ?** Nominatif (immédiat) ou compte de service demandé à l'agglo (propre) ?
- **Q6 — Stockage ?** Nouvelle table `parcel_ownership` ou enrichissement des colonnes `dgfip_*`
  de `buildings` ? *Proposition : table dédiée — une parcelle a plusieurs titulaires de droits
  (`l_ccodro`), un bâtiment plusieurs parcelles.*
- **Q7 — Et le fichier MAJIC prévu à l'origine ?** Le connecteur SIG le remplace-t-il définitivement
  (`dgfip_majic_file_path` devient mort) ou les deux sources coexistent-elles ?

---

## 8. Décisions datées

| Date | Décision | Motif |
| --- | --- | --- |
| 2026-09-03 | Audit avant code ; reconnaissance **sans copie de donnée nominative** | Règle « fil du dev » + minimisation RGPD : on n'extrait rien tant qu'on ne sait pas ce qu'on extrait |
| 2026-09-03 | API ciblée = `rest_vmap2/v2`, **pas de scraping** de l'interface | Route confirmée ; un client HTTP est stable, un scraping ne l'est pas |
| 2026-09-03 | On passe par **l'API métier de consultation** (`/vmap/layers/{id}/query`) | WFS désactivé et SQL générique interdit au compte : on reste dans l'usage prévu de l'outil |
| 2026-09-03 | **Cible pressentie = couche 317** (foncier présumé public) | Seule couche qui porte à la fois `id_par` et le propriétaire ; et elle ne contient aucune personne physique |
| 2026-09-03 | **Périmètre retenu : TOUT, toute l'agglo** (couche 474 comprise, particuliers inclus) | Choix de l'utilisateur après exposé des options et du cadre RGPD ; la recommandation « 317 seule » n'est pas retenue |
| 2026-09-03 | Le dossier d'extraction porte **son propre `.gitignore` à `*`** | La donnée personnelle ne doit pas pouvoir entrer dans git, même par `git add -A` — protection câblée, pas procédurale |
| 2026-09-03 | Un **`MANIFESTE.md`** daté accompagne toute extraction | Origine, finalité, volumétrie : répondre dans six mois à « d'où vient ce fichier » |
| 2026-09-03 | Les rapports de synthèse **nomment les personnes morales, agrègent les particuliers** (`--noms-particuliers` pour lever) | Le CSV porte la donnée complète comme décidé ; un rapport de synthèse n'a pas besoin de désigner des particuliers |

---

## 9. Étape 2 exécutée — ce que l'extraction a donné (2026-09-03)

**510 284 lignes extraites** en 6 couches (`sig_agglo_extract.py`), **93 Mo**, dans `sig_agglo_data/`
(hors git). Analyse → `sig_agglo_data/rapport-proprietaires.md` (`sig_agglo_analyse.py`).

**Découverte structurante** : `id_uf` de la couche 474 **porte un identifiant de parcelle**.
La jointure au cadastre est donc **directe** — 62 367 lignes sur 63 809 (**97,7 %**) — contrairement
à ce que laissait craindre l'audit initial. Il n'y a pas de rapprochement à construire.

| Mesure | Valeur |
| --- | --- |
| Propriétaires distincts | 43 802 (32 039 comptes communaux) |
| Personnes physiques / morales | 80 % / 20 % des lignes — mais 39 % de la surface aux morales |
| Couverture (14 communes agglo) | 62 367 parcelles sur 84 248 = **74 %** |
| Propriétaires hors Hérault | 9 300 lignes (15 %) |
| Foncier public | 72,5 km² aux communes, 31,9 km² au Conservatoire du littoral, 30,8 km² à l'État |
| Ville de Sète | **599 parcelles, 1,3 km²** (+ agglo 316 parcelles, + Sète Thau Habitat 218) |

**Limite mesurée** : la couche est à la maille **unité foncière**. 63 811 UF couvrent 86 154
parcelles, dont 10 664 UF en regroupent plusieurs (jusqu'à 125) ; seule la parcelle « tête » porte
l'identifiant. Passer de 74 % à ~100 % suppose de rattacher les parcelles secondaires, via
`id_dnupro` (jointure simple, à tenter d'abord) ou par intersection géométrique (`--avec-geom`).

**Piège écarté** : le fond cadastral couvre **27 communes** (les 14 de l'agglo + les limitrophes).
Rapporter la couverture à ses 170 383 parcelles donne un taux faussement bas de 36,6 % ; le bon
dénominateur est le périmètre agglo.

---

## 10. Classeur unique et adresse des biens (2026-09-03)

Demande : tout dans **un seul fichier, une seule feuille**, avec l'adresse **du bien** en plus de
celle du propriétaire. → `sig_agglo_classeur.py` produit `foncier-agglo.xlsx` (63 809 lignes ×
34 colonnes, une ligne = un propriétaire sur un bien).

**L'adresse du propriétaire n'est pas celle du bien.** `dlign3`→`dlign6` donnent le *domicile*
du propriétaire (pour la Ville de Sète : l'Hôtel de Ville). L'adresse du bien vient d'ailleurs :

| Source | Couverture | Rattachement |
| --- | --- | --- |
| `adresse.v_sete_adresse` (couche **226**, 9 974 adresses) | Sète | **exact** : la couche porte `section` + `parcelle` (jusqu'à 3 parcelles par adresse) |
| `referentiels.vmp_ban` (couche **397**, 80 514 adresses) | tout le territoire | **approché** : points seuls, on prend le plus proche du centroïde de parcelle |

Résultat : **6 812 exactes + 40 181 approchées = 73,6 %** des lignes adressées. Qualité des
approchées : **médiane 14 m**, 75ᵉ centile 23 m, 8 % au-delà de 50 m. Sète est couverte à **99 %**.
Les 15 374 parcelles sans adresse sont à plus de 100 m de tout point adresse (surface médiane
2 561 m² : du foncier rural, sans adresse postale) ; s'y ajoutent les 1 442 lignes sans parcelle.

**Obstacle technique traité** : les centroïdes de parcelle sont en **degrés WGS84**, la BAN en
**Lambert-93**. `pyproj` n'est pas installé sur le poste → la projection conique conforme est
implémentée dans le script et **vérifiée sur les données réelles avant usage** : l'écart médian
parcelle ↔ adresse la plus proche vaut 31 m (une projection fausse donnerait des kilomètres). Le
script refuse de produire les adresses au-delà de 500 m d'écart médian.

**Détail d'import** : MAJIC cale le numéro de voie sur 4 chiffres (`0007 RUE PAUL VALERY`). Le
script le dépouille — sans quoi tout rapprochement d'adresse échouerait, comme sur ASTECH.

| Date | Décision | Motif |
| --- | --- | --- |
| 2026-09-03 | Adresse du bien = **exact (226) d'abord, BAN (397) en repli**, source et distance affichées ligne à ligne | Aucune source ne couvre tout ; l'utilisateur doit pouvoir juger une adresse approchée, pas la subir |
| 2026-09-03 | Projection Lambert-93 **implémentée et validée sur les données**, pas supposée juste | `pyproj` absent du poste entreprise ; une projection fausse est silencieuse et contamine tout |

---

## 11. Hors agglo (Agde…) : ce qu'on peut et ne peut pas obtenir — testé le 2026-09-04

Question posée : le SIG donne-t-il la même chose sur des communes hors du territoire de l'agglo ?
**Réponse mesurée : le cadastre et le foncier public oui, les propriétaires nominatifs non.**

Le SIG couvre **27 communes** en cadastre (les 14 de l'agglo + 13 voisines), mais seulement
**14 en MAJIC nominatif**. Vérifié commune par commune :

| Périmètre | Parcelles | Propriétaires nominatifs | Foncier public | Adresses BAN |
| --- | ---: | ---: | ---: | ---: |
| 14 communes de l'agglo | 84 248 | **63 809** | 9 777 | oui |
| 13 communes voisines (dont **Agde : 18 799 parcelles**) | 86 135 | **0** | **7 263** (Agde : 1 490) | oui |
| Au-delà (Montpellier, Pézenas, Lattes…) | **0** | 0 | 0 | non |

**Contrôle d'exhaustivité** : les **8 couches** du SIG portant un champ propriétaire (`ddenom`,
`dnuper`, `dnupro`…) ont été interrogées une à une sur Agde. **Seule la couche 317 répond** ;
474 et 532 renvoient 0, les autres sont bornées à l'agglo par construction. Il n'y a donc pas
d'autre porte d'entrée dans le SIG.

**Interprétation** : ce n'est pas une limite technique mais un **périmètre de convention**. Les
fichiers MAJIC sont délivrés par la DGFiP à un EPCI pour son territoire ; Agde relève d'Hérault
Méditerranée, pas de Sète Agglopôle. Aucun contournement à chercher côté SIG — obtenir Agde en
nominatif suppose une démarche auprès de la DGFiP ou d'Hérault Méditerranée, ce qui est une
question de convention, pas de code.

**Livrable** : `sig_agglo_classeur.py --source public` produit
`foncier-public-27-communes.xlsx` — 17 040 lignes, 23 colonnes, dont **7 263 parcelles publiques
hors agglo**. Colonne `Dans l'agglo` pour filtrer. **Aucune donnée personnelle** (personnes
morales publiques uniquement), donc ce classeur-là n'a pas les contraintes du précédent.

| Date | Décision | Motif |
| --- | --- | --- |
| 2026-09-04 | Mode `--source public` ajouté, couvrant les 27 communes | Le foncier public est la seule donnée propriétaire disponible hors agglo, et elle est exploitable telle quelle |
