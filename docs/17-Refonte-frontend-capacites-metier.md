# 17 - Refonte frontend par capacites metier

> Date : 2026-06-16.
> Objectif : cadrer la refonte totale du frontend sans repartir d'une simple liste de routes.
> Ce document transforme les capacites backend existantes en parcours utilisateur, en ecrans cibles et en ordre de chantier.

## 1. Nom du chantier

Le bon nom n'est pas "listing des routes" ni "refonte graphique".

Le chantier s'appelle :

```text
Refonte produit du frontend orientee capacites metier
```

Autres formulations correctes :

- refonte UX/UI par parcours metier ;
- cartographie des capacites backend vers des ecrans utilisateur ;
- rearchitecture frontend orientee usages ;
- reconception produit a partir des moteurs backend existants.

Le listing des routes reste utile, mais seulement comme une preuve technique. Il ne dit pas quoi afficher, pour qui, ni dans quel ordre l'utilisateur doit travailler.

## 2. Ce que l'on cherche vraiment

La question a poser n'est pas :

```text
Quelle page appelle quel endpoint ?
```

La bonne question est :

```text
Quel travail metier l'utilisateur doit-il accomplir, quelle decision doit-il prendre,
et quelles capacites backend rendent cette decision fiable ?
```

Exemple :

```text
Controler une facture ENGIE
= importer ou retrouver la facture
+ comprendre le perimetre fournisseur
+ comparer prix BPU / TURPE / quantites ENEDIS
+ isoler les ecarts
+ prendre une decision
+ produire une sortie finance exploitable
```

Ce parcours mobilise plusieurs endpoints et services, mais l'utilisateur ne doit pas les voir comme des briques techniques.

## 3. Regle de conception

Chaque fonctionnalite doit etre classee selon quatre niveaux.

| Niveau | Question | Exemple |
|---|---|---|
| Capacite backend | Que sait faire le systeme ? | analyser une facture, lire un BPU, calculer un ecart |
| Parcours metier | Pourquoi l'utilisateur s'en sert ? | controler une facture avant mandatement |
| Ecran cible | Ou l'utilisateur agit ? | Marches & contrats > Factures marche |
| Niveau d'exposition | Est-ce quotidien, expert, cache ? | quotidien pour controle, expert pour import BPU |

Regle durable :

```text
Toute operation que l'on doit faire en SQL, SSH ou script manuel est un trou d'UX.
```

## 4. Lecture de l'existant

Documents sources lus pour ce cadrage :

- [[09-Vision-produit-et-navigation-UX]]
- [[10-Audit-moteurs-et-experience-utilisateur-2026-06-15]]
- [[11-Analyse-backend-et-socle-refonte-UX]]
- [[12-Plan-plateforme-cible-et-tri-endpoints]]
- [[13-Matrice-routes-fonctionnalites-refonte-api]]
- [[14-Catalogue-fonctionnalites-commentees-et-reaffectation]]
- [[15-Validation-P0-factures-finance]]
- [[16-Audit-moteur-contractuel-BPU-Herault]]

Conclusion : le backend contient deja beaucoup de valeur. Le probleme principal n'est pas l'absence de fonctions, mais leur presentation en front. Les ecrans actuels exposent trop souvent des modules, des imports ou des routeurs, alors que la cible doit exposer des decisions metier.

## 5. Colonne vertebrale produit cible

La navigation cible doit rester lisible en six domaines.

| Domaine | Role produit | A ne pas faire |
|---|---|---|
| Tableau de bord | cockpit des urgences, files a traiter, indicateurs transverses | page d'accueil decorative |
| Patrimoine | base maitre sites, batiments, locaux, compteurs, rattachements | annuaire isole sans liens energie/contrats |
| Energie | consommations, distributeurs, prix, TURPE, preconisations | melanger donnees mesurees et factures marche |
| Marches & contrats | CPE DALKIA, SPIE, contrats, factures marche, atterrissages | cloner DALKIA pour tous les marches |
| Technique | inventaires CVC, equipements, F-Gaz, ESP, rapport technique | cacher le terrain dans Administration |
| Administration | imports experts, referentiels, connecteurs, diagnostics | y mettre les parcours quotidiens |

## 6. Carte des moteurs a re-exposer

