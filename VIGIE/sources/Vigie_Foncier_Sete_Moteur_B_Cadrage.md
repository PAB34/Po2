# Vigie Foncier Sète — Moteur B
## Détection automatique de réserves foncières et de divisions parcellaires potentielles

**Version :** cadrage fonctionnel V0.1  
**Territoire pilote :** commune de Sète (34301)  
**Objectif :** détecter automatiquement, à partir de données publiques gratuites, les parcelles bâties présentant un potentiel de division foncière ou de densification douce, avant toute mise en vente.

---

## 1. Principe général

Le moteur ne cherche pas d'abord les biens en vente. Il cherche les **propriétés qui possèdent une valeur foncière non exploitée** :

- maison implantée à l'avant avec grand jardin arrière ;
- maison décalée sur un côté avec réserve latérale ;
- grande parcelle très peu bâtie ;
- parcelle permettant potentiellement un accès indépendant ;
- unité foncière dont l'emprise construite actuelle est très inférieure à l'emprise admise par le PLU.

Le fonctionnement cible est :

```text
PLU / zonage
    ↓
Sélection des zones intéressantes
    ↓
Cadastre : parcelles + bâtiments
    ↓
Calcul de la réserve foncière / emprise résiduelle
    ↓
Analyse géométrique simple
    ↓
Filtrage risques / protections / contraintes
    ↓
Score de potentiel
    ↓
Carte des meilleures parcelles
    ↓
Vérification humaine
    ↓
Recherche du propriétaire uniquement sur les meilleurs dossiers
```

Le moteur est donc un **outil de présélection**. Il ne doit jamais présenter une parcelle comme juridiquement constructible de manière certaine.

---

# 2. Étape indispensable : lire et structurer le règlement du PLU

Avant toute analyse géographique, il faut transformer le règlement du PLU de Sète en une **matrice de règles exploitable par le programme**.

Le document opposable actuellement publié sur le Géoportail de l'urbanisme est le **PLU de Sète daté du 15 décembre 2025**, version 14, publié le 1er janvier 2026.

Le moteur doit extraire, pour chaque zone et sous-zone utile :

| Donnée PLU | Utilité pour le moteur |
|---|---|
| Destination habitation autorisée | Élimination immédiate des zones incompatibles |
| Emprise au sol maximale | Calcul de l'emprise théorique encore disponible |
| Implantation par rapport à la voie | Définition approximative de l'enveloppe constructible |
| Implantation par rapport aux limites séparatives | Vérification de la largeur réellement exploitable |
| Distance entre bâtiments | Vérification d'une seconde construction sur la même unité foncière |
| Hauteur maximale | Information secondaire pour la V0, importante ensuite |
| Stationnement | Détection des parcelles qui risquent d'être bloquées |
| Espaces libres / végétalisation | Réduction de la capacité théorique |
| Accès et voirie | Critère majeur pour une division foncière |
| PPRI | Filtre / pénalité forte |
| SPR | Alerte réglementaire |
| Espaces verts protégés | Filtre fort |
| Servitudes / emplacements réservés | Alerte ou exclusion |

**Important :** le simple pourcentage d'emprise ne suffit pas. Le vrai indicateur recherché sera la **réserve d'emprise réellement exploitable**.

---

# 3. Premier pré-classement des zones du PLU de Sète

Ce classement est destiné au développement du moteur. Il ne constitue pas une analyse juridique définitive des possibilités de construire.

## 3.1 Priorité n°1 — zones UD

Le règlement décrit la zone **UD comme une zone d'habitations à faible densité composée essentiellement d'habitat individuel**. C'est donc le terrain de recherche naturel pour une stratégie « maison + jardin / réserve foncière ».

Emprises maximales actuellement identifiées :

| Secteur | Emprise maximale | Lecture pour Vigie Foncier |
|---|---:|---|
| UD1 | 11 % | Grandes parcelles possibles, mais constructibilité très contrainte ; à conserver si parcelle importante |
| UD1a | 20 % | Potentiel sur grandes propriétés |
| UD2 | 20 % | **Très intéressant à scanner** : pavillonnaire de moyenne densité |
| UD3 | 30 % | **Priorité élevée** : pavillonnaire de forte densité |
| UD4 | 50 % | **Priorité élevée** si la typologie parcellaire reste individuelle |
| UD1v | 8 % | Faible priorité / fortes protections |
| UD2v / UD3v / UD4v | 10 % | Faible priorité / espaces verts protégés |

