---
type: decisions
status: actif
read_policy: si la tâche concerne le lot F4 de l'outil thermique
related:
  - metres-sur-plan-F3-decisions.md
  - parcours-par-niveau-E3bis-decisions.md
  - relais-local-F0-decisions.md
---

# Lot F4 — les éléments : voir, isoler, modifier, exclure — décisions

> Fichier « fil du dev » ouvert le **2026-09-24**, après la mise en production de F0. Existant vérifié
> sur les **vraies données du R+1**, décisions proposées, puis questions numérotées à trancher **avant**
> d'écrire du code.

## 1. Le problème, chiffré sur le vrai R+1

Le relevé du niveau porte **227 éléments**, dont **92 marqués « à vérifier » — 40 %**. Aujourd'hui le
thermicien les voit dessinés sur le plan (F3) mais ne peut rien en faire : ni les confirmer, ni corriger
une dimension, ni écarter un élément que l'agent a cru voir. Il n'a aucun moyen de faire baisser ce 40 %.

Répartition des 227 éléments par type :

| Type | Nombre |
|---|---|
| menuiserie | 58 |
| paroi | 51 |
| angle_sortant | 43 |
| angle_rentrant | 21 |
| poteau | 17 |
| garde_corps | 14 |
| about_refend | 13 |
| indéterminé | 10 |

## 2. Existant vérifié

### La donnée source est le relevé brut, pas ce qui est dessiné

`enveloppe.releve_brut.elements` porte les 227 enregistrements. Chacun a la même forme :

```json
{"troncon": "T02", "debut_m": 4.32, "fin_m": 7.3, "type": "menuiserie", "composant": "M1",
 "nu_exterieur_cm": -3, "nu_interieur_cm": -26, "nu_exterieur_fin_cm": -3, "nu_interieur_fin_cm": -26,
 "couches": [], "menuiserie_type": "mur-rideau", "cadre_cm": -4, "confiance": 0.85,
 "indice": "double trait fin vers -4, trait simple -26", "a_verifier": false}
```

`enveloppe.objets` (289 formes dessinées) en est le **reflet** : `thermique_etude_edition.reconstruire()`
le régénère intégralement à chaque recalcul, depuis `releve_brut`. **Conséquence décisive : une correction
écrite ailleurs que dans `releve_brut` serait effacée au premier recalcul.**

### La chaîne de recalcul existe et ne demande ni agent ni image

`reconstruire()` enchaîne déjà `decouper_par_piece` → `reprojeter` → `synthese_pieces` → `fiches` →
`demandes_etude` → `controler_couverture` → `controler_niveau`. Corriger un élément, c'est modifier le
relevé puis rappeler cette chaîne : **rien de nouveau à écrire côté calcul**.

### Les opérations d'édition ont déjà leur cadre

`thermique_etude_edition.OPERATIONS = ("modifier", "couper", "fusionner")`, appliquées par
`appliquer(contenu, operations)`, avec aperçu (`remodeliser`) et enregistrement versionné
(`enregistrer`). F4 ajoute des opérations à cette liste, il n'invente pas un second mécanisme.

### Le catalogue est partagé

`composant` renvoie au catalogue du niveau (`P1`, `M1`, `L1`…). Plusieurs éléments portent le même
composant : corriger le composant corrige tout le monde. C'est une force et un piège — voir Q3.

### Ce qui n'existe pas

- Aucun moyen de **désigner** un élément : la couche des métrés est en `pointer-events: none` (D79,
  pour que le plan reste déplaçable).
- Aucun panneau d'élément, aucune opération d'élément, aucune notion d'élément écarté.
- Aucune façon de faire baisser le compteur « à vérifier ».

## 3. Décisions proposées

### D99 — Une correction s'écrit dans le relevé brut, jamais dans le dessin

Toute opération d'élément modifie `enveloppe.releve_brut.elements`, puis `reconstruire()` refait le
dessin, les fiches, la synthèse et la couverture. C'est la seule façon qu'une correction survive au
recalcul suivant, et cela garantit que ce qui est affiché découle toujours de ce qui est mesuré.

### D100 — Écarter n'est pas supprimer

Un élément écarté reste dans le relevé avec `exclu: true` et un motif. Il n'entre plus dans les métrés
ni dans les fiches, mais il reste visible en grisé sur le plan et reste réactivable. Supprimer
détruirait la trace de ce que l'agent avait lu, et empêcherait de revenir en arrière.

