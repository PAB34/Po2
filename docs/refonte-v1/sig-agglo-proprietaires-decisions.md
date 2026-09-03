# SIG de l'agglo — récupérer les propriétaires : audit, cadre, décisions

> Créé le **2026-09-03** (session Claude). Statut : **étape 1 (reconnaissance) FAITE et exécutée.**
> Rien n'est encore écrit en base Po2 — questions §7 à trancher avant l'étape 3.
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

La couche **474** (nominative, personnes physiques comprises) porte `id_uf` mais **pas `id_par`** :
la jointure parcelle → propriétaire nominatif passe par l'unité foncière, elle demande un travail
de rapprochement.

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

**Étape 2 — décision.** Trancher §7, en particulier Q1 (317 seule vs 474 nominative).

**Étape 3 — connecteur produit.** Service `app/services/sig_agglo.py` + table de rapprochement
parcelle → propriété, branchés sur l'écran bâtiment qui attend déjà cette donnée. Là seulement on
écrit en base.

---

## 7. Questions ouvertes (à trancher avant l'étape 3)

- **Q1 — Quelle couche ?** (a) **317 seule** — `id_par` + propriétaire public, jointure directe,
  zéro donnée personnelle ; (b) 317 **+ 474 filtrée sur les personnes morales** ; (c) 474 entière,
  personnes physiques comprises. *Proposition : (a) d'abord, (b) si un besoin le justifie.*
- **Q2 — Périmètre géographique ?** Sète seule (`id_com = 34301`, 1 624 parcelles publiques) ou
  les 14 communes de l'agglo (17 040) ?
- **Q3 — Périmètre parcellaire ?** Uniquement les parcelles des ~184 bâtiments Po2, ou **toutes**
  les parcelles publiques de la commune ? La seconde permet de découvrir du patrimoine **absent**
  de Po2 — c'est souvent là qu'est la valeur.
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
