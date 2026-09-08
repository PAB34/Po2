# Collecte Airbnb – 14 communes de Sète Agglopôle – décisions avant codage

> Statut : **note de décisions soumise à validation**, aucun code V2 écrit à ce stade.
> Date : 2026-09-08. Auteur : session Claude Code.
> Objet : produire une base des locations courte durée Airbnb des 14 communes,
> puis la rapprocher du classeur cadastral `sig_agglo_data\locaux-agglo-complet.xlsx`.
> Note de concept métier associée : `sig_agglo_data\etude_concept_intendance_valorisation_thau_10_derniers_echanges.md`.

---

## 1. Existant vérifié

### 1.1 Le POC fourni (`airbnb_sete_poc.zip`)

Trois fichiers : `airbnb_sete_inventory.py` (334 lignes), un README, un `requirements`
(`pyairbnb==2.2.2`, pandas, requests, shapely).

Ce que le POC fait **bien**, et qu'il faut garder :

| Point | Détail |
|---|---|
| Découpage en tuiles | `split_bbox()` en grille régulière, principe correct |
| Contour officiel | `geo.api.gouv.fr` en GeoJSON, avec les 3 formats de réponse gérés |
| Dédup par `room_id` | correcte, et mémorise les tuiles d'origine (`_tiles_seen`) |
| Champ `longitud` | le typo de pyairbnb est déjà géré ligne 151 — piège réel, bien vu |
| Ne filtre pas sur le contour | garde les points hors contour comme indicateurs, cohérent avec le flou Airbnb |
| Aucun contournement | pas de tentative sur CAPTCHA/auth, explicitement documenté |

### 1.2 Le classeur cadastral (déjà construit, à ne pas refaire)

`sig_agglo_data\locaux-agglo-complet.xlsx` — 176 695 lignes × 224 colonnes, une ligne
par local, feuilles « Locaux agglo » + « Dictionnaire ». Colonnes de rattachement
disponibles : `Réf. cadastrale (id_par)`, `Invariant`, `Adresse du bien` (maille
**parcelle**), `Longitude`/`Latitude` WGS84 (maille **parcelle**, couche 943),
`Type de local`, `Propriétaire hors agglo` (21 306 non-résidents),
`DPE — surface habitable moyenne (m²)`.

⚠️ `sig_agglo_data/` contient des données personnelles et porte son propre
`.gitignore` (`*`). **Aucun `git add` dans ce dossier.**

---

## 2. Mesures réelles effectuées ce jour (sondes, pas des estimations)

Environnement : Python 3.12.10, `pyairbnb==2.2.2` installé dans le scratchpad.
Quatre sondes exécutées contre Airbnb depuis le poste.

### M1 — Le réseau passe. ✅
`fetch_stays_search_hash()`, `search_all_from_url()` et `get_details()` répondent
depuis le poste entreprise. Pas de blocage proxy constaté.

### M2 — Plafond de 40 résultats par recherche, quelle que soit l'emprise. ⛔ **critique**

| Emprise testée | Résultats | `room_id` uniques |
|---|---:|---:|
| Sète entier (bbox du POC, ~0,18° × 0,10°) | **40** | 40 |
| Quart nord-est de Sète | **40** | 40 |
| Centre-ville dense (~1,5 km × 1,7 km) | **40** | 40 |

Une emprise 100 fois plus grande rend exactement le même nombre d'annonces qu'une
petite. C'est un **plafond**, pas un comptage.

**Conséquence sur le POC** : avec `--grid 5` (25 tuiles), le plafond théorique est
25 × 40 = **1 000 annonces** avant dédup — pour un parc sétois qui se compte en
milliers. Le POC sous-collecte massivement, et **silencieusement** : rien dans sa
sortie ne signale qu'une tuile a été tronquée. Son propre message final
(« si le nombre est très faible, augmente `--grid` ») montre que le symptôme avait
été vu, mais la cause — la saturation par tuile — n'est pas traitée.