### D101 — Confirmer est un geste à part entière

Un élément « à vérifier » que le thermicien regarde et approuve passe `a_verifier: false` **sans rien
changer d'autre**. C'est le geste le plus fréquent — 92 fois sur le R+1 — et il doit coûter un clic.

### D102 — L'élément se désigne sur le plan, et se retrouve dans une liste

Deux chemins vers le même panneau : cliquer la forme sur le plan, ou la prendre dans la liste des
éléments du local sélectionné. Le clic sur le plan ne doit pas casser le déplacement (D79) : seuls les
éléments **du local sélectionné** deviennent cliquables, le reste de la couche laisse passer.

### D103 — Les corrections s'accumulent avant de recalculer

Comme pour les contours (D68), une passe de corrections ne recalcule pas à chaque geste : on enchaîne,
puis on recalcule. Sur un local à quinze éléments, recalculer quinze fois serait insupportable.

### D104 — Ce qui est volontairement remis à plus tard

Réponse Q1 : les recommandations sont retenues **et ce qui en est écarté doit rester écrit**, pour ne pas
être redécouvert comme un oubli. Sont hors du lot F4, sans être abandonnés :

| Reporté | Pourquoi | Quand le reprendre |
|---|---|---|
| `couches` d'un élément | se corrigent déjà par le composant, dans la bibliothèque | si un élément doit un jour diverger de son composant |
| `menuiserie_type`, `cadre_cm` | n'entrent pas dans le calcul tant que la menuiserie n'est pas rattachée au référentiel | avec E4 (bibliothèque alimentée) |
| bornes `debut_m` / `fin_m` | geste géométrique délicat : déplacer une borne déplace le voisin | avec l'ajout d'élément (Q2), même famille de gestes |
| ajout d'un élément non relevé | demande de désigner une position sur un tronçon | second temps de F4, après correction et exclusion |

### D105 — Un recalcul de niveau coûte 3 secondes, pas 3 dixièmes

Mesuré le 2026-09-24 sur le vrai R+1 (24 locaux, 227 éléments, 289 formes), après la mise en ligne de F4 :

| Étape de `reconstruire()` | Avant | Après index spatial |
|---|---|---|
| `fiches_locaux` | **4,79 s** | **0,9 s** |
| `limites_des_locaux` | 0,89 s | 0,89 s |
| `decouper_par_piece` | 0,47 s | 0,47 s |
| tout le reste | 0,15 s | 0,15 s |
| **chaîne complète** | **6,6 à 19,4 s**, en dérive | **3,2 s**, stable |

La cause : un sondage tous les 10 cm sur chaque côté de chaque local, chacun testant un point tous les
3 cm jusqu'à 1,20 m, et **chacun de ces points interrogeant les 24 locaux du niveau**. Des millions de
tests. Un index spatial (`Voisinage`) ramène l'interrogation aux seuls locaux dont la boîte englobe le
point. L'ordre d'origine est conservé — deux locaux peuvent se recouvrir, et c'est le premier qui
l'emporte — et les fiches produites sont **identiques au fichier près** (sha256 `a5260e5a`, 222 côtés,
170,12 m déperditifs, avant comme après).

**Ce que cela impose** : même à 3,2 s, recalculer à **chaque clic** est intenable. Confirmer les 92
éléments douteux du R+1 demanderait cinq minutes d'attente pure. Or dix gestes envoyés ensemble coûtent
**3,4 s**, soit le prix d'un seul : le coût est le recalcul, pas le geste. C'est exactement ce que D68 et
D103 avaient prévu ; F4 a été livré sans le respecter, en appelant le serveur après chaque geste.

**Correction** : les gestes sur les éléments s'appliquent d'abord **dans l'écran**, sans serveur — un
élément confirmé, corrigé ou écarté se voit aussitôt dans la liste et le panneau. Le recalcul n'a lieu
que sur demande (« Recalculer ») et à l'enregistrement, et c'est lui qui met le **plan** à jour. L'écran
dit franchement ce qui attend : « 7 corrections en attente — recalculez pour les voir sur le plan ».

## 4. Questions numérotées — réponses du 2026-09-24

**Les huit recommandations sont retenues telles quelles.** Q1 s'accompagne de D104, qui consigne ce qui
est reporté pour que ce ne soit pas perdu. L'énoncé complet est conservé ci-dessous.

