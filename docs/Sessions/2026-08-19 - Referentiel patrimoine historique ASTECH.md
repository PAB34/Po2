# 2026-08-19 — Référentiel patrimoine historique (ASTECH)

## Objectif

Rapprocher le fichier patrimoine historique de la collectivité (ASTECH, clé `CODE_BIEN`)
avec le référentiel Po2, dans un **aller-retour** : export ASTECH → import Po2 →
traitement (rapprochement, carte, attribution IGN) → **réexport réinjectable**.

## Ce qui a été fait

**Livré en prod** (migrations `0070` → `0074`, PR #98 à #117) :

- **Écran dédié `/patrimoine/astech`** (menu Patrimoine) : file des biens à gauche, carte
  à droite, panneau d'action. Décision Q7 : un seul écran pour tout le parcours.
- **Import ASTECH** : détection automatique de la feuille exploitable (`Feuil1` porte la
  clé renseignée, `BAT` l'a vidée), **en-têtes conservés à l'octet près** (contrainte de
  réinjection), payload des 317 colonnes conservé, import **idempotent**.
- **Moteur de reconnaissance** : réutilise `_site_similarity` (cvc.py). L'adresse ne sert
  qu'à départager. Deux garde-fous mesurés sur données réelles : ambiguïté entre candidats
  proches (sauf nom identique) et plusieurs biens visant le même bâtiment.
- **Carte** : points ASTECH violets, verts quand appariés, éventail quand plusieurs biens
  visent le même bâtiment, marqueur déplaçable (ASTECH *et* bâtiment Po2), géocodage
  inverse au déplacement.
- **Héritage** : un bien rattaché reprend nom, adresse ET cadastre du bâtiment porteur —
  reconstitués depuis `adresse_reconstituee` et `dgfip_reference_norm`, les colonnes
  structurées étant vides en base.
- **Cible bâtiment ou local** (Q15/Q16) ; le site n'est pas une cible mais reste dans la
  plateforme. Statut **`propose`** distinct de `lie` : un rattachement automatique n'est
  pas une validation (Q17), avec bouton « tout confirmer ».

**Correctifs livrés en cours de route** (tous constatés sur données réelles) :

| Sujet | Cause trouvée |
|---|---|
| Purge du patrimoine incomplète | `delete_all_buildings` ne touchait pas aux sites ; puis le bouton disparaissait avec le dernier bâtiment |
| « Une erreur est survenue » au contrôle IGN | Requête unique > 120 s → 504 Caddy. Découpé en lots de 4 avec progression |
| Zéros initiaux d'adresse | Le nettoyage existait mais ratait `0005B` (suffixe bis/ter) et n'était pas appliqué à l'affichage |
| Adresse des locaux perdue | L'import jetait adresse et parcelle des lignes LOCAL (migration `0074`) |
| Carte vide au premier chargement | Leaflet fige la taille du conteneur → `ResizeObserver` |
| Carte floue/blanche | `maxZoom 22` alors qu'OSM s'arrête à 19 + `fitBounds` sur un point unique |
| `[object Object]` en message | FastAPI renvoie un `detail` en **liste** sur une 422 |
| Cellule multi-parcelles rejetée | `parcel_reference` limité à 64 car. → découpage en références multiples |
| Points ASTECH disparus | Purge du patrimoine → `building_id` NULL en cascade ; carte filtrée sur `lie` |

## Handoff — où reprendre

**État prod au 2026-08-19** : migration `0074` · 184 bâtiments · 160 sites · 626 locaux ·
444 biens ASTECH.

**Action utilisateur en attente** : cliquer « 2. Reconnaître les noms » sur
`/patrimoine/astech`. La purge du patrimoine a effacé les rattachements (cascade) ;
le bouton répare les liens orphelins et les repropose contre le référentiel actuel.

**Prochain chantier = INCRÉMENT 3, le réexport ASTECH** (rien n'est commencé) :

1. Générer la **feuille réduite** décidée (Q12) : `CODE_BIEN` + champs maîtrisés par Po2,
   **en-têtes recopiés à l'octet près** depuis `PatrimoineLegacyImport.headers_json`
   (gabarit `Feuil1`), jamais retapés — sinon ASTECH refuse l'import.
2. Appliquer la **règle d'adresse** actée : `NORUE` = numéro seul, `BISTER` = bis/ter
   uniquement, `LIBELVOIE` = type de voie **en toutes lettres** + nom. Table d'expansion
   des abréviations DGFIP (`AV`→`AVENUE`, `BD`→`BOULEVARD`…), la source étant elle-même
   incohérente (`BD`/`BOULEVARD`, `AV`/`Avenue`).
3. `REFCAD` = section + plan sur 3 chiffres (`AK149`). **Garde-fou** : si le plan dépasse
   999, ne rien écrire plutôt qu'une référence tronquée.
4. Coordonnées **à virgule décimale** (`43,404512`) — format constaté dans le fichier.
5. **Seconde feuille de traçabilité** (ancienne → nouvelle valeur, origine, date), pour
   relecture avant réinjection.
6. Les biens au statut `a_creer` sortent avec un **`CODE_BIEN` vide** : c'est ASTECH qui
   l'attribuera (Q13).

**Règle de sûreté à respecter partout** : on n'écrit jamais dans le fichier de la
collectivité une valeur qu'on n'a pas su produire proprement ; le doute laisse le bien
« à vérifier » dans l'écran.

## Notes & décisions

- Décisions Q1→Q17 consignées dans
  `docs/refonte-v1/patrimoine-fichier-historique-rapprochement-decisions.md` (§5, §9, §11,
  §13, §15, §17).
- **En attente de la référente ASTECH** : périmètre exact importé (Q2) ; confirmation
  qu'ASTECH accepte un import de mise à jour par clé (sinon repli sur le classeur
  complet, prévu) ; largeur du champ `REFCAD`.
- **Chantier séparé, non démarré** : suppression des sites (Q14). L'utilisateur est
  finalement réticent — les sites portent la hiérarchie Site › Bâtiment › Local.
