# 43 - Decisions apres reponses sur l'assistant matrices V1

Date : 2026-06-25  
Source : reponses Pascal dans `docs/42-Questions-ciblees-apres-cartographie-existant.md`.

## 1. Decisions confirmees

### Assistant matrice dedie

Decision : creer une entree dediee `Configurer la matrice comptable`.

Le parcours cible est valide :

1. importer un export facture de reference ;
2. detecter les lignes recurrentes ;
3. completer les axes comptables dans un tableau ;
4. exporter/importer XLSX ;
5. verifier que tout est couvert ;
6. activer la version.

Consequence : la configuration matrice ne doit pas etre noyee dans la file `Factures & decisions`. La file facture consomme les matrices activees, mais l'administration/configuration des matrices est un atelier a part.

### Tous les tiers facturants doivent avancer

Decision : ne pas limiter le chantier a DALKIA.

DALKIA reste le cas le plus complexe et structurant, mais l'objectif immediat est de pouvoir produire rapidement des exports XLSX a transmettre au service comptabilite pour tous les tiers concernes : DALKIA, ENGIE, EDF, TotalEnergies, puis SUEZ/SPIE quand les fichiers seront disponibles.

Consequence : l'assistant doit etre multi-fournisseurs des le depart, avec des schemas de detection differents selon le tiers.

### Anciennes factures DALKIA

Decision : les factures portant sur l'ancien marche doivent rester visibles, mais avec le badge `Ancien marche - hors controle courant`.

Consequence : ne pas les supprimer et ne pas les masquer completement. Elles doivent etre distinguees pour ne pas polluer le controle du nouveau marche autour du 11 octobre 2025.

### Roles

Decision metier rappelee : les roles cibles sont :

- Admin ;
- Direction ;
- Responsable maintenance ;
- Fluide ;
- Technicien CVC ;
- Patrimoine.

Regle matrices : tous les roles autorises sauf Fluides et Technicien CVC.

Implementation actuelle ajustee :

- autorises : ADMIN, SUPERADMIN, DIRECTION, RESPONSABLE_MAINTENANCE, PATRIMOINE, FINANCE, COMPTA, COMPTABILITE ;
- exclus : FLUIDES, FLUIDE, RESPONSABLE_FLUIDES, TECHNICIEN_CVC, TECHNICIEN CVC.

Note : les roles FINANCE/COMPTA/COMPTABILITE restent acceptes pour compatibilite avec l'existant, meme s'ils ne font pas partie de la nomenclature utilisateur finale rappelee.

### Contacts fournisseur

Decision : contacts libres suffisants en V1.

Champs cible minimaux : nom, email, telephone, commentaire. Pas besoin de typologie stricte facturation/reclamation/technique/commercial au depart.

### Navigation Fluides

Decision : organisation visible validee :

- `Fluides > Portefeuille` ;
- `Fluides > Electricite` ;
- `Fluides > Gaz` ;
- `Fluides > Eau` ;
- `Fluides > Abonnements a recalibrer` ;
- `Fluides > Referentiels et prix`.

Consequence : la refonte doit assumer une navigation Fluides plus structuree, pas une seule page fourre-tout.

## 2. Changement de priorite technique

Avant reponse, la recommandation etait : DALKIA pilote, puis les autres.

Apres reponse, la cible devient : assistant multi-tiers rapidement exploitable pour generer des XLSX comptables.

Ordre recommande :

1. exposer l'export XLSX de versions matrices existantes dans `/refonte-v1/matrices` ;
2. ajouter ensuite l'import/preview/commit XLSX cote front ;
3. construire l'assistant de detection recurrente par source ;
4. commencer le moteur de detection par les sources deja parsees : ENGIE/EDF normalises, TotalEnergies gaz, CPE DALKIA ;
5. afficher la couverture : recurrent couvert / non couvert / a arbitrer / ancien marche.

## 3. Avancement realise dans cette tranche

- `/refonte-v1/matrices` affiche un atelier de configuration par tiers facturant.
- Les roles matrices sont alignes sur la decision : Fluides et Technicien CVC en lecture seule.
- L'export XLSX d'une version de matrice est expose cote frontend via le bouton `Exporter XLSX` dans le drawer de version.
- Le backend possedait deja l'endpoint `/api/accounting-matrices/versions/{version_id}/export.xlsx` ; le frontend sait maintenant l'appeler.

## 4. Prochaine tranche logique

Ajouter le flux retour comptabilite :

1. bouton `Importer XLSX complete par la compta` ;
2. appel `import-preview` ;
3. affichage des differences et erreurs ;
4. bouton `Creer une version brouillon` ;
5. controle de couverture avant activation.

Cette tranche est prioritaire avant d'appliquer automatiquement les matrices aux factures.

## 5. Avancement realise apres cette decision

Le retour comptabilite XLSX est maintenant raccorde cote frontend :

- export d'une version de matrice depuis le drawer ;
- import du fichier complete ;
- preview sans ecriture ;
- affichage du resume d'ecarts ;
- creation d'une nouvelle version brouillon si le fichier est valide.

Cela permet de commencer a envoyer des matrices au service comptabilite sans attendre le moteur complet de detection automatique des lignes recurrentes.
