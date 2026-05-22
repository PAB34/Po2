# Module - Energie / Gaz

> Cadre simple pour ne pas melanger provenance distributeur, contrat fournisseur et CPE DALKIA.

## Decision de perimetre

Le point commun du gaz est le `PCE` :

1. `GRDF` porte la donnee distributeur : PCE, donnees techniques, consommations et futures courbes disponibles par API ou fichier.
2. `HERAULT ENERGIE / TotalEnergies` porte la fourniture gaz des compteurs dont la collectivite est titulaire.
3. `DALKIA P1` porte une fourniture gaz contractuelle du marche CPE sur certains sites, avec ses cibles et sa cotation OS3.

Ces trois sujets se croisent sur le patrimoine, mais ils ne doivent pas etre fusionnes en un seul module facture ou CPE.

## Ce qui existe

### Socle patrimoine

`BuildingMeterLink` est ajoute pour rattacher manuellement un compteur au batiment depuis `/buildings/:id` :

- fluide ;
- identifiant compteur (`PCE` gaz, `PRM` electricite ou identifiant eau) ;
- libelle et usage ;
- contexte fournisseur/contrat ;
- dates de validite, cle de repartition et statut de validation cote modele.

La V1 permet le lien manuel. Le cas "un compteur alimente plusieurs batiments" reste a porter dans une evolution du modele et des ecrans.

### Reference prix Ville

Le BPU `saas/energie/HERAULT ENERGIE/BPU_2026_Lots_1_2_et_7.xlsx` fournit le lot gaz `7` TotalEnergies :

- profils `T1` a `T4` selon la consommation annuelle ;
- composantes 2026 : fourniture ferme, CEE classique, CEE precarite, CPB et GO ;
- script d'import : `app.scripts.import_bpu_gas_lot7`.

Cette reference servira au controle des futures factures gaz TotalEnergies sur les PCE Ville.

### CPE DALKIA

Le module CPE DALKIA garde :

- ses sites, cibles NB/ECS et releves mensuels ;
- les PCE deja presents dans le perimetre CPE ;
- la cotation OS3 gaz fixe 2026-2030 pour le P1.

Les documents canoniques restent sous `docs/energie/CPE-DALKIA/`.

## Prochain chemin conseille

1. Rattacher quelques PCE de test aux batiments avec `BuildingMeterLink` en qualifiant `Ville TotalEnergies` ou `P1 DALKIA`.
2. Importer un echantillon GRDF CSV/XLSX sur ces PCE dans le futur pipeline gaz.
3. Ajouter le parser factures gaz TotalEnergies en s'appuyant sur le BPU lot 7.
4. Relier proprement les PCE CPE DALKIA au referentiel compteurs central sans casser le calcul CPE existant.
