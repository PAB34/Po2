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

---

## 7. Livré (2026-09-09)

`cibles-tertiaires-agglo.xlsx` — trois feuilles.

### 7.1 Feuille « Cibles tertiaires » — 33 455 lignes × 42 colonnes

| Enrichissement | Couverture |
| --- | ---: |
| Établissements collectés (15 communes) | **33 455** — dont 18 263 actifs, 15 192 fermés |
| Parcelle cadastrale rattachée | 31 651 (94,6 %) |
| Propriétaire des murs | 19 744 (59 %) — nul à Agde par construction |
| DPE tertiaire rattaché | 11 976 (35,8 %) |
| **Présomption Éco Énergie Tertiaire** | **168** |

Agde pèse **11 607 établissements**, Sète 8 494, Frontignan 2 915.

**Décision 5 — les fermés sont conservés, avec une colonne `Activité`** (Actif /
Fermé) en tête de feuille. L'état brut de l'API vaut `A` ou `F`, illisible dans
un filtre Excel. Un établissement fermé n'est pas un prospect mais signale un
local vacant, donc un propriétaire à démarcher. Le tri place les actifs d'abord.

### 7.2 Feuille « Partenaires RGE » — 93 entreprises

Le vivier du §6 du business model, obtenu par le filtre `est_rge` de l'API : des
entreprises qualifiées, donc assurées pour ce qu'elles annoncent. Constituer
cette liste à la main aurait pris des jours.

### 7.3 Deux défauts corrigés avant livraison

**1. Sur-attribution massive des DPE.** Premier passage : 21 468 lignes
rattachées pour **1 480 DPE existants**, un même DPE attribué jusqu'à
**6 968 fois**. Cause : les adresses sans numéro ni voie produisaient une clé
vide des deux côtés, qui appariait tout avec tout. Les clés incomplètes sont
désormais exclues.

**2. Le découpage d'adresse ne rendait presque rien.** L'annuaire des entreprises
livre l'adresse d'un bloc, complément compris — `BATIPAUME VILLAGE VACANCES 20
CHEMIN RAYMOND FAGES 34300 AGDE` : le numéro n'est ni au début ni isolé, et la
fin porte le code postal. Le découpage retire d'abord le code postal et ce qui
suit, puis cherche le dernier couple « numéro + type de voie » : **25 718
adresses structurées** sur 33 455, contre quasiment aucune auparavant.

### 7.4 Fiabilité du DPE, dite ligne par ligne

| Niveau | Lignes |
| --- | ---: |
| élevée — un seul établissement à cette adresse | 36 |
| moyenne — bâtiment partagé, le DPE décrit le bâtiment | 2 411 |
| faible — position approchée | 9 529 |

Une colonne compte les établissements partageant le même DPE. Plusieurs
occupants d'un immeuble de bureaux partagent légitimement un diagnostic : le
classeur le dit au lieu de le taire.

| Date | Décision | Motif |
| --- | --- | --- |
| 2026-09-09 | Fermés conservés, colonne `Activité` explicite | Un local fermé est un indice de vacance, pas un déchet ; le tri suffit |
| 2026-09-09 | Clés d'adresse incomplètes exclues du rapprochement | Une clé vide appariait 6 968 établissements à un seul DPE |

---

## 8. Repérer les propriétaires sans pilotage (2026-09-09)

### 8.1 OPERAT : les déclarants ne sont pas publics

Recherche faite dans le catalogue de l'ADEME. **Aucun jeu nominatif n'existe** :
les données issues d'OPERAT sont publiées **agrégées**, sans SIRET ni adresse. Le
grain le plus fin est la commune (`9uk1jf62hz215jablj6tvn71` — nombre de
déclarations, surface et consommation déclarées).

Impossible, donc, de nommer un non-déclarant. Mais le ratio *déclarations /
établissements actifs* dit **où** le décret est le moins appliqué :

| Commune | Déclarations | Surface déclarée | 1 déclaration pour |
| --- | ---: | ---: | ---: |
| Frontignan | 60 | 129 169 m² | 55 étab. |
| Sète | 94 | 348 392 m² | 90 |
| Agde | 93 | 206 264 m² | 125 |
| **Marseillan** | **11** | 30 996 m² | **219** |
| **Mèze** | **8** | 16 476 m² | **255** |
| Bouzigues, Loupian, Montbazin, Villeveyrac | **0** | — | — |

Marseillan et Mèze sont deux à trois fois moins déclarés que Frontignan à parc
comparable ; quatre communes n'ont aucune déclaration. Intégré au score.

### 8.2 Deux idées reçues démenties par les données

**L'âge du bâti ne prédit pas la consommation.** Médianes par époque, en
kWh EP/m²/an : 151 avant 1975, 120 entre 1975 et 1989, 163 entre 1990 et 2004,
157 entre 2005 et 2012, **132 après 2013**. Aucune tendance. Et **28 % des
bâtiments postérieurs à 2005 sont classés D à G** — sur du récent, la
performance tient à la conduite, pas à l'enveloppe. C'est précisément ce que
l'offre vend, et cela invalide le ciblage par ancienneté du bâti.
*(échantillon de 244 bâtiments — à consolider)*

