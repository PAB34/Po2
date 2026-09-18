---
type: decisions
status: actif
read_policy: si la tâche concerne les contours de pièces
related:
  - metre-thermique-decisions.md
  - refondation-parcours-decisions.md
---

# Contours de pièces — audit et décisions

> Audit ciblé réalisé le **2026-09-18** avant reprise du travail interrompu dans la session
> « Outil thermicien métré plans ».

## Existant vérifié

- Le front `PiecesPage.tsx` sait déjà sélectionner une pièce puis ouvrir **Corriger le contour**.
  L'utilisateur peut déplacer un sommet, cliquer un côté pour en ajouter un et faire Alt + clic pour
  en retirer un.
- Le backend recalcule la surface après correction manuelle et marque la pièce comme manuelle.
- Le contour proposé au clic passe par une première tentative de réduction aux quatre droites
  dominantes. Le travail est non commité et interrompu : une constante manque, et la stratégie
  « quatre côtés à tout prix » n'est pas adaptée au grand espace irrégulier.
- Le contour détaillé d'origine peut déjà être conservé dans `points_json`, sans migration de base.

## Décisions du 2026-09-18

1. **L'utilisateur reste l'autorité finale.** La correction manuelle existante est conservée et
   testée ; aucun contour automatique ne doit rendre cette correction impossible.
2. **Pièce courante : quatre droites dominantes.** Une proposition quadrilatère est acceptée
   seulement si ses quatre supports expliquent l'essentiel du périmètre, produisent un polygone simple
   et donnent une géométrie cohérente.
3. **Grand espace : simplification multi-côtés.** Si le quadrilatère n'est pas fiable, on supprime les
   sommets quasi alignés et les petits zigzags avec une tolérance métrique, sans effacer les véritables
   angles d'une forme en L ou en U.
4. **Garde-fous.** Une simplification multi-côtés est refusée si elle croise ses propres segments ou
   modifie trop la surface. Le contour brut est alors rendu tel quel.
5. **Traçabilité.** Dès qu'un contour est simplifié, le contour détaillé d'origine est conservé à côté.
   Une correction manuelle devient la nouvelle vérité et n'est jamais simplifiée à nouveau.
6. **Contour douteux : retracé court.** Au-delà de douze sommets, l'interface prévient l'utilisateur et
   propose de remplacer entièrement la zone en cliquant ses angles. C'est préférable à la suppression
   manuelle de dizaines de points issus d'une fuite entre pièces.

## Validation réelle du R+1 — 2026-09-18

Lecture seule de cinq clics de référence sur la planche 25, autorisée par l'utilisateur :

- un bureau passe correctement de 20 à 4 sommets ;
- le cas le plus bruité passe de 59 à 19 sommets ;
- trois zones restent de surface fausse et une ne se ferme pas, car les limites désignées ne contiennent
  pas toutes les menuiseries visibles sur le plan ; le lissage ne peut pas inventer ces parois absentes ;
- la fermeture morphologique seule, isotrope ou directionnelle, ne résout pas ce manque et peut réunir
  plusieurs pièces. Elle est donc écartée comme correction générale.

Conséquence : l'étape suivante du moteur hybride devra proposer les limites manquantes depuis le rendu
raster/IA, puis les recaler sur les traits vectoriels. En attendant, le retracé en quelques clics rend le
parcours fiable sans présenter une géométrie automatique douteuse comme exacte.

## Validation ciblée

- rectangle, rectangle incliné et décrochements de portes ;
- contour qui fuit par une baie ;
- forme en L préservée ;
- grand espace comportant de nombreux zigzags, simplifié sans devenir un quadrilatère ;
- polygone auto-croisé ou déformation excessive refusés ;
- service : conservation du contour détaillé et recalcul de la surface.
