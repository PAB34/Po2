# Reunion finances trimestrielle - presentation Po2 energie / DALKIA

> Statut : memo actif de preparation.
> Objectif : preparer une presentation de 30 minutes a la direction des finances lors de la reunion trimestrielle de suivi des depenses energie et du marche DALKIA.
> Angle : montrer que le service maintenance / energie maitrise, controle, explique et anticipe les impacts financiers.
> URL de demonstration pressentie : staging Po2, a verifier avant la reunion.

## Message central

Po2 ne doit pas etre presente comme un outil concurrent des vues finance, MANTY ou Power BI.
La bonne posture est complementaire :

- MANTY / Power BI donnent une vision consolidee du consomme, du previsionnel et des ecritures comptables.
- Po2 securise la donnee energie en amont : controle facture, recalcul metier, explication des ecarts, donnees contractuelles, projection technique et budgetaire.

Phrase cle :

> Power BI repond a la question : ou en est-on financierement ? Po2 repond a la question : est-ce que ce que l'on paie est juste, explicable et anticipable ?

Autre phrase utile :

> L'objectif est de transformer une depense energie subie en depense controlee, expliquee et projetee.

## Public et intention

Public principal : direction des finances.

Ce qu'il faut leur montrer :

- le service energie comprend les mecanismes qui produisent la depense ;
- les factures ne sont pas seulement suivies, elles peuvent etre controlees ;
- les ecarts peuvent etre documentes de facon lisible pour les finances ;
- les consommations et les changements de perimetre alimentent l'atterrissage budgetaire ;
- Po2 peut devenir un sas de qualite avant reporting financier consolide.

Ce qu'il faut eviter :

- noyer la reunion dans des details techniques ;
- donner l'impression de remplacer le travail finance / MANTY / Power BI ;
- montrer trop d'ecrans ;
- faire une demo longue et fragile.

## Plan recommande - 30 minutes

### 1. Introduction - 3 minutes

Titre possible : Piloter les depenses energie : du controle facture a l'anticipation budgetaire.

Messages :

- Le SOEM est a la croisee de l'energie, de la maintenance et de la finance.
- La depense energie est multi-sources, variable et contractuellement complexe.
- L'enjeu n'est pas seulement de suivre la depense, mais de la controler et de l'anticiper.

### 2. Missions SOEM sur l'energie - 4 minutes

Rappeler les missions :

- suivre les consommations gaz et electricite ;
- suivre les factures ;
- suivre le marche CPE DALKIA ;
- suivre interessement et penalites ;
- preparer le budget N+1 ;
- suivre l'atterrissage budgetaire de fin d'annee ;
- expliquer les ecarts aux finances.

Message : le sujet energie est autant financier que technique.

### 3. Complexite de la donnee energie - 5 minutes

Montrer une cartographie simple :

- DALKIA : P1 gaz, P2 exploitation, P3, interessement / penalites, sites du CPE.
- Ville : electricite des sites CPE, electricite hors CPE, gaz hors CPE via Herault Energie.
- Fournisseurs : ENGIE, EDF, TotalEnergies, DALKIA.
- Donnees : factures, exports fournisseurs, Chorus, consommations, contrats, indices, matrices comptables, DPGF, avenants.

Chiffres a ajouter avant reunion :

- consommation annuelle gaz ;
- consommation annuelle electricite ;
- montant annuel energie ;
- montant annuel marche DALKIA ;
- part fixe / part variable quand disponible ;
- nombre de sites CPE et hors CPE.

### 4. Risques sans controle centralise - 4 minutes

Risques a citer :

- payer une facture sans detecter un ecart ;
- ne pas comprendre une variation tarifaire ;
- decouvrir trop tard une derive budgetaire ;
- retraiter manuellement dans plusieurs fichiers Excel ;
- ne pas relier facture, site, contrat, matrice comptable et budget ;
- perdre l'explication metier derriere une ecriture comptable.

Phrase : la confiance n'exclut pas le controle.

### 5. Demonstration Po2 - 10 minutes maximum

Ne pas depasser 3 ou 4 ecrans.

#### Demo A - consommations et indicateurs energie

But : montrer le lien entre donnees techniques et atterrissage budgetaire.

A montrer si l'ecran est stable :

- consommation gaz / electricite par periode ;
- indicateurs simples : kWh, euros, evolution, derive ;
- lien avec projection fin d'annee ;
- lecture par fournisseur, marche ou site si disponible.

Message : la consommation est le premier signal d'atterrissage budgetaire.

#### Demo B - controle des factures

But : montrer la plus-value Po2 par rapport a un reporting financier classique.

A montrer :

