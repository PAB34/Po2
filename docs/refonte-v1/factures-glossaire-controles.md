# Factures & décisions — comprendre les contrôles

> Document d'aide à destination de la comptable (et de toute personne qui reprend la page `/refonte-v1/factures`).
> Objectif : expliquer en langage clair **chaque état d'une facture** et **quoi faire** dans chaque cas.
> Page concernée : file unique DALKIA (CPE) + ENGIE + EDF.

## L'idée générale

Chaque facture importée passe par un **moteur de contrôle** automatique. Ce moteur ne décide pas à votre place : il **prépare le travail** en classant ce qu'il trouve. Vous gardez la main sur la **décision** (valider / refuser / contester).

Il y a donc **deux axes distincts** :

| Axe | Valeurs | Qui décide |
|---|---|---|
| **Résultat du contrôle** (moteur) | OK · Écart · À expliquer · Bloquée · Expliquée | automatique |
| **Décision** (humain) | À contrôler · Validée · Refusée · Contestée | vous |

Une facture « tout vert » au contrôle passe **automatiquement** en « Validée » (voir plus bas). Tout le reste attend votre décision.

## Les états de contrôle, un par un

### 🟢 OK / Sans écart
Le moteur n'a rien trouvé à signaler : montants cohérents, périodes continues, prix conformes.
- **Action :** aucune. La facture est **auto-validée**.

### 🟡 Écart
Un **vrai écart de facturation chiffré** : le montant facturé ne correspond pas à ce qui était attendu.
- **Exemples :** total de la facture ≠ somme des lignes ; prix unitaire ≠ bordereau (BPU) ; TVA incohérente ; prix P1 gaz ≠ prix OS n°3 attendu.
- **Action :** examiner, et si l'écart est avéré, le **signaler au fournisseur**.

### 🟠 À expliquer (anomalie)
Le moteur a détecté quelque chose d'**anormal mais non chiffré comme un écart de prix** : il manque une explication.
- **Exemple principal — trou de facturation :** entre deux factures d'un même point (PRM), une période n'est pas couverte (ex. fin 30/11/2025 → reprise 02/02/2026 : décembre et janvier manquent).
  - L'énergie se facture **en continu**. Un trou veut dire soit qu'une **facture de rattrapage n'est pas encore arrivée** (elle comblera le trou plus tard), soit qu'elle **ne viendra jamais** (oubli fournisseur).
  - **Action :** vérifier si une facture ultérieure couvre la période ; sinon, **réclamer au fournisseur**.

### 🔴 Bloquée
Le contrôle **n'a pas pu être fait** : il manque une donnée de référence ou une donnée externe.
- **Exemples :** PRM hors du référentiel chargé ; bordereau (BPU) non configuré ; nature comptable manquante (CPE) ; totaux HT/TVA incomplets.
- **Important :** une donnée externe absente **n'est jamais** un écart de facturation. C'est « à compléter », pas « la facture est fausse ».
- **Action :** compléter la donnée manquante (référentiel, matrice comptable) puis **recalculer**.

### 🟢 Expliquée (neutralisée)
Le moteur a d'abord vu quelque chose de suspect, **puis a trouvé une raison légitime** : ce n'est plus une anomalie, c'est **non bloquant**.
- **Exemples :**
  - **Transition fournisseur** EDF → ENGIE : le « trou » au 1er janvier est normal (changement de contrat), pas un manque de facturation.
  - **Doublon exact** : réédition / export fournisseur du même fichier, sans impact de période.
  - **Avoir / annulation / refacturation** : régularisation expliquée.
  - **Ligne fixe sans consommation** (abonnement seul) : contrôle de période non applicable.
- **Action : AUCUNE.** Une anomalie expliquée **n'a pas besoin de contrôle**. Elle est affichée pour transparence, mais ne bloque rien.

## Auto-validation : que se passe-t-il tout seul ?

Quand une facture est **100 % propre** (aucun écart, aucune anomalie à expliquer, aucun blocage — les éléments « expliqués » ne comptent pas), elle passe **automatiquement** en décision **« Validée »**.

- Cela ne s'applique **que** si vous n'avez **pas déjà** pris une décision : une facture que vous avez validée, refusée ou contestée à la main n'est **jamais** écrasée.
- Côté DALKIA/CPE comme côté énergie (ENGIE/EDF).

## Une question de dates

Les factures portent **deux dates importantes** :

- **Date d'émission** (« Date d'édition » chez ENGIE, « date facture » chez EDF) : quand la facture a été produite.
- **Période de consommation** (début → fin) : à quoi correspond réellement la dépense.

Ces deux dates **ne coïncident pas toujours**. Une facture **émise en mars 2026** peut concerner une **consommation d'octobre à décembre 2025** (facturation tardive). C'est fréquent et **normal** : on l'**affiche** (« conso oct → déc 2025, émise mars 2026 ») mais ça **ne bloque pas**.

- Le **graphique « Charge annuelle »** classe les factures par **mois d'émission** (« quand est-ce arrivé »).
- Le **bouton année** (en haut à droite du graphique) évite de mélanger les années.
- **Cliquer sur un mois** du graphique filtre le tableau sur ce mois.

## Cas particulier : dépassement de puissance

Un « dépassement de puissance facturé » est une **pénalité réelle** : le site a tiré plus que sa **puissance souscrite**, le distributeur facture un supplément.

- Ce **n'est pas** une anomalie de facturation à trancher ici : c'est un montant légitime (ou le signe qu'il faudrait revoir l'abonnement à la hausse).
- Il **n'est donc plus affiché** sur cette page. Le calcul reste fait côté moteur et sera **réutilisé dans la future section Fluides** (suivi des puissances / optimisation des abonnements).

## En résumé : que dois-je traiter ?

| État | Faut-il agir ? |
|---|---|
| OK / Expliquée | Non (auto-validée ou neutralisée) |
| Écart | Oui — examiner, signaler au fournisseur si avéré |
| À expliquer | Oui — vérifier le trou, réclamer si la période reste non facturée |
| Bloquée | Oui — compléter la donnée manquante, puis recalculer |
