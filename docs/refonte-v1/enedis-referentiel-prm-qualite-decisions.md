# ENEDIS — qualité du référentiel PRM (décisions)

> Statut : diagnostic terminé, corrige la conclusion du 2026-07-22, arbitrages ouverts
> Date : 2026-07-23
> Prérequis : `enedis-sync-fiabilite-decisions.md` (§6 « PRM muets »), dont ce document
> **infirme la conclusion principale**.
> Données : prod, `saas/energie/output/*.csv` + table `energy_invoice_sites`, relevés le 2026-07-23.

## 1. Ce que la note du 22/07 supposait, et pourquoi c'était faux

La note du 22/07 concluait que les 138 PRM en `ADAM-ERR0155` (« point inexistant »)
étaient des **identifiants qu'ENEDIS ne reconnaît pas**, et renvoyait le sujet à
« la source qui alimente `enedis_contracts.csv` ».

Deux vérifications faites depuis contredisent cette lecture.

**a) ENEDIS connaît parfaitement ces 138 points.** Les fiches client sont remplies
pour la totalité d'entre eux :

| Groupe | n | contrats | adresses | contract_summary | connexions |
|---|---|---|---|---|---|
| `ok_data` | 370 | 370/370 | 370/370 | 370/370 | 370/370 |
| `invalid_request` | 138 | **138/138** | **138/138** | **138/138** | **138/138** |
| `access_not_subscribed` | 40 | 40/40 | 40/40 | 40/40 | 40/40 |

Un identifiant inconnu d'ENEDIS ne peut pas renvoyer un contrat, une adresse postale,
un numéro de compteur et un état de raccordement. Le taux de remplissage moyen des
138 « inexistants » (23,4 champs) est même **supérieur** à celui des PRM qui
fonctionnent (21,2). Ce ne sont pas des identifiants erronés.

**b) `enedis_contracts.csv` n'a pas de « source amont » à corriger : la source est
ENEDIS.** `_load_prms()` (`enedis_customer_sync.py`) interroge d'abord l'endpoint
périmètre `/usage_point_id_perimeter/v1` et ne retombe sur le CSV qu'en cas d'échec.
Appel de contrôle passé le 2026-07-23 :

```
périmètre déclaré par ENEDIS : 567 PRM
enedis_contracts.csv         : 549 PRM
dans le CSV mais hors périmètre : 0
dans le périmètre mais hors CSV : 18
```

**Zéro PRM du CSV n'est étranger au périmètre de consentement.** Le référentiel local
est un sous-ensemble strict de ce qu'ENEDIS déclare lui-même. Il n'y a rien à
remonter à une source amont — la question « d'où viennent ces identifiants ? » a pour
réponse : d'ENEDIS.

`ADAM-ERR0155` ne signifie donc pas « ce PRM n'existe pas », mais « **pas de mesure
recevable pour ce point sur cette période** ».

## 2. Cause réelle : deux champs qu'ENEDIS nous donne déjà et qu'on n'exploite pas

`enedis_connections.csv` contient `connection_state`, `enedis_contract_summary.csv`
contient `services_level`. Ces deux fichiers sont téléchargés à chaque sync
contractuelle et **ne sont utilisés nulle part** dans la logique de collecte.

Croisés avec les outcomes, ils expliquent la quasi-totalité des échecs :

| `connection_state` | `ok_data` | `invalid_request` | `access_not_subscribed` |
|---|---|---|---|
| Alimenté | **370** | 48 | 31 |
| Coupé | 0 | 50 | 2 |
| Non alimenté | 0 | 39 | 3 |
| Limité | 0 | 1 | 4 |

**Les 370 PRM qui remontent des données sont exactement les 370 PRM « Alimenté ».**
La correspondance est parfaite, sans une seule exception.

| `services_level` | `ok_data` | `invalid_request` |
|---|---|---|
| Communicant (ouvert aux services) | 333 | 26 |
| Communicant (non ouvert aux services) | 0 | 9 |
| Non communicant | **0** | **52** |
| (vide) | 37 | 51 |

Aucun compteur « Non communicant » ne remonte de donnée — c'est une impossibilité
physique, pas un incident : ces compteurs n'ont pas de télérelève.

## 3. Les 179 PRM muets reclassés par cause

En appliquant ces deux critères, les 179 se répartissent ainsi (montants = électricité
facturée constatée en base sur ces PRM) :

| Cause | PRM | dont facturés | € TTC facturés | Nature |
|---|---|---|---|---|
| **A** — point coupé / non alimenté | 90 | 7 | 5 743 | Normal. Pas de consommation à remonter. |
| **B** — compteur non communicant | 36 | 31 | 21 394 | Impossible techniquement (pas de Linky). |
| **C** — droit d'accès manquant | 40 | 25 | 42 881 | Démarche contractuelle ENEDIS. |
| **D** — anomalie réelle | 13 | 4 | 347 | Alimenté **et** communicant ouvert : devrait marcher. |
| Total | 179 | 67 | 70 365 | |