- import facture ou consultation facture controlee ;
- montant facture vs montant recalcule ;
- ecart identifie ;
- explication courte : site manquant, export fournisseur incomplet, index, tarif, matrice, nature comptable.

Message : Po2 ne regarde pas seulement combien on a paye, il verifie si le montant paye est coherent.

#### Demo C - rapport comptable exploitable

But : montrer que le controle metier devient lisible pour les finances.

A montrer :

- rapport de controle comptable ;
- statut facture : rapprochee, ecart, absente plateforme, a controler ;
- explication de l'anomalie ;
- lien avec matrice comptable si disponible.

Message : Po2 transforme un controle technique en document exploitable par la comptabilite.

#### Demo D - DALKIA OS / avenant

But : montrer l'anticipation financiere.

A montrer :

- selection d'un site a supprimer ou creation d'un site ;
- colonnes P1, P2, P3 ;
- impact retenu = P2 + P3 ;
- prorata a la date d'effet ;
- projection par exercice et fin de marche ;
- export Excel d'impact si utile.

Message : avant de signer ou preparer un avenant, Po2 objective l'impact financier.

### 6. Lien avec budget et atterrissage - 3 minutes

Slide dediee : Des consommations vers l'atterrissage budgetaire.

Chaine logique :

1. consommations constatees ;
2. factures controlees ;
3. prix unitaires, indices, revisions ;
4. evenements connus : nouveaux sites, suppressions, avenants ;
5. projection fin d'annee ;
6. preparation budget N+1.

Phrase : l'atterrissage budgetaire ne repose pas seulement sur le consomme comptable ; il doit integrer les consommations reelles, les factures a venir, les variations tarifaires et les changements de perimetre.

### 7. Conclusion - 2 minutes

Benefices a marteler :

- meilleure tracabilite ;
- moins de retraitements manuels ;
- controle avant reporting ;
- explication des ecarts ;
- lien maintenance / energie / finances ;
- meilleure anticipation budgetaire.

Phrase de cloture :

> Po2 est un outil de dialogue entre energie, maintenance et finances : il aide a expliquer la depense, la controler et anticiper son evolution.

## Plan de slides cible

Maximum 9 slides :

1. Titre : piloter les depenses energie.
2. Missions SOEM energie.
3. Une depense multi-sources.
4. Les risques et difficultes actuelles.
5. Positionnement : Power BI / MANTY et Po2.
6. Demo 1 : consommations et indicateurs.
7. Demo 2 : controle factures et rapport comptable.
8. Demo 3 : DALKIA, OS / avenant, impact P2+P3.
9. Conclusion : controler, expliquer, anticiper.

## Elements differenciants a mettre en avant

- Controle avant reporting : Po2 verifie la qualite de la donnee avant exploitation financiere.
- Recalcul facture : comparaison entre montant facture et montant attendu.
- Explication des ecarts : pas seulement un montant different, mais une cause probable.
- Lien site / facture / contrat / matrice / indice / decision de controle.
- Suivi DALKIA adapte aux specificites P1, P2, P3, revision de prix, interessement, penalites, avenants.
- Impact de perimetre DALKIA calcule sur P2 + P3, P1 garde en contexte.
- Production de rapports lisibles pour la comptabilite.
- Support a l'atterrissage budgetaire et au budget N+1.

## Checklist de recette avant reunion

Objectif : tester chaque fonctionnalite que l'on risque de montrer. Ne rien improviser en direct.

### Acces et environnement

- [ ] Verifier l'URL de demo retenue : staging ou production.
- [ ] Verifier compte utilisateur et droits.
- [ ] Verifier temps de chargement des pages principales.
- [ ] Prevoir un navigateur propre avec onglets deja ouverts.
- [ ] Prevoir un plan B : captures d'ecran ou export PDF si la demo live echoue.

### Donnees de synthese

- [ ] Recuperer consommation annuelle gaz.
- [ ] Recuperer consommation annuelle electricite.
- [ ] Recuperer montant annuel energie.
- [ ] Recuperer montant annuel marche DALKIA.
- [ ] Recuperer nombre de sites CPE / hors CPE.
- [ ] Identifier 2 ou 3 chiffres simples a afficher, pas plus.

### Suivi consommations / indicateurs

- [ ] Tester la page de suivi des consommations.
- [ ] Verifier que les filtres periode / fournisseur / marche / site fonctionnent.
- [ ] Verifier au moins un indicateur gaz.
- [ ] Verifier au moins un indicateur electricite.
- [ ] Verifier le lien avec l'atterrissage budgetaire si l'ecran existe.
- [ ] Choisir un exemple parlant mais simple.

### Controle factures energie