### Règle de sélection proposée

Ne pas éliminer UD1 parce que l'emprise n'est que de 11 %. Une propriété de 1 500 m² peut théoriquement autoriser davantage de bâti résiduel qu'une parcelle de 350 m² située dans une zone à 30 %.

Le moteur calculera donc :

```text
Emprise_max_théorique = Surface_parcelle × Taux_emprise_PLU

Réserve_emprise_brute = Emprise_max_théorique - Emprise_bâtie_existante
```

Exemple :

```text
Parcelle UD2 : 900 m²
Emprise autorisée : 20 % = 180 m²
Maison existante : 95 m²
Réserve brute : 85 m²
```

Cette parcelle mérite une analyse géométrique même si 20 % paraît faible.

---

## 3.2 Priorité n°2 — certaines zones UC

La zone UC est à dominante habitat / équipement. Le règlement distingue notamment des secteurs de groupes d'habitations, petits collectifs et secteurs résidentiels.

| Secteur | Emprise maximale | Première lecture |
|---|---:|---|
| UC1 | 50 % | Cas particulier IFREMER — non prioritaire |
| UC2 | 45 % | Principalement équipements / loisirs — secondaire |
| UC3 | 85 % | Potentiel de densification mais tissu déjà dense |
| UC4a / UC4b / UC4c | 50 % | **À analyser**, selon morphologie réelle des parcelles |
| UC4d / UC4e | 75 % | Densité élevée / opérations plus complexes |
| secteurs UC*v | 10 % | Faible priorité / espaces verts protégés |

Pour notre spécialité, **UC4a / UC4b et certaines parcelles UC3/UC4c** peuvent être intéressantes, mais elles passent après les zones UD car le tissu y est généralement plus dense.

---

## 3.3 Priorité n°3 — zones 3UB

Le PLU décrit désormais explicitement la zone **3UB comme une zone à fort potentiel de mutation et de densification**.

Elle comprend notamment les corridors des boulevards de Verdun et Camille-Blanc.

Emprises principales :

- 3UB1 / 3UB2 / 3UB3 : 75 % ;
- 3UB4 / 3UB6 / 3UB8 / 3UB9 : 50 % ;
- 3UB7 : règle spécifique ;
- secteurs « v » : droits fortement minorés.

Ces secteurs sont intéressants mais correspondent davantage à des **opérations de mutation urbaine, restructuration ou promotion** qu'à la simple division d'un jardin.

Ils seront donc conservés dans Vigie Foncier, mais dans une catégorie distincte :

> **Densification / opération promoteur**

et non :

> **Division pavillonnaire simple**.

---

## 3.4 Zones à faible priorité pour la V0

### UA et 1UB