**Le gisement de qualité de données n'est pas de 179 PRM mais de 53** (C + D), dont
29 seulement portent de la facturation. Les 126 autres (A + B) ne sont pas un défaut :
ce sont des points qu'on interroge alors qu'il est acquis qu'ils ne peuvent rien
renvoyer. Ils consomment ~126 appels API par jour pour rien et polluent le diagnostic.

Le seul groupe qui justifie un ticket technique est **D, 13 PRM**, et son enjeu
financier est marginal (347 €).

## 4. 60 PRM facturés absents du référentiel — et ce ne sont pas les nôtres

Croisement `energy_invoice_sites` × référentiel ENEDIS :

| | PRM | € TTC facturés | Part |
|---|---|---|---|
| Facturés **et** dans le référentiel | 437 | 691 026 | 60 % |
| Facturés et **absents du référentiel** | **60** | **464 829** | **40 %** |
| Total facturé | 497 | 1 155 855 | 100 % |

⚠️ Ces montants sont ceux **facturés sur la fenêtre couverte en base** (majoritairement
janvier→juin 2026), **pas des montants annuels** : la base ne contient que 8 mois de
factures (voir `fluides-elec-drilldown-projections-decisions.md` §4). Ne pas les
présenter comme des chiffres annuels dans un courrier externe. La part de 40 % est en
revanche valide, les deux termes du ratio portant sur la même fenêtre.

**40 % de la dépense d'électricité porte sur des compteurs totalement invisibles du
module Énergie** : pas de consommation, pas de courbe de charge, pas de performance
DJU, pas d'atterrissage. Les plus gros du parc sont dedans (69 558 €, 53 544 €,
43 689 €, 29 466 €…), et 16 des 60 ont un identifiant en `30002…`, format typique des
sites de forte puissance.

Ventilation par rapport au consentement ENEDIS :

- **59 PRM / 464 824 € sont hors du périmètre de consentement.**
- **1 PRM / 5 €** est dans le périmètre mais absent du CSV → simple retard de sync.

### Ce ne sont pas nos compteurs : ce sont ceux de l'Agglo

Première lecture (2026-07-23, matin) : « demander à ENEDIS d'étendre le consentement
à ces 59 points ». **Cette demande aurait été rejetée, et à juste titre.**

Les 549 PRM du périmètre de consentement portent tous **un seul et même SIRET** :

```
549 / 549  ->  21340301700014   (Commune de Sète)
```

Les 60 PRM absents du référentiel sont, eux, des équipements de **Sète Agglopôle
Méditerranée** — personne morale distincte. Leur nature ne laisse pas de doute, elle
recoupe exactement les compétences intercommunales :

| Compétence agglo | Sites concernés parmi les 60 |
|---|---|
| Assainissement / eau | STEP Mèze, Villeveyrac, Mireval, Montbazin ; lagunages Vic-la-Gardiole, Onglous, Pradels ; PR pluviaux ; pôle cycle de l'eau |
| Déchets | déchetteries de Mèze, Balaruc, Marseillan, Montbazin, Frontignan, Sète ; pôle déchets Marseillan ; plate-forme déchets verts |
| Culture intercommunale | conservatoire intercommunal, médiathèques (Mitterrand, Malraux, Olympe de Gouges, intercommunale), Théâtre Molière |
| Gens du voyage | aires de Marseillan, Frontignan, Mèze |
| Développement éco / tourisme | Écosite, complexe Oikos, pépinière Flexys, musée de l'étang de Thau, villa gallo-romaine |

Un site s'appelle littéralement **« CA DU BASSIN DE THAU »** — l'ancien nom de l'agglo.
À l'inverse, les regroupements du groupe couvert sont sans ambiguïté ceux de la Ville :
`212-ENSEIGNEMENT`, `BUREAU DES FESTIVALS`, `RH - SYNDICATS`, `CIRC - VOIRIE`,
`COMPLEXE FUNERAIRE`, `PORT DES QUILLES`.

**Il n'y a donc aucun défaut de référentiel ici non plus.** Le module ingère les
factures d'un **groupement de commandes** (marché ENGIE `2024-FCS-03`) qui couvre Ville
**et** Agglo, alors que le consentement ENEDIS ne couvre — et ne peut couvrir — que la
Ville. `ADAM-ERR0191` est exactement le mécanisme qui protège ça : une collectivité ne
peut pas consommer la donnée de comptage d'une autre personne morale.