### M3 — Le NER (numéro d'enregistrement) n'est PAS exposé. ⛔ **critique**

Recherche sur 6 fiches détail complètes : aucun numéro d'enregistrement.
La seule occurrence du mot « enregistrement » trouvée était dans un **commentaire de
voyageur** (« l'enregistrement automatique » = arrivée autonome) — faux positif.
Aucune chaîne de la forme `343xx…` (préfixe INSEE d'un NER héraultais) dans le JSON.

**Conséquence** : la source n°1 du plan de rapprochement (« NER lorsqu'il est
disponible ») **tombe avec pyairbnb seul**. C'est le point qui coûte le plus cher au
projet, parce que le NER était la seule clé *exacte* vers l'adresse. Voir Q1.

### M4 — `host_id` : vide en direct, mais récupérable de façon fiable. ✅

`det["host"]["id"]` est vide sur 6/6 fiches, et `get_host_details()` renvoie une
erreur GraphQL Airbnb (`passportStamps`, `CLIENT_INPUT`) sur 6/6.

Contournement trouvé et validé : le `reviewee` d'un avis **est l'hôte de l'annonce**,
et son profil porte l'identifiant dans
`reviews[].reviewee.userProfilePicture.onPressAction.url` = `/users/profile/<host_id>`.

Résultat : **host_id récupéré sur 8/8 annonces testées**, avec le prénom de l'hôte
(dont un « Alexandra GESTION », révélateur d'une conciergerie professionnelle —
exactement la cible analytique visée).

⚠️ Limite : le procédé exige **au moins un avis**. Une annonce neuve sans avis n'aura
pas de `host_id`. Sur l'échantillon les annonces avaient 3 à 585 avis, mais le taux
réel sur tout le parc reste à mesurer au premier lot.

`get_listings_from_user()` existe dans la lib mais renvoie une liste **vide** : la
piste « demander à Airbnb les autres annonces d'un hôte » est inopérante. On
regroupera donc par `host_id` **à partir de notre propre collecte**, ce qui suffit
pour repérer les multi-annonces du territoire.

### M5 — Les équipements sont riches et exploitables. ✅

`amenities` = liste de 12 groupes, chacun avec `values[]` portant
`title` / `subtitle` / `icon` / `available` (booléen). Exemple réel relevé :

```
[Chauffage et climatisation]  Climatiseur portable, Ventilateurs portables, Chauffage d'appoint
[Parking et installations]    Stationnement gratuit dans la rue
[Internet et bureau]          Wifi
[Chambre et linge]            Lave-linge (Gratuit) dans le logement, …
[Non inclus]                  3 items  ← équipements explicitement ABSENTS
```

Deux enseignements : (a) les libellés sont **variés** (« Climatiseur portable »,
« Climatisation centralisée », « AC – split »…), donc les colonnes booléennes
demandées exigent un **lexique de motifs**, pas une égalité de chaîne ; (b) le groupe
« Non inclus » et le drapeau `available:false` permettent de distinguer
**absent** de **non renseigné** — distinction qu'il faut préserver (voir §4).

### M6 — Champs vides et champ très volumineux. ⚠️

Sur la fiche témoin : `description` = `""`, `highlights` = `[]`, `house_rules` vide,
`location_descriptions` = `[]`, `title` = `[]`. À confirmer sur un échantillon plus
large — s'ils sont systématiquement vides, la « description » demandée ne sera pas
disponible par cette voie.

À l'inverse `calendar` pèse **201 454 caractères pour une seule annonce** (12 mois
jour par jour, avec `available` et prix). C'est à la fois un coût de stockage
(≈ 1 à 2 Go de brut sur l'agglo) et une **opportunité forte** : le calendrier donne le
taux d'occupation et les jours réellement bloqués — précisément l'indicateur
« jours commercialisables » du concept d'intendance. Voir Q4.

---

## 3. Ce que ces mesures imposent à l'architecture V2

**D1 — Découpage récursif adaptatif, et non plus grille fixe.**
Toute tuile qui rend 40 résultats est réputée **saturée** et subdivisée en 4,
récursivement, jusqu'à rendre < 40 ou atteindre une profondeur plancher (~150 m de
côté). C'est la seule correction qui approche l'exhaustivité. Chaque tuile terminale
encore saturée est **journalisée comme zone d'incertitude** : on saura où l'inventaire
reste possiblement incomplet, au lieu de l'ignorer.

**D2 — Aucun chiffre d'exhaustivité ne sera annoncé sans contre-mesure.**
Le nombre collecté sera comparé à un dénombrement indépendant (page publique Airbnb,
et/ou données de taxe de séjour si tu y as accès) et le taux de couverture écrit dans
le rapport de collecte. Pas de « base exhaustive » proclamée sur la foi du scraper.

**D3 — Cache disque par `room_id`, une fiche = un fichier JSON.**
Le passage 2 ne rappelle jamais une fiche déjà en cache (avec TTL configurable). La
reprise sur erreur découle du cache : relancer reprend là où ça s'est arrêté.

**D4 — Rafraîchissement du hash + backoff.**
Le POC récupère `fetch_stays_search_hash()` une seule fois ; sur une collecte de
plusieurs heures il expirera. La V2 le renouvelle sur échec, avec backoff exponentiel
et plafond de tentatives.

**D5 — Séparer strictement brut et dérivé.**
`raw/` (JSON par annonce, jamais réécrit) → `derive/` (CSV plats, recalculables à
volonté sans rappeler Airbnb).

**D6 — Correction géométrique.**
Le POC calcule son tampon de 250 m en degrés de latitude uniquement ; à 43,4° de
latitude c'est ~27 % trop étroit en longitude. La V2 projette en **Lambert-93
(EPSG:2154)** pour toute distance — ce qui sera de toute façon requis pour le
rapprochement au cadastre.

---

## 4. Ce que je propose de produire (V2)

Scripts dans `saas/backend/scripts/` (committés, conformes au dépôt) :

| Fichier | Rôle |
|---|---|
| `airbnb_lcd_communes.py` | les 14 communes, codes INSEE, contours officiels |
| `airbnb_lcd_collecte.py` | **passage 1** — tuilage récursif adaptatif, dédup, journal des zones saturées |
| `airbnb_lcd_details.py` | **passage 2** — `get_details` avec cache, reprise, backoff, extraction `host_id` |
| `airbnb_lcd_equipements.py` | lexique de motifs → colonnes booléennes |
| `airbnb_lcd_export.py` | CSV + statistiques par commune + rapport de collecte |

Sorties dans `sig_agglo_data\airbnb\` (donc **hors git**, comme le reste des données
personnelles) :

- `raw/<room_id>.json` — fiche brute intégrale, `amenities` compris
- `annonces.csv` — une ligne par annonce
- `equipements.csv` — une ligne par couple (annonce, équipement), forme longue
- `hotes.csv` — une ligne par `host_id`, avec le nombre d'annonces sur le territoire
- `rapport-collecte.md` — tuiles, saturations résiduelles, taux de couverture, taux
  de remplissage de chaque colonne

Colonnes booléennes demandées : `clim`, `piscine`, `jacuzzi`, `chauffage`, `parking`,
`borne_recharge`, `wifi`, `ascenseur`, `lave_linge`, `seche_linge`. Chacune en
**trois états** — `True` / `False` (explicitement « non inclus ») / vide (non
renseigné) — parce qu'écraser « absent » et « inconnu » fausserait tout ciblage.

**Sur le rapprochement cadastral** : la V2 s'arrête à la *préparation* (coordonnées
projetées, normalisation d'adresse selon la règle éprouvée du §3 des décisions SIG,
clés candidates). Le rapprochement lui-même fera l'objet d'une note séparée, parce
que M3 en change les fondations — voir Q1 et Q2.

---

## 5. Questions à trancher

**Q1 — Le NER est mort côté Airbnb (M3). Quelle source de substitution ?**
Sans NER, il ne reste que la coordonnée floutée, et je maintiens ce que j'ai écrit
avant la sonde : **le flou Airbnb dépasse la taille d'un îlot sétois**. Les options,
par valeur décroissante :
 a. le fichier des **déclarations de meublés / taxe de séjour** de l'agglo (adresse
    exacte → rattachement au logement) — as-tu le droit de l'utiliser ?
 b. **DATAtourisme / Office de tourisme** (adresses exactes, mais seulement les
    meublés déclarés/classés, minorité du parc) ;
 c. coordonnées seules → **rattachement à la parcelle au mieux**, souvent à l'îlot.
Sans (a) ou (b), le livrable honnête est une **densité par secteur + un score de
propension**, pas une identification de biens. Il faut le décider maintenant, pas
après la collecte.

**Q2 — Quelle maille cible assumes-tu ?** Le piège n°1 déjà payé (710 logements
vacants étalés sur 30 470 lignes) dit qu'il ne faut jamais poser une donnée
d'immeuble sur un lot. Confirmes-tu que toute donnée Airbnb non rattachable à un
logement précis sera nommée `LCD — … sur la parcelle` et jamais attribuée à un local ?

**Q3 — Budget de collecte.** Le passage 2 est le poste lourd : une fiche par annonce.
Si l'agglo porte 6 000 à 10 000 annonces, à quelques secondes chacune, c'est
**8 à 16 heures** de collecte. Je propose : cache + exécution par lots + reprise, en
commençant par **Sète seule** pour mesurer le temps réel et le taux de couverture
avant de lancer les 13 autres. D'accord ?

**Q4 — Le calendrier (200 ko/annonce, ~1–2 Go au total) : on le garde ?**
Il donne le taux d'occupation et les jours bloqués — le cœur de l'indicateur métier
de ton concept. Je propose de **stocker un résumé** (jours dispo/bloqués par mois,
prix médian) et de ne garder le brut que sur un échantillon. Ou bien tout garder si
l'espace disque ne te gêne pas.

**Q5 — Cadre juridique et RGPD.** La note de concept pose déjà la question (§ Points
juridiques, n°1) et elle n'est pas tranchée. Ici on va constituer un fichier qui
croise des annonces publiques avec des **noms et adresses de propriétaires** issus de
MAJIC. Je code l'outil d'analyse territoriale sans difficulté ; mais avant tout usage
de **prospection commerciale**, la question de la base légale et de la finalité
initiale des données MAJIC doit être tranchée par toi, pas par moi. Veux-tu que la
note de rapprochement comporte une section « usages autorisés / interdits » explicite ?

**Q6 — Fréquence.** Collecte unique (photographie du parc) ou récurrente
(suivi d'évolution, entrées/sorties d'annonces) ? Ça change le schéma de stockage :
si récurrent, il faut horodater chaque observation dès maintenant plutôt que de
migrer plus tard.

---

## 6. Réponses reçues et résultats de la V2 (2026-09-08, après validation)

**Q1 → non.** Pas d'accès au fichier des déclarations de meublés ni à celui de la
taxe de séjour. Conséquence assumée et inscrite dans le livrable : **aucune annonce
ne sera rattachée à un logement nommé**. La maille atteignable est la parcelle ou le
secteur. Le rapprochement cadastral fera l'objet d'une note séparée.

**Q3 → ok.** Démarrage sur Sète seule.

Les autres questions n'ont pas été tranchées ; défauts appliqués, réversibles :
Q2 → règle stricte maintenue ; Q4 → résumé du calendrier pour toutes les annonces,
brut conservé sur un échantillon (option `--garder-calendriers` pour tout garder) ;
Q6 → chaque ligne porte un horodatage `collecte_utc` dès maintenant, pour ne pas
avoir à migrer si le suivi devient récurrent.

### Résultats mesurés sur Sète

| Mesure | Valeur |
|---|---|
| Annonces collectées | **2 501** |
| Requêtes de recherche | 236 tuiles, dont 202 interrogées, **0 échec** |
| Zones encore saturées | **1** (contre 17 au plancher 197 m) |
| `host_id` récupéré | **12/12** sur le premier lot de fiches |
| Passage 2 (fiches détaillées) | **2 499 / 2 501**, 2 échecs, en **2 h 44** |
| Hôtes distincts | **1 754**, dont **199 multi-annonces** |
| `host_id` manquant | 259 / 2 499 (**10,4 %** — annonces sans avis) |
| Volumétrie | 0,29 Go de cache, 8,3 Mo d'équipements, 0,86 Mo d'annonces |

Têtes de liste des hôtes multi-annonces : ConciLogis (58), Guilhem (33),
Sebastien (22), Poplidays (21), **Thau Conciergerie (16)** — cette dernière est
précisément l'un des concurrents identifiés dans la note de concept. La colonne
`host_id` fait donc ce qu'on lui demandait : elle distingue le particulier du
professionnel.

### Faux positifs du lexique, relevés et corrigés

Vérification sur les 93 490 lignes d'équipements réelles (et non sur un
échantillon) :

- « Vue sur la piscine » (58 occurrences) était compté comme une piscine —
  corrigé, `piscine` passe de 362 à **338** ;
- « Chauffage : système split sans évacuation » (135) tombait dans `clim` —
  sorti vers une colonne `split_reversible` dédiée, pour que le doute reste
  visible plutôt que fondu dans le total.

Le contrôle inverse est bon : les 968 « stationnement dans la rue » sont bien
exclus de `parking` et rangés dans `parking_rue`. Autotest du lexique : 17/17.

Le gain sur le POC v1 est direct : sa grille fixe 5×5 plafonnait à 1 000 annonces
avant dédup. Le tuilage adaptatif en trouve **2 501** — et sait dire où il reste
incertain.

L'affinage progressif est validé : relancer avec `--cote-min 85` a réinjecté les
zones saturées et rapporté **+276 annonces pour 68 requêtes**.

### Anomalie relevée au passage

`prix_nuit_eur` est **inexploitable tel quel** : 972 € et 1,00 € la nuit relevés sur
des T2 dès le premier lot de 12. Airbnb renvoie selon les cas une nuitée, un total de
séjour ou un prix promotionnel, sans le signaler. Inscrit dans les limites du rapport
de collecte. Toute analyse de revenus devra requalifier ce champ.

---

## 7. DATAtourisme Occitanie : audit de la ressource (2026-09-08)

Piste soumise : le CSV `datatourisme-reg-occ.csv` (ressource data.gouv
`0c463ef6-c00a-48e2-b50a-d17cfe998b84`), présenté comme permettant « de
récupérer tout ce qui est numéro RNE ». Téléchargé et audité intégralement.

**La ressource est réelle** : 42,9 Mo, **53 281 lignes**, 15 colonnes, licence
ouverte. L'identifiant est le bon. Ce n'est pas l'API Meublés mais le flux
DATAtourisme, alimenté par les offices de tourisme.

**Elle ne contient aucun numéro d'enregistrement.** Mesuré sur les 53 281
lignes :

- chaînes au format d'un NER héraultais (`34xxx` + 8 caractères) : **0** ;
- lignes mentionnant « enregistrement », « NER » ou « RNE » où que ce soit :
  **3**, sur toute la région.

Les 15 colonnes sont : nom, catégories, latitude, longitude, adresse postale,
code postal + commune, périodes, mesures Covid, créateur, SIT diffuseur, date de
mise à jour, contacts, classements, description, URI du POI. Le classement porte
les étoiles, pas le numéro de déclaration.

### Ce que la ressource apporte réellement

| Mesure | Valeur |
|---|---|
| POI sur les 14 communes | 2 137 |
| Hébergements meublés / locatifs | **918** |
| Avec adresse postale | 1 014 / 1 017 |
| Avec coordonnées | 1 017 / 1 017 |

Répartition très déséquilibrée : **Balaruc-les-Bains 594**, Sète 134,
Frontignan 58, Marseillan 39. DATAtourisme reflète l'activité des offices de
tourisme, pas le parc réel — Balaruc (station thermale) déclare beaucoup, Sète
presque pas.

### Pourquoi ça ne rapproche pas Airbnb

À Sète : **134 hébergements DATAtourisme contre 2 499 annonces Airbnb**, soit
5 % du parc. Et le rapprochement par distance ne discrimine pas :

| Rayon | Hébergements ayant un voisin Airbnb | Candidats dans le rayon (médiane) |
|---|---:|---:|
| 25 m | 69 % | 1 (moyenne 2,6) |
| 50 m | 90 % | 5 |
| 100 m | 100 % | **18** |
| 200 m | 100 % | 65 |

Le « 100 % à 100 m » n'est pas un succès : c'est la densité du parc sétois. Avec
18 candidats dans le rayon, la proximité ne prouve rien. Un appariement
exigerait un critère supplémentaire (nom, type, capacité) et resterait probabiliste.

### Contre-épreuve sur Balaruc-les-Bains

Hypothèse formulée puis **réfutée** : on supposait que DATAtourisme et Airbnb
décrivaient des parcs disjoints (meublés de cure loués en direct d'un côté,
plateformes de l'autre). Collecte Airbnb lancée sur Balaruc pour vérifier :

- **749 annonces Airbnb** à Balaruc-les-Bains, pour 594 entrées DATAtourisme ;
- rapporté à la population, **10,5 % du nombre d'habitants contre 5,5 % à Sète** :
  Balaruc est la commune la plus intensive en location courte durée, pas une
  commune hors plateformes.

Les parcs ne sont donc pas disjoints. L'écart Sète/Balaruc dans DATAtourisme
(134 contre 594) mesure la pratique des offices de tourisme, rien d'autre.

Et l'appariement géographique y est **encore moins discriminant** qu'à Sète :

| Rayon | Hébergements avec ≥1 voisin | Candidats (médiane) | Avec un candidat **unique** |
|---|---:|---:|---:|
| 25 m | 76,8 % | 2 | **17,5 %** |
| 50 m | 91,2 % | 9 | 4,9 % |
| 100 m | 96,1 % | **29** | 2,5 % |

À 25 m, seuls 17,5 % des hébergements ont un candidat unique — et même ceux-là
ne sont pas sûrs, puisque le flou des coordonnées Airbnb dépasse ce rayon : le
bon logement peut être hors du cercle et un voisin dedans.

### Décision

**L'appariement géographique DATAtourisme ↔ Airbnb est abandonné.** Mesuré sur
deux communes aux profils opposés, il ne discrimine dans aucune. Les deux
sources seront exploitées séparément :

- **Airbnb** → volume, équipements, hôtes multi-annonces, densité par secteur ;
- **DATAtourisme** → adresses exactes, rattachement au cadastre par adresse
  normalisée (et non par géométrie), donc accès au propriétaire.

DATAtourisme **n'est pas la clé du rapprochement Airbnb**. En revanche ses 918
hébergements portent une **adresse postale exacte**, donc rattachable au
cadastre par adresse (avec la règle de normalisation éprouvée). C'est un
livrable complémentaire à part entière — surtout sur Balaruc-les-Bains — et non
un substitut au NER.

Le piège n°4 s'est d'ailleurs vérifié à nouveau : filtrer sur le seul nom de
commune capturait Mireval-Lauragais (Aude), Mézerville (Aude) et un Marseillan
du Gers. Le filtre retenu croise **code postal ET nom**.

---

## 8. Ce que je ne ferai pas

- Aucune tentative de contournement d'un blocage, d'une authentification ou d'un
  CAPTCHA Airbnb (le POC s'en abstenait déjà, la V2 aussi).
- Aucun `git add` dans `sig_agglo_data/`.
- Aucune annonce de taux d'exhaustivité non mesuré.
- Aucun rattachement d'une donnée d'immeuble à un lot.
