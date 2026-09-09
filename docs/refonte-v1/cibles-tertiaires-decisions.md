# Cibles tertiaires — AMO performance énergétique (décisions)

> Sujet ouvert le 2026-09-09. Fait suite au repositionnement de l'offre vers
> l'ingénierie commerciale et l'AMO en performance énergétique **tertiaire**
> (`business_model_AMO_performance_energetique_tertiaire.md`).
> Le classeur résidentiel `locaux-agglo-complet.xlsx` reste inchangé ;
> ce sujet produit un **fichier distinct**.

## 1. Le constat qui ouvre le sujet

Le classeur cadastral porte **8 490 locaux commerciaux ou industriels**, mais le
cadastre **ne dit jamais l'activité** : 8 034 d'entre eux sont rangés sous le seul
libellé « Local professionnel ». Un hôtel, un cabinet dentaire et un garage y sont
indiscernables. Pour une prospection B2B ciblée, ce fichier donne des murs, pas
des interlocuteurs.

## 2. Existant vérifié (2026-09-09)

| Source | Contenu | Verdict |
| --- | --- | --- |
| Classeur cadastral | type de local, propriétaire, parcelle | ne qualifie pas l'activité |
| Couche SIG 60 `economie.vmp_etab_eco` | 27 448 établissements, NAF + SIRET + effectif | **bornée à l'agglo** : 1 seule ligne à Agde ; 4 560 sans commune renseignée |
| Couche SIG 755 métiers de bouche | 1 750 commerces | sous-ensemble de la précédente |
| **API Recherche d'entreprises** (data.gouv.fr) | NAF, SIRET, enseignes, adresse, **latitude/longitude**, tranche d'effectif, état administratif, qualifications RGE | **ouverte, sans clé**, couvre Agde |
| **DPE Tertiaire ADEME** (`j9ol0fwjqckyf49vr29nknbu`) | `surface_shon`, `surface_utile`, conso kWh/m², étiquette, relevés N-1/N-2/N-3 | ouverte ; 415 bâtiments à Agde, ~1 100 sur l'agglo |

**Décision 1 — la couche SIG 60 est écartée au profit de l'API nationale.** Elle
s'arrête à l'agglo, laisse 4 560 lignes sans commune et ne porte pas de
coordonnées. L'API nationale est homogène sur les 15 communes, donne la position
et l'état administratif (un établissement fermé n'est pas un prospect).

## 3. Périmètre retenu

**14 communes de l'agglo + Agde** (34003), décidé le 2026-09-09.

Agde n'est pas un complément marginal — c'est le premier gisement touristique du
périmètre : **109 hôtels, 65 campings, 306 hébergements courte durée, 935
restaurants**, contre 91 hôtels et 51 campings sur toute l'agglo.

⚠️ **Ce qu'on n'aura pas à Agde** : aucun propriétaire cadastral (périmètre de
convention DGFiP, cf. `sig-agglo-proprietaires-decisions.md` §5 et §6.10). Le
fond cadastral, lui, couvre Agde : le rattachement à la parcelle reste possible,
seul le nom du propriétaire manquera. Une colonne le dira explicitement.

**Décision 2 — aucun filtre sur l'effectif.** Tous les établissements sont
retenus, y compris les SCI sans salarié. La priorité est portée par une colonne,
pas par une exclusion en amont : une SCI patrimoniale sans salarié peut détenir
plusieurs bâtiments.

## 4. Segments et codes d'activité

Les 12 segments du business model, traduits en NAF. Le rang de priorité suit la
logique de ciblage du modèle (plusieurs bâtiments, CVC lourd, factures
significatives, pas de responsable technique interne).

| Rang | Segment | NAF |
| ---: | --- | --- |
| 1 | Hôtels, campings, villages vacances, résidences de tourisme | 55.10Z, 55.20Z, 55.30Z, 55.90Z |
| 2 | Administrateurs de biens, syndics, agences immobilières | 68.32A, 68.32B, 68.31Z |
| 3 | Santé et hébergement médico-social | 86.10Z, 87.10A/B/C, 87.30A/B, 87.20A/B |
| 3 | Grandes et moyennes surfaces | 47.11B→F, 47.19A/B, 47.30Z, 47.52B, 47.54Z |
| 4 | Concessions et garages | 45.11Z, 45.19Z, 45.20A/B |
| 4 | Foncières, SCI, marchands de biens | 68.20A/B, 68.10Z, 64.20Z |
| 5 | Industrie et agroalimentaire | divisions 10, 11, 20, 22, 23, 25 |
| 5 | Équipements sportifs et de loisirs | 93.11Z, 93.21Z |
| 6 | Restauration | 56.10A/C, 56.21Z, 56.29A/B, 56.30Z |

Le rang 6 pour la restauration est délibéré : nombreux mais mono-site, petite
surface, décision courte — du volume de rendez-vous, pas du récurrent. Les
groupes de restauration seront isolés par leur SIREN commun (`nombre_etablissements`).

## 5. Rattachements prévus, et leur fiabilité

| Donnée ajoutée | Méthode | Fiabilité attendue |
| --- | --- | --- |
| Parcelle cadastrale | coordonnées de l'établissement → centre de parcelle le plus proche (≤ 60 m) | approchée, distance écrite |
| Propriétaire du local | via le classeur cadastral, par la parcelle | 14 communes seulement, jamais Agde |
| Surface et étiquette DPE tertiaire | adresse exacte puis coordonnées | à mesurer avant promesse |
| Assujettissement Éco Énergie Tertiaire | `surface_shon` ≥ 1 000 m² | **présomption**, pas un constat |

**Décision 3 — l'assujettissement EET est présenté comme une présomption.** Le
seuil de 1 000 m² s'apprécie par site et par activité, en cumulant les surfaces ;
un DPE ne couvre qu'un bâtiment. La colonne servira à trier les appels, jamais à
affirmer une obligation à un prospect.

**Décision 4 — reprendre les garde-fous du classeur résidentiel.** Toute donnée
rapprochée porte sa méthode et sa distance ; aucune donnée d'immeuble n'est
attribuée à un établissement nommé ; les clés de jointure sont validées sur la
forme de leurs valeurs, jamais sur le nom de la colonne.

## 6. Questions ouvertes

1. Faut-il conserver les établissements **fermés administrativement** (utile pour
   repérer un bâtiment vacant à reconvertir) ou ne garder que les actifs ?
2. Les **qualifications RGE** exposées par l'API identifient les entreprises du
   bâtiment qualifiées : les extraire dans une feuille séparée comme **vivier de
   partenaires** (§6 du business model) ?
3. Étendre plus tard à Béziers et Montpellier ? Écarté pour l'instant.

| Date | Décision | Motif |
| --- | --- | --- |
| 2026-09-09 | API Recherche d'entreprises plutôt que la couche SIG 60 | La couche s'arrête à l'agglo et n'a ni coordonnées ni état administratif |
| 2026-09-09 | Périmètre = 14 communes + Agde | Agde est le premier gisement touristique, malgré l'absence de propriétaires |
| 2026-09-09 | Aucun filtre d'effectif ; la priorité est une colonne | Une SCI sans salarié peut détenir plusieurs bâtiments |
