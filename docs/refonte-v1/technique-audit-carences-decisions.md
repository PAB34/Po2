# Audit des carences d'inventaire CVC — décisions

> Écrit **avant** de coder (règle « fil du dev »). Date : 2026-08-17.
> Objectif : faire de l'inventaire CVC un **levier contractuel** — mesurer ce que le titulaire
> ne livre pas, et produire une demande de complétude exploitable.

## 1. Existant vérifié

- Page `/refonte-v1/technique` livrée (PR #93) : KPI, pyramide des âges, criticité, complétude
  globale, tableaux bâtiments/familles.
- Écrans d'acquisition legacy : `/buildings/cvc-import` (722 l.), `/buildings/cvc-import/batiments`,
  `/buildings/cvc-fluides`. Fonctionnels, non réécrits.
- Parseurs : `import_cvc_from_excel` traite deux formats (DALKIA / SPIE) détectés automatiquement.

## 2. Le constat qui structure la fonctionnalité

Les carences sont de **deux natures différentes**, et les confondre décrédibiliserait la demande
au titulaire. Le code des parseurs le montre sans ambiguïté (champs codés en dur à `None`) :

| Nature | Signification | Demande correspondante |
|---|---|---|
| **A — Champ non livré par le format** | La colonne n'existe pas dans l'export du prestataire | « Faire évoluer votre export pour inclure ce champ » |
| **B — Champ livré mais incomplet** | La colonne existe, N équipements sur M sont vides | « Compléter ces N équipements » |

Mesuré en production (lots courants, 1 422 équipements) :

| | DALKIA (1 133) | SPIE (289) |
|---|---|---|
| **Non livré (A)** | type d'équipement, n° de série, puissance, puissances frigo/calo, capacité, durée de vie | statut, état de santé, bâtiment |
| **Incomplet (B)** | date MES 53 %, réf. SYPEMI 21 %, modèle 41 %, marque 27 % | rattachement 78 %, puissance 86 %, local 97 %, niveau 93 %, réf. 69 %, date MES 63 %, n° série 58 %, modèle 32 %, marque 24 % |

### Nuance d'honnêteté : toutes les carences ne sont pas imputables au titulaire

Le **rattachement au bâtiment** (`building_id`) n'est pas une donnée fournie par le prestataire :
c'est le **résultat de notre rapprochement** entre son libellé de site et notre patrimoine. Il est
donc affiché **à part**, en « à traiter en interne », et non dans la demande adressée au titulaire.
Lui demander de remplir un identifiant de notre base n'aurait aucun sens et affaiblirait le reste
de la demande.

## 3. Décisions (2026-08-17)

1. **Import embarqué** : l'écran d'import existant est ré-hébergé dans la page technique (patron
   « embed » PR #42), **sans réécriture** — un flux qui fonctionne ne se refait pas pour l'esthétique.
2. **Livrable = export Excel par prestataire** : liste des équipements incomplets, colonnes
   d'identification remplies (pour qu'il retrouve l'équipement) et colonnes manquantes vides
   (pour qu'il les remplisse), réimportable ensuite. La boucle est fermée.
3. **Champs exigibles retenus** (les 4 groupes) :
   - **Identification technique** : marque, modèle, n° de série ;
   - **Date de mise en service** — levier n°1 (34,9 % du parc non calculable sans elle) ;
   - **Localisation précise** : niveau, local ;
   - **Caractéristiques énergétiques** : puissance, capacité.
4. **Distinction A/B affichée explicitement** : un champ non livré appelle une évolution de format,
   pas un remplissage ligne à ligne.
5. **Le rattachement patrimoine est exclu de la demande titulaire** (cf. §2).

## 4. Résultat mesuré en production (2026-08-17, livré PR #95)

### DALKIA — 1 133 équipements, **47,4 % renseigné**, 696 équipements incomplets

| Nature | Champs |
|---|---|
| **Non livrés par le format** | Capacité, N° de série, Puissance |
| **Livrés mais incomplets** | Date de mise en service **598 (52,8 %)** · Modèle 462 (40,8 %) · Marque 310 (27,4 %) |

Niveau et Local sont renseignés à 100 % : la localisation n'est pas un sujet chez DALKIA.

### SPIE — 289 équipements, **31,1 % renseigné**, 289 équipements incomplets (la totalité)

| Nature | Champs |
|---|---|
| **Non livrés par le format** | *(aucun — SPIE livre toutes les colonnes attendues)* |
| **Livrés mais incomplets** | Capacité 285 (98,6 %) · Local 280 (96,9 %) · Niveau 268 (92,7 %) · Puissance 249 (86,2 %) · Date de MES 182 (63,0 %) · N° de série 169 (58,5 %) · Modèle 92 (31,8 %) · Marque 69 (23,9 %) |

### La lecture qui en découle

Les deux titulaires ont des **profils de carence opposés**, et donc des demandes différentes :

- **DALKIA remplit correctement ce qu'il livre, mais ne livre pas tout** → la demande porte
  d'abord sur une **évolution de son export** (3 colonnes à ajouter), puis sur les dates de MES.
- **SPIE livre toutes les colonnes mais ne les remplit pas** → la demande porte entièrement sur
  le **remplissage**, sans évolution de format à négocier.

**À traiter en interne** : 247 équipements sur 1 422 non rattachés au patrimoine (hors demande titulaire).

Exports générés : DALKIA 64 Ko, SPIE 20 Ko.

## 5. Questions ouvertes

- Faut-il **historiser** les demandes de complétude (date d'envoi, taux de retour) pour suivre
  l'engagement du titulaire dans le temps ? (Non traité dans cette itération.)
- Les seuils d'alerte par champ sont-ils contractuels (un taux de complétude minimal est-il exigé
  au marché) ou purement indicatifs ?