Emprises parfois élevées (jusqu'à 75–85 %), mais tissu très dense, maisons mitoyennes, centre-ville et forte présence du SPR.

=> Peu adaptées au moteur « grand jardin divisible ».

### 2UB

Emprise non réglementée dans certaines dispositions, mais secteur urbain spécifique / opérations d'ensemble.

=> Hors cible V0.

### UE / UP / AU / A / N

Zones économiques, portuaires, à urbaniser sous conditions, agricoles ou naturelles.

=> Exclues par défaut de la recherche « maison + réserve foncière ».

---

# 4. La bonne métrique : la réserve foncière exploitable

Il ne faut pas chercher simplement :

> `parcelle > 500 m²`

ni simplement :

> `emprise PLU élevée`.

Le moteur doit calculer plusieurs niveaux.

## Niveau 1 — réserve brute de terrain

```text
Surface_libre = Surface_parcelle - Emprise_bâtiments
```

## Niveau 2 — réserve réglementaire d'emprise

```text
Réserve_emprise = (Surface_parcelle × CES_max) - Emprise_existante
```

CES = coefficient / taux d'emprise au sol utilisé ici comme raccourci fonctionnel.

## Niveau 3 — zone libre réellement continue

Le programme soustrait de la parcelle :

- bâtiments existants ;
- marges simplifiées autour des bâtiments ;
- retraits simplifiés aux limites ;
- zones protégées connues.

Puis il mesure le **plus grand polygone libre continu**.

C'est ce polygone qui nous intéresse réellement.

---

# 5. Analyse géographique simple à développer

La V0 ne cherchera pas à reproduire un logiciel d'instruction des permis.

Elle doit reconnaître quatre configurations simples.

## Type A — réserve latérale

```text
RUE
────────────────────
│ MAISON │ TERRAIN │
│        │  LIBRE  │
│        │ FUTUR   │
│        │  LOT    │
────────────────────
```

Critères :

- espace libre latéral significatif ;
- contact possible avec la voie ;
- largeur minimale configurable.

## Type B — fond de parcelle

```text
RUE
────────────────────
│ MAISON             │
│                    │
│ passage potentiel  │
│ ↓                  │
│                    │
│   GRAND JARDIN     │
│   FUTUR LOT ?      │
────────────────────
```

Critères :

- maison proche de la rue ;
- espace libre important derrière ;
- corridor latéral potentiel jusqu'au fond de parcelle.

## Type C — parcelle très sous-bâtie

```text
┌───────────────────────┐
│   maison              │
│   █████               │
│                       │
│      grande zone      │
│         libre         │
│                       │
└───────────────────────┘
```

Critère principal :

```text
Emprise_existante / Emprise_max_PLU faible
```

## Type D — plusieurs bâtiments / découpage complexe

Le moteur détecte la situation mais ne cherche pas à résoudre automatiquement la division.

=> classement : **À étudier manuellement**.

---

# 6. Critères simples de présélection V0

Tous les seuils doivent être **configurables**.

Valeurs de départ proposées uniquement pour tester l'algorithme :

```yaml
surface_parcelle_min: 350 m²
surface_libre_min: 180 m²
reserve_emprise_min: 60 m²
plus_grande_zone_libre_min: 120 m²
largeur_acces_cible: 3.0 m
```

Ces seuils ne représentent pas des règles légales. Ils servent uniquement à éliminer les parcelles manifestement peu intéressantes.

---

# 7. Score de potentiel foncier V0

Score sur 100 :

| Critère | Points |
|---|---:|
| Zone PLU adaptée à la stratégie | 20 |
| Réserve d'emprise réglementaire | 20 |
| Grande zone libre continue | 20 |
| Accès indépendant potentiel | 15 |
| Position favorable du bâti existant | 10 |
| Surface totale de la parcelle | 5 |
| Géométrie simple / rectangulaire | 5 |
| Absence de contrainte majeure détectée | 5 |

Puis application de pénalités :

| Contrainte | Pénalité indicative |
|---|---:|
| Sous-secteur espace vert protégé « v » | -30 à exclusion |
| PPRI fortement contraignant | -20 à exclusion |
| SPR | -10 / alerte |
| bâtiment ou élément patrimonial protégé | -20 |
| accès manifestement impossible | exclusion division simple |
| terrain extrêmement pentu | -10 à -30 |

### Classes finales

```text
80–100 : PRIORITÉ A — enquête immédiate
65–79  : PRIORITÉ B — contrôle visuel
50–64  : PRIORITÉ C — potentiel possible
< 50   : non prioritaire
```

---

# 8. Données gratuites à utiliser

## 8.1 PLU / zonage

**Géoportail de l'Urbanisme / Géoplateforme**

À récupérer :

- polygones de zonage ;
- prescriptions ;
- servitudes disponibles ;
- règlement écrit ;
- SPR ;
- PPRI / annexes utiles.

## 8.2 Parcelles cadastrales

**Cadastre Etalab / Géoplateforme**

À récupérer :

- identifiant cadastral ;
- polygone de parcelle ;
- surface géométrique.

## 8.3 Bâtiments

Deux sources possibles :

1. bâtiments cadastraux ;
2. BD TOPO IGN pour enrichissement ultérieur.

Pour la V0, les bâtiments cadastraux suffisent.

## 8.4 Orthophotographie

Utilisation uniquement pour la **validation visuelle humaine** des meilleures parcelles.

Pas besoin d'IA de reconnaissance d'image en V0.

---

# 9. Architecture technique volontairement simple

```text
Python
├── GeoPandas
├── Shapely
├── Pandas
├── SQLite / GeoPackage
└── Streamlit + Folium/Leaflet
```

### Base locale

L'objectif est de télécharger les données de Sète puis de travailler principalement en local sur le VPS.

Cela évite :

- des milliers d'appels API ;
- les limitations de débit ;
- la dépendance permanente à des services externes.

---

# 10. Pipeline informatique proposé

## Étape 1 — téléchargement

```text
cadastre/parcelles.geojson
cadastre/batiments.geojson
plu/zonage.geojson
plu/prescriptions.geojson
```

## Étape 2 — jointure parcelle / PLU

Pour chaque parcelle :

```text
id_parcelle
surface
zone_plu
sous_zone
```

## Étape 3 — calcul du bâti

Intersection bâtiments ↔ parcelle :

```text
surface_emprise_batie
nombre_batiments
ratio_bati
```

## Étape 4 — application de la matrice PLU

Exemple :

```python
REGLES = {
    "UD1": {"emprise": 0.11, "priorite": 2},
    "UD2": {"emprise": 0.20, "priorite": 1},
    "UD3": {"emprise": 0.30, "priorite": 1},
    "UD4": {"emprise": 0.50, "priorite": 1},
}
```

La table définitive sera créée après lecture complète des articles utiles du PLU.

## Étape 5 — calcul des réserves

```text
surface_libre
emprise_max_PLU
reserve_emprise
ratio_utilisation_emprise
```

## Étape 6 — géométrie simple

Calcul :

- centroïde du bâtiment principal ;
- distance à la rue / limite avant ;
- surface libre avant / arrière / côtés ;
- plus grand polygone libre ;
- corridor potentiel jusqu'à la voirie.

## Étape 7 — score

Production :

```text
score_foncier
classe_A_B_C
motif_selection
```

## Étape 8 — carte interactive

Chaque parcelle est affichée avec une couleur suivant son score.

Au clic :

```text
Parcelle : XX 0123
Zone : UD3
Surface : 742 m²
Bâti : 104 m²
Emprise maximale PLU : 222 m²
Réserve théorique : 118 m²
Terrain libre : 638 m²
Grande zone libre détectée : 286 m²
Accès latéral potentiel : OUI
Configuration : FOND DE PARCELLE
Score : 84 / 100
```

---

# 11. Interface V0

L'interface doit rester volontairement très fonctionnelle.

## Écran principal

Carte de Sète avec :

```text
[ ] afficher toutes les parcelles
[x] potentiel > 65
[x] zones UD
[ ] zones UC
[ ] zones 3UB
```

Filtres :

```text
Surface parcelle > [500] m²
Réserve emprise > [80] m²
Surface libre > [250] m²
Score > [70]
```

## Fiche parcelle

- référence cadastrale ;
- zone PLU ;
- surface parcelle ;
- emprise existante ;
- emprise maximale théorique ;
- réserve d'emprise ;
- surface libre ;
- configuration détectée ;
- score ;
- contraintes détectées ;
- vue orthophoto / carte.

Boutons :

```text
[ À étudier ]
[ Rejetée ]
[ Recherche propriétaire ]
[ Ajouter une note ]
```

---

# 12. Ce que la V0 ne doit PAS chercher à faire

Pour garder un outil réellement développable et fonctionnel :

- pas de simulation automatique de permis de construire ;
- pas de calcul architectural complet ;
- pas d'IA de reconnaissance d'images ;
- pas de calcul automatique de réseaux EU/EP ;
- pas d'identification automatique massive des propriétaires ;
- pas de garantie de constructibilité ;
- pas de génération automatique d'un plan de division définitif.

La V0 doit répondre à une seule question :

> **Quelles sont les 50 à 200 parcelles de Sète qui méritent réellement d'être regardées par un marchand de biens spécialisé en division foncière ?**

---

# 13. Validation du moteur avant lancement sur toute la commune

Ne pas lancer directement le score comme vérité sur tout Sète.

Créer un jeu test d'environ :

- 20 parcelles manifestement divisibles ;
- 20 parcelles manifestement non divisibles ;
- 10 cas ambigus.

Puis comparer :

```text
résultat humain ↔ résultat algorithme
```

On ajuste ensuite les seuils.

Objectif réaliste :

> faire remonter correctement la majorité des bonnes parcelles, même si le moteur génère encore quelques faux positifs.

Un faux positif coûte quelques minutes de vérification.

Un faux négatif peut faire manquer une opération.

Le moteur devra donc privilégier **la sensibilité** plutôt qu'une sélection trop restrictive.

---

# 14. Ordre de développement recommandé

## Phase 1 — matrice PLU

Lire complètement les articles utiles de :

1. UD ;
2. UC ;
3. 3UB ;
4. éventuellement UA / 1UB pour cas particuliers.

Créer :

```text
config/plu_sete.yaml
```

avec les règles essentielles.

## Phase 2 — preuve de concept géographique

Tester uniquement les zones UD.

Objectif : afficher toutes les parcelles UD et calculer :

```text
surface parcelle
surface bâtie
surface libre
emprise résiduelle
score simple
```

## Phase 3 — reconnaissance des configurations

Ajouter :

- jardin arrière ;
- réserve latérale ;
- accès potentiel ;
- plus grand polygone libre.

## Phase 4 — contraintes

Ajouter :

- PPRI ;
- SPR ;
- espaces verts protégés ;
- servitudes principales.

## Phase 5 — interface

Carte + filtres + fiche parcelle + statut de prospection.

## Phase 6 — extension

Ajouter UC puis 3UB.

---

# 15. Recommandation stratégique

Pour la première version, **ne pas essayer d'analyser tout le PLU avec le même niveau de précision**.

Le meilleur MVP est :

> **zones UD uniquement → calcul de réserve foncière → reconnaissance jardin arrière / réserve latérale → score → carte.**

Pourquoi :

- typologie majoritairement pavillonnaire ;
- correspond exactement à la stratégie recherchée ;
- règles d'emprise lisibles ;
- géométrie plus facile à analyser ;
- validation humaine rapide sur orthophoto.

Une fois que ce moteur trouve effectivement de bonnes parcelles en UD, on ajoute UC puis les secteurs 3UB à potentiel de mutation.

---

# 16. Résultat final recherché

Exemple de sortie :

```text
TOP OPPORTUNITÉS FONCIÈRES — SÈTE

1. Parcelle XX 0001 — UD3 — Score 91
   812 m² / 108 m² bâtis
   Réserve d'emprise : 136 m²
   Jardin arrière continu : 325 m²
   Passage latéral détecté : ~3,6 m
   → PRIORITÉ A

2. Parcelle XX 0002 — UD2 — Score 86
   1 040 m² / 112 m² bâtis
   Réserve d'emprise : 96 m²
   Réserve latérale importante
   → PRIORITÉ A

3. Parcelle XX 0003 — UD4 — Score 79
   510 m² / 130 m² bâtis
   Réserve d'emprise : 125 m²
   Géométrie favorable mais accès à vérifier
   → PRIORITÉ B
```

L'utilisateur ne consulte ensuite manuellement que ces dossiers.

---

# 17. Sources de référence

- Géoportail de l'Urbanisme — PLU de Sète, document `34301_PLU_20251215`, version en vigueur au 01/01/2026 :  
  https://www.geoportail-urbanisme.gouv.fr/document/by-id/f612ef0bbbd56e033bc88e5f79ab08e5

- Règlement écrit du PLU de Sète — fichier `34301_reglement_20251215.pdf` :  
  https://data.geopf.fr/annexes/gpu/documents/DU_34301/f612ef0bbbd56e033bc88e5f79ab08e5/34301_reglement_20251215.pdf

- Géoportail de l'Urbanisme — consultation zonage, prescriptions et servitudes :  
  https://www.geoportail-urbanisme.gouv.fr/

- Cadastre Etalab :  
  https://cadastre.data.gouv.fr/

---

## Conclusion

Le projet est techniquement réaliste sans créer un moteur d'urbanisme complexe.

La valeur du produit vient du croisement de trois informations simples :

```text
DROIT À BÂTIR THÉORIQUE
        +
GÉOMÉTRIE DE LA PARCELLE
        +
POSITION DU BÂTI EXISTANT
        =
RÉSERVE FONCIÈRE POTENTIELLE
```

Le PLU sert d'abord à **réduire le territoire de recherche**. La géométrie sert ensuite à faire ressortir les parcelles sous-exploitées. La vérification humaine intervient uniquement sur les meilleurs résultats.

C'est volontairement un moteur de **détection d'opportunités**, et non un logiciel de délivrance de permis.
