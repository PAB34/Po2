# 2026-05-21 — Rapport fournisseur factures filtrees

## Objectif

Transformer les filtres de `/energie/factures` en rapport de demande d'explications exploitable avec le fournisseur d'energie.

## Principe retenu

- Le rapport part de la liste filtree, puis conserve les factures qui portent des points de controle a clarifier.
- Les filtres par categorie et type de probleme restreignent aussi les points affiches dans la synthese fournisseur.
- Le rapport ne conclut pas a une erreur certaine : il expose une demande de clarification utile pour le fournisseur et pour l'amelioration du modele Po2.

## Livraison code locale

- Bouton `Editer rapport` dans `Filtrer les factures`.
- Editeur avant emission : emetteur, destinataire, objet, contexte et demande.
- Preview fournisseur avec perimetre, indicateurs, points groupes et tableau des factures concernees.
- Sortie `Imprimer / PDF` via le navigateur avec mise en page dediee a l'impression.

## Validation

- `git diff --check` passe sur les fichiers frontend modifies.
- Le build frontend local reste non executable sur le poste : `npm` est absent et `node_modules` n'est pas present.

## Suite

Verifier en production le niveau de synthese sur un filtre reel, puis ajuster les formulations fournisseur avec les retours des premiers envois.

## Extension multi-selection

- Les filtres controle, decision, regroupement, titulaire, categorie et type de probleme acceptent maintenant plusieurs valeurs.
- Une selection vide reste equivalente a `Tous` / `Toutes`.
- La liste facture reste reactive a chaque case cochee.
- Le rapport fournisseur reprend le perimetre multi-selectionne et limite les points affiches aux categories/types choisis.
