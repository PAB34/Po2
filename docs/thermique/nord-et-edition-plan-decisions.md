---
type: decisions
status: actif
read_policy: si la tâche concerne l'outil thermique
related:
  - metres-sur-plan-F3-decisions.md
  - edition-pieces-E3-decisions.md
---

# Nord de la planche et gestes d'édition — décisions

> Fichier « fil du dev » ouvert le **2026-09-23**, après reprise du travail interrompu par la limite
> de session Claude Code. Il consigne l'existant vérifié, les décisions issues des demandes utilisateur
> et les contrôles attendus avant livraison.

## 1. Existant vérifié

- `thermique_projects.north_deg` existe depuis la migration 0078, mais son ancien repère commun a été
  supprimé avec les tables de métré historiques par la migration 0082. La valeur n'est plus exposée ni
  utilisée par l'espace de travail refondé.
- Les études importées portent déjà, côté par côté, une orientation. Tant qu'aucun nord fiable n'est
  défini, elle vaut `nord à caler`.
- Les planches sont affichées par des tuiles raster. Les gestes sont enregistrés en points PDF, seul
  repère durable quand l'utilisateur tourne l'affichage.
- L'édition E3 sait déplacer, ajouter et retirer un sommet, mais la suppression répétée d'une dentelle
  de points est trop lente. Le travail Claude interrompu avait commencé un lasso et un menu contextuel.

## 2. Décisions du 2026-09-23

- **D85 — Geste sans ambiguïté.** Le thermicien clique d'abord la base d'une flèche, puis sa pointe,
  obligatoirement **du côté du nord**. Un `N` est dessiné à la pointe et la direction est reformulée en
  clair avant validation.
- **D86 — Donnée par planche.** La flèche est stockée en points PDF sur chaque planche. L'action
  « appliquer à tous les plans » copie sa **direction** et réancre son dessin dans chaque format de page ;
  elle ne réutilise pas aveuglément les mêmes coordonnées.
- **D87 — Orientations dérivées.** Poser ou redéfinir le nord recalcule immédiatement les orientations
  de l'étude importée, sans déplacer les contours et sans créer artificiellement une version d'édition.
- **D88 — Lasso libre.** En reprise de contour, `Alt + glisser` dessine un lasso libre et retire au
  relâchement les sommets entourés. L'opération est refusée si elle laisserait moins de trois sommets.
- **D89 — Menu contextuel.** Le clic droit propose uniquement les gestes applicables au point visé :
  ouvrir/reprendre/couper un local hors édition ; ajouter, supprimer ou redresser un côté en édition.
- **D90 — Aucune confusion entre outils.** Les deux points d'une mesure ou d'un contrôle d'échelle ne
  doivent jamais être rendus comme une flèche du nord provisoire.

## 3. Questions numérotées et réponses

- **Q1 — Dans quel sens tracer ?** Réponse utilisateur : il faut un dispositif compréhensible.
  Décision D85 : base puis pointe vers le nord, rappelée avant et après le geste.
- **Q2 — Une fois ou par niveau ?** L'ancien choix projet reste utile, mais les feuilles peuvent avoir
  des formats différents. Décision D86 : case projet proposée, avec adaptation propre à chaque planche.
- **Q3 — Quand recalculer les orientations ?** Recommandation retenue : immédiatement à la validation,
  car une flèche enregistrée avec des fiches encore « à caler » serait incohérente.
- **Q4 — Rectangle ou lasso ?** Réponse utilisateur explicite : **lasso**, pas rectangle. Décision D88.

## 4. Contrôles de sortie

1. Service nord : huit secteurs, rotations de rendu, coordonnées invalides et propagation entre formats.
2. Édition : lasso vide, lasso multiple, garde-fou du triangle et redressement d'un côté, y compris au
   passage de l'angle −180°/180°.
3. Frontend : tests thermiques ciblés, typecheck et build.
4. Recette réelle R+1 : direction lisible, validation, lasso libre, menu contextuel, navigation intacte.
