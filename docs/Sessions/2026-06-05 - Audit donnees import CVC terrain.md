# 2026-06-05 - Audit donnees import CVC terrain

## Perimetre audite

- Page cible : `/buildings/cvc-import`.
- Dernier lot prod : `import_d0791486`.
- Date import : 2026-06-05 08:33 UTC.
- Source locale confrontee : `saas/energie/CVC/listing materiels V2.xlsx`.

## Collecte brute

Le fichier source et le lot importe sont coherents sur le volume :

| Indicateur | Valeur |
|---|---:|
| Lignes source XLSX non vides | 1133 |
| Lignes importees en base | 1133 |
| Sites source renseignes | 1133 |
| Batiment source renseigne | 1133 |
| Niveau source renseigne | 1133 |
| Local source renseigne | 1133 |
| Designation renseignee | 1133 |
| Famille renseignee | 1133 |
| Quantite relevee renseignee | 1133 |
| Marque renseignee | 823 |
| Modele renseigne | 671 |
| Date MES renseignee | 535 |
| Reference duree de vie rattachee | 1128 |
| Batiment patrimoine rattache | 0 |

Conclusion : la collecte brute est saine. Le probleme principal est l'interpretation automatique vers `equipment_references`.

## Probleme racine

Le matching actuel compare surtout `FAMILLE` a `equipment_references.equipement` avec `SequenceMatcher`, sans contrainte metier suffisante sur le domaine SYPEMI ni dictionnaire d'alias. Le taux de rattachement 1128/1133 est donc trompeur : beaucoup de lignes sont rattachees a une reference plausible uniquement lexicalement.

## Faux positifs majeurs

| Famille terrain | Lignes | Reference actuelle | Probleme |
|---|---:|---|---|
| Autre a qualifier | 177 | Garniture et paliers / Production de froid | Faux positif massif ; ne devrait pas auto-matcher |
| Split system | 154 | Plieuse / Service de Reprographie | Faux positif critique ; devrait aller vers Split / Multi-split |
| Ventilation | 93 | Grilles de ventilation / menuiseries interieures | Mauvais domaine ; devrait aller vers ventilation CVC si possible |
| Compteur | 83 | Pompe d'exhaure | Faux positif ; pas de reference compteur claire dans SYPEMI actuel |
| Filtre | 32 | Vitrage | Faux positif critique |
| Centrale Traitement Air | 24 | Poste central et moniteurs / videosurveillance | Faux positif critique ; devrait aller vers CTA |
| Aerotherme | 10 | Robinetterie sanitaire | Faux positif |
| Cassette | 8 | Chaussee | Faux positif ; probablement unite terminale clim |
| Pompe a Chaleur | 8 | Pompe a huile / Production de froid | Mauvaise reference ; devrait viser PAC Air/Eau ou Eau/Eau selon donnees |
| Preparateur ECS | 8 | Separateur a fecules | Faux positif |
| Systeme VRV | 3 | Systeme de GTB | Faux positif |
| VRV | 2 | Non rattache | A traiter comme DRV/VRV froid/clim |

Estimation haute des lignes a revoir en priorite : environ 628 lignes, dont 154 split/clim + 177 "Autre a qualifier".

## Exemples confirmes

- `UE clim DAIKIN 3` (`famille = Split system`) est actuellement rattache a `Plieuse`, `A.2.9 Service de Reprographie`, duree 10 ans. C'est faux. Le referentiel contient pourtant :
  - `id 235` : `Climatiseurs a detente directe type Windows ou Split system`, reference 15 ans ;
  - `id 236` : `Split - Multi-split`, reference 10 ans.
- `Armoire electrique` est bien rattachee a `id 118 Armoire electrique`, `A.2.2 Courant fort`, reference 35 ans. Ce n'est pas un echec d'identification, mais c'est hors `A.2.3 CVC`. Si on veut la voir/editer dans le parcours CVC terrain, il faut accepter explicitement certaines familles electriques auxiliaires.
- `Centrale Traitement Air` est actuellement rattachee a `Poste central et moniteurs` en videosurveillance. Le referentiel contient `id 221 CTA simple ou double flux a recuperation d'energie`, reference 20 ans.
- `Cassette` est rattachee a `Chaussee`, ce qui est manifestement faux.
- `Compteur` est rattache a `Pompe`, faute de reference compteur dediee.

## Recommandation technique