**L'écart au benchmark est un outil de conversion, pas de ciblage.** Il n'est
calculable que sur les 572 bâtiments à consommation renseignée, soit une
fraction des 33 455 établissements. Il sert en rendez-vous, pas pour bâtir une
liste d'appels.

### 8.3 Le score de non-pilotage

Dix signaux pondérés, mêlant assumément **négligence** et **qualification** :
une cible négligée qui n'est pas un vrai site d'exploitation ne vaut pas un appel.

| Signal | Points |
| --- | ---: |
| Surface DPE > 1 000 m² (présomption décret tertiaire) | 3 |
| Détention de la parcelle depuis plus de 20 ans | 2 |
| Propriétaire détenant 5 locaux ou plus | 2 |
| Bâti postérieur à 2005 classé D à G | 2 |
| Établissement employeur | 2 |
| Segment prioritaire 1 ou 2 | 2 |
| Secteur à fort écart interquartile | 1 |
| Entreprise créée avant 2011 | 1 |
| Entreprise de 3 établissements ou plus | 1 |
| Commune peu déclarante à OPERAT | 1 |

**Première calibration abandonnée** : elle cherchait la date de mutation sur les
seuls *locaux professionnels*, ce qui ne renseignait que 22 % des cibles — un
hôtel ou un commerce en pied d'immeuble n'est pas toujours cadastré ainsi. En
élargissant à tous les locaux de la parcelle, la couverture passe à **40 009
parcelles**. Le critère « aucun DPE rattaché » a été retiré : à 67 %, il ne
discriminait rien.

### 8.4 Livré : feuille « Liste d'appels »

**214 cibles** notées 7 et plus, actives, sur les segments prioritaires 1 à 3 —
dont 52 au-delà de 9. Par commune : Sète 65, **Marseillan 48**, Balaruc-les-Bains
28, Mèze 19, Frontignan 16, Agde 11. Marseillan et Mèze remontent, conformément
au signal OPERAT.

Noms de tête : Vacantel, la SEM d'aménagement du Bassin de Thau, Goélia Gestion,
Miléade, Indivision Vataire (7 022 m²), S'Antoni Immobilier, Human Immobilier,
Gesim. Chaque ligne porte la colonne **« Signaux retenus »**, qui dit pourquoi
elle est là — de quoi préparer l'appel.

| Date | Décision | Motif |
| --- | --- | --- |
| 2026-09-09 | Pas de ciblage par âge du bâti | Les données montrent l'absence de corrélation avec la consommation |
| 2026-09-09 | Score de qualification **et** de négligence, pas seulement de gisement | Une cible négligée sans exploitation réelle ne vaut pas un appel |
| 2026-09-09 | Signal OPERAT retenu à la maille communale | Le nominatif n'existe pas ; le ratio par commune reste discriminant |

---

## 9. Surface des bâtiments — pourquoi seulement 168 présomptions (2026-09-09)

### 9.1 Le goulot

L'assujettissement était présumé sur la `surface_shon` du **DPE tertiaire**. Or il
n'existe que **1 480 DPE tertiaires** sur le territoire, rattachés à 11 976
établissements, dont une partie sans surface renseignée : d'où **168 présomptions
sur 33 455 établissements**.

La surface de parcelle ne peut pas y suppléer — c'est celle du **terrain**. Un
camping de trois hectares a une parcelle immense et quelques centaines de mètres
carrés bâtis ; le seuil du décret porte sur la surface de plancher d'activité.

### 9.2 La BD TOPO comble le trou

L'IGN publie chaque bâtiment avec son usage, sa hauteur, son nombre d'étages et
son emprise. API Géoplateforme (WFS), ouverte, sans clé. `sig_agglo_batiments.py`
en extrait **7 865 bâtiments d'activité** sur le bassin et Agde :

| Usage | Bâtiments | dont ≥ 1 000 m² estimés |
| --- | ---: | ---: |
| Commercial et services | 5 090 | 621 |
| Industriel | 1 489 | 472 |
| Agricole | 980 | 151 |
| Religieux | 170 | 69 |
| Sportif | 136 | 67 |

Surface de plancher estimée = emprise au sol × nombre d'étages, avec la hauteur
divisée par trois en repli. Les aires sont calculées par la formule du lacet sur
des géométries demandées directement en Lambert-93 — pas de `shapely` sur ce
poste. **12 590 établissements** sont rattachés à un bâtiment (≤ 40 m, seuil plus
serré que pour la parcelle : un bâtiment est un objet précis), dont **2 477
au-delà de 1 000 m²**.

### 9.3 Le contrôle qui a changé le nom de la colonne

Sur les **7 610 établissements où DPE et estimation coexistent** :

| Mesure | Résultat |
| --- | ---: |
| Ratio médian estimation / DPE | **3,36** |
| Estimation dans un facteur 2 du DPE | 26 % |
| Même verdict sur le seuil de 1 000 m² | 81 % |
| **Faux positifs** (estimé ≥ 1 000, DPE < 1 000) | **1 390** |
| Faux négatifs | 85 |