| Moteur | Valeur utilisateur | Ecran cible | Niveau |
|---|---|---|---|
| Patrimoine site -> batiment -> local | savoir sur quoi porte une facture, une conso, un contrat ou un equipement | Patrimoine > Sites et batiments | quotidien |
| Rattachement compteurs PRM/PCE/eau | relier les donnees aux bons sites | Patrimoine > Rattachements | quotidien/P0 |
| ENEDIS | prouver les consommations electriques et la couverture des donnees | Energie > Donnees electricite | quotidien + expert collecte |
| GRDF | prouver les consommations gaz et alimenter les analyses P1/fourniture gaz | Energie > Donnees gaz | quotidien + expert collecte |
| BPU / TURPE | verifier les prix contractuels | Energie > Prix contractuels | expert, mais visible depuis controle facture |
| Factures fournisseurs et prestataires | controler, decider, exporter finance | Marches & contrats > Factures marche | quotidien/P0 |
| Preconisations puissance | ajuster contrats et economies | Energie > Optimisations | metier/P1 |
| CPE DALKIA | piloter P1/P2/P3, controles, cibles, finances | Marches & contrats > CPE DALKIA | quotidien/P0 |
| Referentiel DALKIA | transformer l'acte d'engagement en moteur de controle | CPE DALKIA > Referentiel + Administration > Imports | expert/P0 |
| P3/P6 travaux | controler devis, BPU, engagements | CPE DALKIA > Travaux | metier/P0 |
| CVC / equipements | exploiter l'inventaire technique terrain DALKIA/SPIE | Technique > Inventaire CVC | metier/P1 |
| F-Gaz / ESP | suivre obligations et risques techniques | Technique > Fluides et conformite | metier/P1 |
| Connecteur ENGIE API | potentiel connecteur direct, non prouve comme usage produit actif | Administration > Connecteurs | cache/veille |
| Pronostics | hors plateforme PatrimoineOp | hors produit | ne pas integrer |

## 7. Parcours metier prioritaires

### 7.1 Cockpit quotidien

L'utilisateur doit arriver sur une page qui lui dit quoi traiter maintenant.

Files a remonter :

| File | Domaine | Action attendue |
|---|---|---|
| Factures marche a controler | Marches & contrats | ouvrir le controle factures marche |
| Factures CPE DALKIA bloquees | Marches & contrats | ouvrir le controle CPE |
| Compteurs non rattaches | Patrimoine / Energie | rattacher PRM/PCE/eau |
| Sites marche non relies | Patrimoine / Marches | relier DALKIA/SPIE au patrimoine |
| Donnees distributeur incompletes | Energie | verifier ENEDIS/GRDF |
| Alertes techniques fluides | Technique | traiter F-Gaz/ESP |

### 7.2 Controle factures marche

Ecran cible : `Marches & contrats > Factures marche`.

Sous-ecrans utiles :

| Sous-ecran | Role |
|---|---|
| Etat | synthese imports, montants, ecarts, decisions |
| ENGIE | controle electricite batiments : BPU, TURPE, ENEDIS, decisions |
| EDF | controle eclairage public, CSV, regles propres |
| TotalEnergies / gaz | a preparer : PCE, GRDF, BPU gaz si disponible |
| DALKIA | CPE P1/P2/P3, controles specifiques, liaison finance |
| SPIE | maintenance P2/P3, a cadrer |
| Prix & references | acces expert BPU/TURPE utilise par le controle |
| Export finance | fiche de liaison et matrice comptable |

Ce parcours doit etre pense comme :

```text
importer -> controler -> comprendre -> decider -> exporter
```

L'ecran ne doit pas etre une liste brute de factures. Il doit expliquer ce qui est payable, contestable, incomplet ou a rattacher.

### 7.3 CPE DALKIA

Ecran cible : `Marches & contrats > CPE DALKIA`.

Sous-ecrans utiles :

| Sous-ecran | Role |
|---|---|
| Vue marche | montant, lots, sites, avancement, alertes |
| Factures | controle P1/P2/P3, decision, export finance |
| Performance | consommations, DJU, cibles, interessement |
| Referentiel contractuel | acte, DPGF, P1, cibles, versions, diff |
| Travaux P3/P6 | devis, BPU, engagements, validation |
| Indices & formules | revision de prix, preuves PDF |

DALKIA doit rester un moteur specifique, pas une simple categorie de facture.

### 7.4 Patrimoine et rattachements

Ecran cible : `Patrimoine > Sites et batiments` et `Patrimoine > Rattachements`.

La fiche patrimoine devient le point de convergence :

```text
Site / batiment / local
-> compteurs
-> consommations
-> factures
-> contrats
-> equipements
-> actions a traiter
```

Les rapprochements doivent etre separes par moteur, avec un meme langage d'interface :