### Rappel de l'énoncé initial

**Q1 — Que doit-on pouvoir corriger ?** Le relevé porte, par élément : son **type** (menuiserie, paroi,
poteau…), son **composant** du catalogue, ses **nus** intérieur et extérieur en cm (début et fin), ses
**couches**, le **type de menuiserie**, le **cadre**, et ses bornes sur le tronçon (`debut_m`, `fin_m`).
*Recommandation : d'abord le **type**, le **composant** et les **nus**. Ce sont les trois qui changent le
calcul. Les couches se corrigent déjà par le composant, dans la bibliothèque. Les bornes sur le tronçon
sont un geste géométrique délicat : à garder pour plus tard, sauf si vous les jugez indispensables.*

**Q2 — Peut-on ajouter un élément que l'agent n'a pas vu ?** Un oubli de menuiserie fausse le calcul
autant qu'une erreur.
*Recommandation : **oui, mais en second temps**. Corriger et écarter d'abord, ajouter ensuite : ajouter
demande de désigner une position sur un tronçon, c'est le geste le plus lourd des trois.*

**Q3 — Corriger un composant : partout ou ici seulement ?** Si `P1` est mal lu et que trente éléments le
portent, voulez-vous corriger les trente d'un coup, ou seulement celui que vous regardez ?
*Recommandation : **demander à chaque fois**, avec le nombre en clair (« P1 est porté par 30 éléments :
corriger partout, ou détacher celui-ci ? »). Un choix implicite dans un sens ou dans l'autre fera des
dégâts silencieux.*

**Q4 — Faut-il une file des 92 « à vérifier » ?** Un enchaînement « suivant, suivant » qui parcourt les
éléments douteux du niveau, comme le parcours pièce par pièce le fait pour les locaux.
*Recommandation : **oui**, c'est ce qui rend les 40 % traitables. Mais après le panneau d'élément : la
file n'a de sens que si le geste unitaire est déjà rapide.*

**Q5 — Le compteur « à vérifier » doit-il bloquer la validation d'un local ?** Aujourd'hui on valide un
local sans que ses éléments douteux soient regardés.
*Recommandation : **prévenir sans bloquer**. Afficher « 4 éléments non confirmés » sur le local et le
laisser valider : c'est vous le thermicien, et certains éléments douteux n'ont aucun effet sur le calcul.*

**Q6 — Un élément écarté doit-il rester visible sur le plan ?** D100 propose de le garder en grisé.
*Recommandation : **oui**, sinon vous ne saurez plus ce que vous avez écarté ni pourquoi, et vous
risquez de l'écarter deux fois ou de le chercher.*

**Q7 — Faut-il tracer qui a corrigé quoi ?** Le relevé porte déjà `confiance` et `indice` (ce que l'agent
a cru voir). Une correction humaine pourrait garder la valeur d'origine à côté de la nouvelle.
*Recommandation : **oui, et c'est peu coûteux** : garder `releve_origine` sur l'élément corrigé. Cela
permet de comparer ce que l'agent a lu et ce que vous avez corrigé, donc de mesurer sa qualité niveau
après niveau — la question qui traverse tout le projet.*

**Q8 — Où le panneau s'affiche-t-il ?** Dans le panneau de droite à la place de la fiche du local, ou
dans une carte flottante près de l'élément sur le plan ?
*Recommandation : **dans le panneau de droite**, sous la fiche du local. Une carte flottante masquerait
justement le plan qu'on essaie de lire.*

## 5. Contrôles prévus

1. Service : une correction survit à `reconstruire()` ; un élément écarté sort des métrés et des fiches
   et revient s'il est réactivé ; corriger un composant partout touche bien tous ses porteurs et un
   détachement n'en touche qu'un.
2. Garde-fous : un nu incohérent (intérieur au-delà de l'extérieur), un type inconnu, un élément qui
   n'existe pas.
3. Interface : désigner un élément sur le plan sans casser le déplacement du plan (D79), corriger,
   confirmer, écarter, réactiver.
4. Recette réelle R+1 : faire baisser le compteur « à vérifier » depuis 92, vérifier qu'une menuiserie
   corrigée change bien la fiche du local, et qu'un élément écarté disparaît des métrés.
5. Tests thermiques ciblés, typage, construction.
