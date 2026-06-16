# Spec page - Controle des factures ENGIE

> Premiere fiche de la refonte "page par page".
> Marche Herault Energie, fournisseur ENGIE.
> Statut : a valider.
> Emplacement cible : Facturation -> Herault Energie -> ENGIE.

## 1. Objectif unique

Controler les factures d'electricite ENGIE du marche Herault Energie, pour les batiments hors CPE, depuis l'export fournisseur importe jusqu'a la fiche de liaison transmise au service finance.

Une page = un fournisseur, un fluide, un usage. La page ENGIE ne doit pas contenir le pilotage multi-fournisseurs, les imports EDF, le gaz, l'eau, ni le marche DALKIA.

## 2. Utilisateur et moment

Le responsable energie ouvre cette page a reception d'un export ENGIE `MesFactures_*.xlsx`.

Il veut verifier que les prix, quantites, periodes et taxes/acheminement factures sont conformes aux references disponibles, puis trancher chaque facture : valider, contester, ou garder a verifier.

## 3. Donnees affichees

- En-tete compact : ENGIE, electricite, distributeur ENEDIS, perimetre batiments ville, millesime BPU actif.
- KPI ENGIE : factures importees, a controler, invalides, valides, decisions a rendre.
- Import XLSX ENGIE uniquement.
- Suivi mensuel facture ENGIE vs releve ENEDIS.
- Liste des factures ENGIE : numero, regroupement, titulaire, periode, montant TTC, statut de controle, decision.
- Detail facture via `/factures/:invoiceImportId` : BPU, TURPE, quantites ENEDIS, periodes, decision, liaison finance.

## 4. Actions attendues

- Importer un export ENGIE XLSX.
- Relancer l'analyse d'une facture ou du perimetre filtre.
- Filtrer les factures par statut, decision, periode, regroupement et recherche.
- Preparer un rapport fournisseur sur les factures a clarifier.
- Ouvrir la matrice comptable et produire la fiche de liaison finance depuis le detail facture.
- Supprimer une facture importee par erreur.

## 5. A garder de l'existant

- Le parcours en 4 etapes : Donnees & import -> Controle contractuel -> Rapport fournisseur -> Liaison finance.
- Le moteur de controle BPU/TURPE/periodes deja branche.
- La comparaison facture ENGIE vs ENEDIS.
- Le rapport fournisseur `InvoiceSupplierReport`.
- La matrice comptable `EnergieAccountingMatrix`.
- La timeline des periodes facturees.
- Les filtres avances, mais replis par defaut.

## 6. A retirer de cette page

- Bande des fournisseurs ENGIE / EDF / TotalEnergies.
- Onglets fluide Electricite / Gaz / Eau.
- Bandeau multi-marches et lien CPE DALKIA.
- Import CSV EDF.
- Texte generique "controle des factures fournisseurs".
- Toute logique de pilotage du marche Herault dans son ensemble.

Ces elements appartiennent soit a la page d'etat Herault Energie, soit aux futures pages dediees EDF, TotalEnergies, DALKIA et SPIE.

## 7. Manques fonctionnels

- Exposer `total_ht` dans la liste des factures si le backend le porte deja via la facture normalisee.
- Finaliser l'historique complet des decisions par facture.
- Produire un export consolide par periode pour la finance.
- Clarifier la route de retour depuis le detail facture selon le fournisseur d'origine.

## 8. Decision d'architecture

La page ENGIE doit etre montee sur une route dediee :

- cible : `/factures/herault/engie`
- redirection historique : `/energie/factures` reste redirige vers `/factures`
- detail facture : `/factures/:invoiceImportId` conserve l'URL actuelle

Le composant existant `EnergieInvoicesPage` peut servir de base, mais en mode fournisseur il doit se comporter comme une page dediee et non comme une version filtree du cockpit generique.

## 9. Premiere tranche de realisation

- Creer la route dediee `/factures/herault/engie`.
- Afficher un en-tete compact ENGIE dans le mode fournisseur.
- Restreindre l'import au XLSX ENGIE.
- Faire pointer la navigation Herault Energie -> ENGIE vers cette route (reste a faire lors de la refonte du cockpit `/factures`).
- Garder la page `/factures` comme etat/cockpit des marches tant que sa refonte specifique n'est pas traitee.
