# Questions - suite refonte Matrices + Factures

Date : 2026-06-25

Objectif : verrouiller la prochaine tranche apres la preview matrices, pour passer d'une belle UX de principe a un flux utilisable par toi puis par la comptabilite.

## 1. Priorite immediate

Question : quelle tranche doit passer en priorite maintenant ?

Reponse :

- [x] A - Continuer la maquette UX sans backend pour aller vite sur les ecrans.
- [x] B - Remettre le backend local/API en route pour tester les vraies donnees.
- [ ] C - Construire directement l'ecran Factures & decisions V1 raccorde aux matrices.
- [ ] D - Finaliser l'atelier Matrices avec export/import XLSX avant de toucher aux factures.

Commentaire :


## 2. Export comptabilite XLSX

Question : le fichier envoye a la comptabilite doit-il etre concu comme un fichier tres simple a remplir, meme s'il contient moins d'informations, ou comme un fichier complet avec beaucoup de colonnes de controle ?

Reponse :

- [ ] Simple et guidé : moins de colonnes, plus facile a remplir.
- [x] Complet : toutes les informations utiles, quitte a etre plus dense.
- [ ] Deux onglets : un onglet simple a remplir + un onglet technique/detail.

Commentaire :


## 3. Statuts factures

Question : quels statuts veux-tu voir dans le workflow facture ?

Proposition de base :

- Nouvelle
- Deja traitee
- Reimportee identique
- Reimportee modifiee
- A controler
- En litige fournisseur
- Validee comptabilite
- Exportee finance

Reponse / corrections :

Ok propositions
## 4. Decision apres controle facture

Question : quand une facture a des ecarts ou une imputation incomplete, que doit pouvoir faire l'utilisateur ?

Proposition :

- Valider quand meme avec commentaire.
- Mettre en attente fournisseur.
- Generer un mail fournisseur.
- Corriger manuellement l'imputation.
- Demander correction de la matrice comptable.
- Exclure la facture du traitement courant.

Reponse / corrections :

Ok propositions
## 5. Fournisseurs a traiter dans la V1

Question : confirmes-tu que la V1 doit traiter en priorite ces quatre fournisseurs avant SUEZ/SPIE ?

- DALKIA
- ENGIE
- EDF
- TotalEnergies

Reponse :

oui
## 6. Role de la comptabilite dans l'application

Question : a terme, la comptabilite doit-elle se connecter a la plateforme, ou seulement completer un fichier XLSX hors plateforme ?

Reponse :

- [x] Pour la V1 : XLSX seulement.
- [x] A terme : acces plateforme lecture/ecriture limite.
- [x] Les deux : XLSX maintenant, compte utilisateur plus tard.

Commentaire :


## 7. Backend local

Question : veux-tu que la prochaine action technique soit de remettre l'environnement backend local en route pour tester les vraies donnees ?

Constat actuel : le front React fonctionne sur `5173`, mais l'API FastAPI n'est pas joignable sur `8000` et Postgres local n'ecoute pas sur `5432`.

Reponse :

- [x] Oui, priorite a l'environnement local complet.
- [ ] Non, on continue d'abord les previews UX.
- [ ] On utilisera plutot staging/prod pour tester les donnees reelles.

Commentaire :


## 8. Niveau d'ambition UI pour la prochaine tranche

Question : pour Factures & decisions V1, tu preferes quel niveau de finition ?

Reponse :

- [ ] Wireframe propre : rapide, fonctionnel, pas final.
- [x] Prototype visuel avance : proche de l'interface definitive.
- [ ] Ecran raccorde API prioritaire, design ensuite.

Commentaire :


## Synthese assistant

Ma recommandation actuelle :

1. Finaliser l'UX Matrices jusqu'au flux export/import XLSX comprehensible.
2. Puis construire Factures & decisions V1 autour de la logique : facture importee -> controle -> decision -> imputation comptable -> export finance.
3. En parallele, remettre un environnement backend local ou staging stable, car sans donnees reelles on risque de faire une belle interface mais de rater des cas metier.

Le prochain vrai jalon produit devrait etre : "je peux prendre une facture reelle, voir son controle, voir son imputation comptable proposee, decider quoi faire, et produire un export exploitable par la comptabilite".