Les « 40 % de la dépense invisible » ne sont pas un trou de données mais un **écart de
périmètre juridique entre deux sources**. Le chiffre est réel, sa lecture change
complètement : il ne mesure pas ce qu'on a perdu, il mesure ce qui ne nous appartient pas.

Réserve de méthode : la propriété des sites est déduite de leur nature et de leur
libellé, pas d'une pièce contractuelle. Le SIRET unique côté ENEDIS est en revanche un
fait. Une confirmation propre passerait par la liste des membres du groupement de
commandes `2024-FCS-03`.

À l'inverse, **112 PRM du référentiel n'ont jamais été facturés** : à instruire côté
fournisseur (points suivis pour rien, ou facturation rattachée ailleurs).

Enfin, **18 PRM présents dans le périmètre ENEDIS ne sont pas dans le CSV** : la
dernière sync contractuelle date du 2026-07-17 et n'a pas été rejouée depuis. Un
simple relancement les intègre.

## 5. Décisions

### D1 — Ne plus interroger les points structurellement muets *(proposé, à arbitrer)*

Filtrer la liste de collecte sur `connection_state == "Alimenté"`, en excluant les
`services_level` explicitement « Non communicant ». Effet : ~126 appels API
quotidiens économisés, et le diagnostic ne remonte plus que des écarts réels.

Garde-fou nécessaire : ces états changent (un point coupé peut être réalimenté). Le
filtre doit se fonder sur la fiche contractuelle **rafraîchie**, et un point exclu
doit redevenir éligible dès que son état repasse à « Alimenté ». Ne jamais figer la
liste en dur.

Alternative écartée : supprimer ces PRM du référentiel. Ils sont légitimes et une
partie est facturée — les perdre créerait un angle mort supplémentaire.

### D2 — Le diagnostic doit nommer la cause, pas le code d'erreur *(proposé)*

`enedis_data_diagnostic.json` expose aujourd'hui `invalid_request`, qui ne dit rien
d'exploitable — c'est ce qui a conduit à la mauvaise conclusion du 22/07. Le
remplacer par les causes A/B/C/D du §3, calculées à partir des deux champs ENEDIS.

### D3 — Une seule demande à ENEDIS, et elle est petite *(à porter par la Ville)*

**Ouverture du service ACCES sur les 40 PRM du groupe C** (42 881 € facturés sur la
fenêtre couverte). Ces points portent le SIRET de la Ville : la demande est recevable.
Liste : colonne `cause = C` de `prm_referentiel_qualite.csv`.

~~Extension du consentement aux 59 PRM hors référentiel~~ — **abandonné** : ces points
appartiennent à Sète Agglopôle Méditerranée (§4). La Ville n'a aucun titre à demander
leur donnée de comptage ; seule l'Agglo, en tant que titulaire, peut consentir pour
eux. Ce n'est pas une démarche ENEDIS, c'est une question de gouvernance (D5).

### D4 — Relancer la sync contractuelle *(sans risque, à faire)*

Récupère les 18 PRM du périmètre absents du CSV et rafraîchit `connection_state` /
`services_level`, prérequis de D1.

### D5 — Trancher le périmètre du module : Ville seule, ou Ville + Agglo ? *(bloquant, décision non technique)*

C'est la question de fond que le §4 met au jour. Aujourd'hui le module est incohérent :
il ingère les factures de deux personnes morales et ne collecte la donnée ENEDIS que
pour une seule. Deux issues, exclusives :

- **Ville seule.** Les 60 PRM Agglo sortent du périmètre de facturation. Les « 40 % de
  dépense invisible » disparaissent — c'était un artefact d'import. Le module redevient
  cohérent, et les indicateurs (€/kWh, atterrissage, part fournisseur) cessent d'être
  calculés sur une assiette dont 40 % n'a pas de consommation en face. Coût : un filtre
  par entité à l'import des factures.
- **Ville + Agglo.** Il faut alors que l'Agglo accorde son propre consentement ENEDIS,
  et que la plateforme porte une notion d'**entité juridique** de bout en bout
  (référentiels, factures, patrimoine, restitutions). Ce n'est pas un réglage, c'est
  une dimension structurante à ajouter au modèle de données.

Tant que ce choix n'est pas fait, tout indicateur électricité agrégé mélange deux
périmètres et n'est pas défendable devant les finances. À arbitrer avant d'investir
ailleurs sur le module.

## 6. Reste à faire

- **Arbitrer D5** — préalable à tout le reste.
- Arbitrer D1 et D2 (code, périmètre limité à `enedis_sync.py` + `enedis_customer_sync.py`).
- Confirmer la composition du groupement de commandes `2024-FCS-03` (pièce
  contractuelle), pour asseoir le §4 sur autre chose qu'une déduction par libellé.
- Instruire les 112 PRM suivis mais jamais facturés.