1. Ne plus auto-rattacher les familles generiques ou inconnues :
   - `Autre a qualifier`, `Compteur`, `Appareil de mesure`, `Analyseur`, `Plomberie` doivent rester a traiter sauf regle explicite.
2. Ajouter un dictionnaire d'alias metier prioritaire avant le fuzzy :
   - `Split system`, `Mono-split`, `UE clim`, `climatisation`, `Cassette` -> `Split - Multi-split` ou `Climatiseurs a detente directe type Split system`.
   - `Centrale Traitement Air`, `CTA` -> `CTA simple ou double flux a recuperation d'energie`.
   - `Armoire electrique`, `Tableau electrique`, `Coffret electrique`, `Armoire CTA` -> `Armoire electrique`.
   - `Pompe a Chaleur`, `PAC`, `Groupe thermodynamique` -> reference PAC, avec revue si Air/Air absent du referentiel.
   - `Groupe Froid`, `VRV`, `DRV` -> production de froid / autonome froid selon arbitrage.
3. Contraindre le fuzzy par famille de domaine :
   - pour inventaire CVC terrain, favoriser `A.2.3`, puis autoriser une whitelist `A.2.1` plomberie sanitaire et `A.2.2` electricite auxiliaire ;
   - ne jamais accepter `A.1.*`, `A.2.7`, `A.2.9` par simple similarite sur ce flux.
4. Stocker ou exposer un `match_confidence` et un `match_reason` pour distinguer :
   - match alias fiable ;
   - match exact ;
   - match fuzzy a valider ;
   - non matche.

## Handoff suivant

Corriger `app.services.cvc._resolve_family()` pour passer par un moteur d'alias + domaines autorises, puis ajouter un endpoint/action de recalcul du dernier import pour remplacer les faux rattachements sans re-uploader le fichier.

## Correctif applique

Suite directe de l'audit :

- moteur `_resolve_family()` remplace par alias metier + fuzzy contraint ;
- domaines autorises pour le flux CVC terrain : `A.2.1`, `A.2.2`, `A.2.3` ;
- familles trop generiques bloquees en fuzzy : `Autre a qualifier`, `Compteur`, `Appareil de mesure`, `Analyseur`, `Plomberie` ;
- alias explicites ajoutes pour Split/UE clim/Daikin, CTA, armoires/tableaux/coffrets electriques, PAC/thermodynamique, groupe froid/VRV, ventilation, filtres, pompes, preparateur ECS, regulation ;
- endpoint de recalcul ajoute : `POST /api/cvc/imports/{import_batch}/recompute-references` ;
- bouton front ajoute : `Recalculer les references`.

Renforcement applique apres audit du recalcul prod :

- les familles de mesure (`Compteur`, `Appareil de mesure`, `Analyseur`, `Plomberie`) ne declenchent plus d'alias PAC/CTA/split ;
- les familles precises passent avant les alias clim : CTA, chaudiere, preparateur ECS, ballon, vase expansion, GTB/GTC, circulateur, echangeur, robinets/vannes ;
- les marques seules (`Daikin`, `Atlantic`, etc.) ne suffisent plus a rattacher un equipement a `Split - Multi-split`.

Recalcul prod du lot `import_d0791486` apres deploiement :

| Indicateur | Valeur |
|---|---:|
| Lignes recalculees | 1133 |
| References rattachees | 895 |
| References non rattachees | 238 |
| Lignes modifiees par le recalcul final | 199 |

Controles cibles apres recalcul :

| Cas | Resultat |
|---|---|
| `UE clim DAIKIN 3` | `id 236 Split - Multi-split`, `A.2.3` |
| `Armoire electrique` | `id 118 Armoire electrique`, `A.2.2` |
| `CPT elec PAC` / famille `Compteur` | non rattache, a valider manuellement |
| `Centrale Traitement Air` | 24/24 vers `id 221 CTA simple ou double flux` |
| `Chaudiere` | 44 vers chaudiere condensation, 22 vers chaudiere murale, aucun split/PAC |
| `Vase expansion` | 52/52 vers `id 188 Vase d'expansion a membrane` |
| `GTB / GTC` | 3/3 vers `id 162 Point de GTB / GTC` |

Validation locale :

- `python -m compileall app tests/test_cvc_reference_matching.py` OK ;
- `DATABASE_URL=sqlite:///:memory: python -m pytest tests/test_cvc_reference_matching.py -p no:cacheprovider` OK, 11 tests passes.