| Rapprochement | Source | Cible |
|---|---|---|
| PRM electricite | ENEDIS / factures | patrimoine |
| PCE gaz | GRDF / factures | patrimoine |
| Sites CPE | DALKIA | patrimoine |
| Sites CVC | inventaires terrain | patrimoine |

### 7.5 Technique

Ecran cible : `Technique`.

Le bloc technique ne doit pas etre cache sous DALKIA. Il doit permettre de lire les actifs terrain :

- inventaire CVC ;
- equipements SYPEMI ;
- sources DALKIA et SPIE ;
- fluides frigoriges / F-Gaz ;
- ESP ;
- rapport technique ;
- actions et risques.

SPIE doit etre traite comme un marche de maintenance propre, pas comme un clone de DALKIA.

## 8. Ce qu'il faut faire du listing endpoints

Le travail route -> endpoint n'etait pas inutile. Il doit devenir une matrice de support, avec des colonnes produit.

Colonnes a ajouter a la matrice :

| Colonne | Sens |
|---|---|
| Parcours utilisateur | travail reel aide par l'endpoint |
| Decision aidee | validation, contestation, rattachement, import, diagnostic |
| Ecran cible | ou l'action doit apparaitre |
| Niveau exposition | quotidien, expert, admin, cache, hors produit |
| Donnees necessaires | objets affiches dans l'ecran |
| Preuve front attendue | ce que l'utilisateur doit pouvoir constater |
| Statut refonte | garder, regrouper, deplacer, cacher, supprimer plus tard |

Regle :

```text
On ne renomme pas brutalement les endpoints.
On reconstruit d'abord les ecrans, puis on consolide l'API quand les usages sont stabilises.
```

## 9. Ordre de chantier recommande

### Phase 0 - Stopper les micro-patchs d'ecran

Objectif : eviter de continuer a empiler des ajustements locaux sans architecture.

Livrable :

- ce document ;
- validation de la navigation cible ;
- choix du premier parcours a reconstruire entierement.

### Phase 1 - Shell de navigation et cockpit

Objectif : installer la structure produit.

Livrable front :

- navigation principale en six domaines ;
- tableau de bord avec files a traiter ;
- routes actuelles conservees ou redirigees pour ne rien casser ;
- composants communs : page header, KPI, statut, file a traiter, tableau decisionnel.

### Phase 2 - Parcours facture -> decision -> finance

Objectif : transformer la valeur backend la plus concrete en experience lisible.

Livrable front :

- `Marches & contrats > Factures marche` reconstruit ;
- `Marches & contrats > CPE DALKIA > Factures` reconstruit ;
- decision utilisateur explicite ;
- export finance visible et controle.

### Phase 3 - Patrimoine et rattachements

Objectif : faire du patrimoine la base maitre qui relie tout.

Livrable front :

- fiche site/batiment/local enrichie ;
- cockpit rattachements PRM/PCE/sites marche ;
- liens depuis factures, contrats, consommations et equipements.

### Phase 4 - Technique et marches secondaires

Objectif : reposer la partie terrain et maintenance.

Livrable front :

- Technique > Inventaire CVC ;
- Technique > Fluides et conformite ;
- Marches & contrats > SPIE ;
- Administration nettoyee.

## 10. Definition du "fonctionnel et joli"

Pour ce projet, "joli" ne veut pas dire decoratif.

La cible doit etre :

| Qualite | Definition pratique |
|---|---|
| claire | on comprend le probleme et l'action attendue en moins de 30 secondes |
| dense | les donnees importantes sont visibles sans page marketing |
| decideuse | chaque ecran aide a valider, contester, rattacher, exporter ou corriger |
| fiable | les sources et limites sont visibles |
| elegante | typographie, espacements, statuts et tableaux coherents |
| rassurante | pas de jargon technique inutile, pas de boutons dangereux sans contexte |

## 11. Premiere decision a prendre

La prochaine etape concrete est de choisir le premier paquet de refonte front.

Recommandation :

```text
Commencer par le shell + cockpit, puis reconstruire le parcours factures/finance.
```

Pourquoi :

- le shell fixe la nouvelle logique produit ;
- les factures/finance sont deja les plus proches d'une preuve metier complete ;
- le backend utile existe deja ;
- cela evitera de corriger encore une page isolee sans changer l'experience globale.

Decision proposee :

```text
Chantier suivant = creer la nouvelle architecture frontend cible,
avec navigation produit, cockpit et squelette des domaines,
sans supprimer les anciennes routes tant que les nouveaux parcours ne sont pas prets.
```
