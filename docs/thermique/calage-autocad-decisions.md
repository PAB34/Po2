# Calage des niveaux « comme AutoCAD » — décisions (2026-09-30)

## Existant vérifié

- Calage S2 (D173) : 4 clics (A calque, A plan, B calque, B plan), puis le serveur calcule d'un coup
  déplacement + rotation + échelle (`thermique_calage.py`, `superposition.ts`, `WorkspacePage.tsx`).
- Le calcul est juste (revérifié le 2026-09-30), mais le thermicien ne voit rien bouger avant la fin :
  un clic imprécis sur B fausse **à la fois** la rotation et l'échelle, sans qu'on comprenne pourquoi.
- Retour utilisateur : « calé mais décalé » ; il veut la méthode AutoCAD (commande ALIGNER).

## Proposition (D201)

Trois temps, le calque bougeant **à l'écran après chaque temps** :

1. **Point de base** : un clic sur le calque bleu, puis le même point sur le plan noir → le calque
   **glisse** pour que les deux points se touchent (déplacement seul).
2. **Rotation** : un clic sur un second point du calque, loin du premier, puis un clic sur le plan noir
   dans la direction où il doit aller → le calque **tourne autour du point de base** (échelle inchangée,
   celle des échelles déclarées).
3. **Longueur (facultatif)** : si le second point ne tombe pas exactement sur son homologue, un bouton
   « Ajuster aussi la longueur » étire le calque depuis le point de base (comme « Mettre à l'échelle les
   objets ? Oui » d'AutoCAD), en affichant l'écart en %.

Puis **Enregistrer**. Échap ou « Annuler » à tout moment ; « Recommencer l'étape » refait la dernière.

Technique : rien ne change côté serveur ; le navigateur envoie deux paires de points qui décrivent exactement
le résultat affiché.

## Questions

**Q49** — Pendant la rotation, faut-il un **aimant sur les angles droits** (0°, 90°, 180°, 270°) quand on
en est à moins de 1° ? Les plans d'un même bâtiment sont presque toujours dans le même sens.
a) oui, aimant à moins de 1° (recommandé) ; b) non, rotation libre.

REPONSE : a (recommandation retenue sur « déploie » du 2026-09-30) ; Alt tourne sans aimant.

**Q50** — Étape 3 : l'écart de longueur est-il seulement **proposé** (bouton), ou appliqué d'office ?
a) proposé, jamais appliqué seul : l'échelle déclarée fait foi (recommandé) ; b) appliqué d'office.

REPONSE : a (recommandation retenue).

**Q51** — Après l'enregistrement, **garder les croix** des deux points à l'écran jusqu'à la fermeture du
bandeau, pour vérifier que tout tombe juste ?
a) oui (recommandé) ; b) non.

REPONSE : a (recommandation retenue).

## Fait (2026-09-30)

`workspace/alignement.ts` (logique pure, testée dans `guideCalage.test.tsx`), `GuideCalage.tsx` (bandeau en
trois étapes, rotation affichée, boutons Enregistrer / Ajuster aussi la longueur / Refaire l'étape),
`WorkspacePage.tsx` (le calque suit la pose en cours). Serveur inchangé.