- [ ] Tester import ou consultation ENGIE.
- [ ] Tester import ou consultation EDF.
- [ ] Tester import ou consultation TotalEnergies si disponible.
- [ ] Identifier une facture avec ecart explique.
- [ ] Verifier que l'explication est en francais et comprehensible.
- [ ] Verifier que le montant facture et le montant recalcule sont visibles.
- [ ] Preparer un exemple court : une anomalie, une explication, une conclusion.

### DALKIA facture / indices / revision

- [ ] Tester la page formules et indices DALKIA.
- [ ] Verifier les indices du trimestre courant.
- [ ] Verifier les coefficients observes dans les factures.
- [ ] Verifier que P2/P3 et revision de prix sont comprehensibles.
- [ ] Identifier ce qui est suffisamment stable pour etre montre.

### Rapport comptable

- [ ] Generer ou ouvrir un rapport comptable recent.
- [ ] Verifier feuilles ENGIE, EDF, TotalEnergies, DALKIA selon disponibilite.
- [ ] Verifier colonnes strictement utiles.
- [ ] Verifier statuts : rapprochee, ecart, absente plateforme, a controler.
- [ ] Verifier explications courtes des anomalies.
- [ ] Choisir une feuille et une ligne a commenter.

### Matrices comptables

- [ ] Tester la page matrices.
- [ ] Verifier matrice DALKIA.
- [ ] Verifier qu'une nature comptable manquante est comprehensible.
- [ ] Eviter de montrer une fonctionnalite trop technique si elle n'est pas claire.

### OS / avenant DALKIA

- [ ] Tester la page `/refonte-v1/os-avenant`.
- [ ] Tester suppression de site.
- [ ] Verifier colonnes P1, P2, P3, Impact.
- [ ] Verifier que l'impact = P2 + P3 uniquement.
- [ ] Verifier le prorata date d'effet.
- [ ] Verifier la projection par exercice.
- [ ] Verifier l'export Excel d'impact.
- [ ] Tester creation de site avec site comparable.
- [ ] Verifier que P1 reste en contexte et n'entre pas dans l'impact.

### Exports et documents

- [ ] Tester telechargement rapport comptable.
- [ ] Tester telechargement impact OS / avenant.
- [ ] Ouvrir les fichiers telecharges avant reunion.
- [ ] Preparer un export local de secours.

### Parcours de demo final

- [ ] Ouvrir tous les onglets dans l'ordre.
- [ ] Nettoyer les filtres inutiles.
- [ ] Noter les identifiants des factures / sites a montrer.
- [ ] Chronometrer la demo : objectif 8 a 10 minutes.
- [ ] Faire une repetition complete.

## Donnees et exemples a choisir

A completer pendant la preparation :

- Exemple consommation gaz : TODO.
- Exemple consommation electricite : TODO.
- Exemple facture avec ecart : TODO.
- Exemple rapport comptable : TODO.
- Exemple DALKIA OS / avenant : TODO.
- Exemple indice / revision : TODO.

## Questions a trancher avant reunion

- Demo sur staging ou production ?
- Quels chiffres annuels peut-on communiquer sans retraitement supplementaire ?
- Faut-il montrer MANTY / Power BI dans une slide de positionnement, ou seulement le citer oralement ?
- Quels ecrans Po2 sont assez stables pour une demo live ?
- Quels ecrans doivent etre remplaces par captures d'ecran ?
- Souhaite-t-on terminer par une demande explicite : validation d'une methode, soutien au deploiement, priorisation d'une fonctionnalite ?

## Priorites produit avant reunion

A traiter seulement si le temps le permet :

1. Stabiliser les ecrans montres en demo.
2. Verifier les libelles metier : francais, finance-compatible, pas trop technique.
3. S'assurer que les rapports Excel sont lisibles et sobres.
4. Preparer un jeu d'exemples reel mais non confus.
5. Ajouter si possible un lien plus explicite entre consommations et atterrissage budgetaire.

## Script oral court

Introduction :

> Je souhaite vous montrer comment le service energie peut contribuer a fiabiliser le suivi financier des depenses energie. L'objectif n'est pas de remplacer les vues finance existantes, mais d'apporter une couche de controle metier, d'explication des ecarts et d'anticipation.

Transition vers demo :

> Je vais volontairement montrer peu d'ecrans, mais des ecrans qui illustrent la chaine complete : consommation, facture, controle, comptabilite, puis anticipation DALKIA.

Conclusion :

> La valeur de Po2 est de relier la donnee technique et la donnee financiere. Cela permet de mieux comprendre ce qui est paye, pourquoi cela varie, et quel impact anticiper sur le budget.
