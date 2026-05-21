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

## Raffinement tableau fournisseur

- La section `Points soumis a clarification` concentre maintenant l'information utile dans la colonne `Point`.
- La colonne `Niveau` est retiree pour eviter une lecture accusatoire ou redondante dans le rapport fournisseur.
- La colonne `Factures` ne donne plus que le volume concerne ; le detail des factures reste dans la section dediee.
- Le point affiche le message de controle, le contexte de sa famille, le perimetre detecte quand il existe et le code de controle.

## Clarification TURPE

- Le rapport fournisseur ne retient plus les alertes TURPE de controle partiel (`TURPE_COMPONENT_UNSUPPORTED`, `TURPE_TARIFF_UNSUPPORTED`, etc.) comme des ecarts fournisseur.
- L'editeur de rapport affiche ces limites TURPE exclues pour les garder visibles sans les imprimer dans le document fournisseur.
- Le detail facture expose un tableau dedie aux lignes d'acheminement exploitees par le controle TURPE ; ces lignes ENGIE ne portent pas toujours le mot `TURPE`.
- Le parseur facture ENGIE reconnait maintenant les lignes de correction negatives. Sur les 83 PDF locaux, les 3 ecarts TURPE calcules observes avant correction disparaissent ; il reste des limites de couverture du controle a traiter separement.

## Audit autres controles sur les 83 PDF

- Les totaux FIC negatifs de regularisation sont maintenant lus ; la facture `160000136326` ne produit plus de faux signal TTC/TVA local sur sa FIC creditrice.
- Le controle `quantite x PU` ignore les lignes ENGIE normalisees `other`, notamment les depassements de puissance dont le montant ne se deduit pas du seul couple extrait.
- Les libelles `Heures Pleines/Creuses Haute/Basse Saison` sont normalises pour rendre le controle BPU plus explicite sur les postes saisonniers.
- Le rapport fournisseur exclut aussi les limites internes BPU/ENEDIS/perimetre (`BPU_REFERENCE_MISSING`, donnees ENEDIS absentes ou partielles, `UNKNOWN_PRM`, etc.).
- Apres correction, les alertes PDF locales restantes portent surtout sur les periodes (`69` gaps et `4` overlaps a qualifier) et `3` factures sans donnees Chorus.
- Les alertes locales ENEDIS restent massivement liees a la couverture de donnees : `529` consommations manquantes, `52` consommations partielles, `324` jeux de puissance absents et `170` occurrences de PRM non retrouves dans le CSV contrats local.
- Simulation BPU avec le gabarit ENGIE lot 1 : `2915` lignes prix raccordes, `33` lignes encore en ecart ; `32` sont des candidats incoherence tarif/poste sur des lignes saisonnieres affichees sous option `Longue utilisation`, une ligne isolee reste sur la facture `150000058810`.