**Ce n'est pas une erreur de calcul, c'est un changement d'objet** : le DPE mesure
un **local** — une boutique de 80 m² dans un immeuble — quand l'estimation mesure
le **bâtiment entier**. Les deux sont justes, ils ne répondent pas à la même
question.

**Décision 6 — la colonne ne s'appelle pas « présomption ».** Avec 1 390 faux
positifs sur 2 477, la nommer ainsi aurait conduit à annoncer une obligation
inexistante à un prospect. Elle devient `Bâtiment — grand volume`, et le DPE garde
le mot « présomption » quand il existe.

**Décision 7 — une colonne `Cumul tertiaire possible`.** Le seuil du décret
s'apprécie **par site en cumulant les activités** : un immeuble de 1 200 m²
abritant plusieurs commerces peut être assujetti alors qu'aucun local ne dépasse
le seuil. La colonne croise donc le grand volume et le nombre d'établissements
recensés dans le même bâtiment — c'est la lecture correcte du décret, et elle
récupère une partie des « faux positifs » comme vraies cibles.

Le score conserve ce signal à **2 points** (contre 3 pour la surface DPE), et
seulement quand le DPE est muet.

| Date | Décision | Motif |
| --- | --- | --- |
| 2026-09-09 | BD TOPO ajoutée comme source de surface | 1 480 DPE ne couvraient pas le parc ; 7 865 bâtiments d'activité le couvrent |
| 2026-09-09 | « Grand volume » et non « présomption » | 1 390 faux positifs sur 2 477 : le mot aurait fait annoncer une obligation inexistante |
| 2026-09-09 | Colonne de cumul tertiaire | Le décret s'apprécie au cumul par site, pas par local |

### 9.4 Feuille « Décret tertiaire » — la couverture par commune

Les non-déclarants ne sont pas nommables, mais ils sont **localisables** : en
rapportant les surfaces déclarées à OPERAT au parc de bâtiments d'activité de
plus de 1 000 m² estimés par la BD TOPO, on obtient un taux de couverture.

| Commune | Bât. > 1 000 m² | Surface estimée | Déclaré | Couverture | Non déclaré |
| --- | ---: | ---: | ---: | ---: | ---: |
| Agde | 175 | 664 798 | 206 264 | **31 %** | **458 534** |
| Sète | 167 | 637 991 | 348 392 | 55 % | 289 599 |
| Marseillan | 25 | 96 581 | 30 996 | 32 % | 65 585 |
| Balaruc-le-Vieux | 14 | 70 639 | 24 394 | 35 % | 46 245 |
| Mèze | 25 | 61 900 | 16 476 | 27 % | 45 424 |
| Mireval | 22 | 53 589 | 8 341 | **16 %** | 45 248 |
| Villeveyrac | 9 | 33 472 | 0 | **0 %** | 33 472 |
| Poussan | 22 | 52 342 | 23 751 | 45 % | 28 591 |
| Gigean | 21 | 43 209 | 14 919 | 35 % | 28 290 |
| Frontignan | 58 | 155 401 | 129 169 | 83 % | 26 232 |
| Loupian, Bouzigues, Montbazin | 16 | 38 087 | 0 | **0 %** | 38 087 |
| Vic-la-Gardiole | 6 | 14 062 | 9 586 | 68 % | 4 476 |
| Balaruc-les-Bains | 26 | 52 758 | 56 022 | **106 %** | 0 |

**Environ 1,1 million de m² tertiaires non déclarés** sur le périmètre.

**Décision 8 — le tableau se lit en relatif, jamais en absolu.** Balaruc-les-Bains
dépasse 100 %, ce qui prouve que l'estimation sous-estime autant qu'elle
surestime : un bâtiment de plus de 1 000 m² n'est pas toujours assujetti, et le
périmètre OPERAT capte des surfaces que la BD TOPO ne voit pas (bureaux en
immeuble mixte). C'est **l'écart entre communes à parc comparable** qui porte
l'information — Frontignan à 83 % contre Mèze à 27 % ne s'explique guère
autrement que par un retard de déclaration.

**La donnée nominative n'existe pas, et la question se pose au téléphone.** Le
script d'appel intègre&nbsp;: « Votre bâtiment dépasse probablement 1 000 m², il
est donc sans doute assujetti. Avez-vous un compte OPERAT à jour ? » Les trois
réponses possibles qualifient toutes le prospect.

**Piste non vérifiée** : le dispositif de sanction prévoit la publication des
mises en demeure restées sans effet. Si cette publication est effective, elle
constituerait la seule liste nominative légale de non-déclarants. À rechercher.

| Date | Décision | Motif |
| --- | --- | --- |
| 2026-09-09 | Feuille « Décret tertiaire » ajoutée au classeur | Le nominatif n'existe pas ; la couverture communale oriente l'effort |
| 2026-09-09 | Lecture relative imposée dans la feuille | Balaruc à 106 % montre que l'estimation n'est pas un absolu |
