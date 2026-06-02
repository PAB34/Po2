# Guide utilisateur — Moteur DALKIA : ce que ça fait et comment le tester

tags: #CPE #DALKIA #guide #utilisateur #test

> Objectif : comprendre, sans connaitre le code, ce que le moteur DALKIA apporte et **comment le
> tester pas a pas dans l'interface**. Date : 2026-06-02.

---

## 1. A quoi sert le moteur DALKIA (en une phrase)

Il transforme **le fichier Excel d'acte d'engagement DALKIA** (Lot 1 / Lot 2) en un **référentiel
contractuel** dans la plateforme, puis s'en sert pour **contrôler automatiquement les factures**
(le prix facturé est-il conforme au contrat ?) et **piloter la performance énergétique** (cibles NB).

Deux grands volets :
- **Volet contrôle de factures** : compare ce que DALKIA facture aux montants/prix du contrat.
- **Volet performance (intéressement)** : suit les consommations gaz vs les cibles contractuelles (NB).

---

## 2. Ou ça se trouve dans l'interface

| Écran | Adresse | Rôle |
|---|---|---|
| Import du référentiel | `/cpe/dalkia-import` | Charger le fichier Excel DALKIA, le prévisualiser, le confirmer |
| Tableau de bord CPE | `/cpe` | Bilan de performance (cibles NB), suivi financier, contrôles de factures |
| Fiche d'un site | `/cpe/sites/:id` | Détail d'un site CPE |

Dans la nouvelle navigation : **Marchés et contrats → CPE DALKIA**.

---

## 3. Parcours de test pas a pas

### Étape 1 — Importer le référentiel DALKIA

1. Va sur **`/cpe/dalkia-import`**.
2. Choisis le fichier Excel (ex. `...L1_AE_ANNEXES_OFFRE_FINALE.xlsx`), indique le **Lot** (1 = écoles/sport, 2 = piscines).
3. Clique **« Analyser »** (rien n'est encore enregistré).

**Ce que tu dois voir** : un **aperçu classifié** avec des compteurs (nb sites, P2/P3, cibles, P1, APE, RECAP)
et **6 onglets** :
- **P2 / P3** : montants de maintenance et travaux par site et par année.
- **Cibles GAZ / ELEC** : la cible de consommation (NB) par site et par année.
- **P1 gaz** : prix du gaz par site + une table **composants & coefficients de révision Pu** (vérifie : la somme a+b+c+d+e = 1 par tarif).
- **BPU travaux** : le catalogue des prix unitaires de travaux (prestations `ENT/ENR/T/C/AM`, 7 taux horaires, coefficients).
- **Travaux APE** : les travaux d'amélioration (montant, gain, CO₂).
- **RECAP financier** : le bilan global du marché (bilan total, redevances P1/P2/P3 par année).

4. Si l'aperçu est cohérent, clique **« Confirmer l'import »**.

**Résultat attendu** : l'import apparait dans **« Historique des imports »** avec le badge **● Actif**.
L'import précédent du même lot passe inactif (conservé pour audit).

> 💡 À tester : ré-importe une 2ᵉ fois → l'ancien devient inactif, le nouveau devient actif.

### Étape 2 — Initialiser les sites CPE

> À faire **après** un import (et après chaque avenant). Ce n'est pas automatique.

1. Toujours sur `/cpe/dalkia-import`, clique **« Initialiser / mettre à jour les sites CPE »**.

**Résultat attendu** : un message vert `✓ N sites CPE synchronisés (X créés, Y mis à jour)`.
Cela crée les sites du volet performance à partir du référentiel (code, nom, catégorie, NB, tarif, PCE).

### Étape 3 — Vérifier le bilan de performance

1. Va sur **`/cpe`** (tableau de bord CPE), section bilan.

**Ce que tu dois voir** : la liste des sites avec, par site :
- **NB année** : la cible de consommation gaz de l'année + un **badge** :
  - **`DLK` (vert)** = NB lu depuis le contrat DALKIA importé (l'état normal) ;
  - **`SITE` (orange)** = repli (aucune cible DALKIA trouvée pour ce site/année).
- **N'B corrigé** (NB ajusté du climat réel), **NC réel** (consommation réelle), **écart**, **résultat** (intéressement / pénalité), **montant**.

> 💡 À tester : tous les sites gaz doivent être en **DLK vert**. Un `SITE` orange sur un site censé
> être au marché = un **code site désaligné** à corriger (voir §5).

### Étape 4 — Contrôler les factures DALKIA

> Les contrôles s'exécutent sur les factures importées (export finances DALKIA). Sur `/cpe`, section
> **« Contrôle factures »**.

Les contrôles automatiques ajoutés par le moteur :

| Contrôle | Ce qu'il vérifie | Statuts |
|---|---|---|
| **Acompte P1 vs DPGF** | L'acompte trimestriel gaz = 1/4 du P1 annuel contractuel | ok / écart / bloqué |
| **Base P2/P3 vs forfait DALKIA** | Le forfait P2/P3 facturé (par site et poste) = le forfait du contrat | ok / écart / bloqué |
| **Prix unitaire gaz vs OS N°3** | Le prix du gaz facturé = le prix fixe OS N°3 du tarif du site (2026-2030) | ok / écart / bloqué |

**Comment lire un statut** :
- **ok** : conforme au contrat.
- **écart (erreur)** : le montant facturé ne correspond pas au contrat → **à vérifier avec DALKIA**.
- **bloqué** : le contrôle n'a pas pu se faire (souvent un code site non rattaché) → voir §5.

> 💡 À tester : ouvre une facture gaz/maintenance, regarde les contrôles. Exemple réel détecté par
> le moteur : **CCAS 04, P3.4 2026 — facturé 13 216 € vs contractuel 14 641 €** (un vrai écart).

### Étape 5 — Synchroniser la référence d'acompte P1 (optionnel)

Sur `/cpe/dalkia-import`, sur l'import actif, le bouton **« Synchroniser la réf. P1 »** met à jour le
montant de référence du contrôle d'acompte P1 à partir du RECAP du marché (le fichier fait foi).

---

## 4. Récapitulatif : quoi tester, où, résultat attendu

| Fonctionnalité | Où | Action | Résultat attendu |
|---|---|---|---|
| Import référentiel | `/cpe/dalkia-import` | Analyser puis Confirmer | Import actif, aperçu 6 onglets |
| Aperçu coefficients P1 | aperçu, onglet P1 gaz | regarder | somme a+b+c+d+e = 1 par tarif |
| Catalogue BPU travaux | aperçu, onglet BPU travaux | regarder | prestations + taux horaires + coefficients |
| Sites CPE | `/cpe/dalkia-import` | bouton « Initialiser les sites CPE » | message ✓ N sites |
| Bilan performance | `/cpe` | regarder colonne NB année | badges DLK verts (SITE orange = à corriger) |
| Contrôle factures | `/cpe` > Contrôle factures | ouvrir une facture | statuts ok / écart / bloqué |
| Référence P1 | `/cpe/dalkia-import` | bouton « Synchroniser la réf. P1 » | message de mise à jour |

---

## 5. Ce qui n'est PAS encore dans l'interface (limites actuelles)

À savoir pour ne pas chercher en vain — ces gestes restent à construire (cf. [[../../09-Vision-produit-et-navigation-UX]] §13) :

- **Recalcul des contrôles** : pas encore de bouton ; le recalcul est déclenché côté technique.
- **Console de rapprochement des codes site** : quand un code de facture ne correspond à aucun site
  du référentiel (badge `SITE` orange / contrôle `bloqué`), il n'y a pas encore d'écran pour le corriger.
  Aujourd'hui le désalignement est **signalé**, pas **corrigeable**.
- **Re-consultation des données persistées** après confirmation (P2/P3, cibles, P1, APE, RECAP, BPU) :
  l'aperçu existe avant confirmation, mais pas de ré-affichage depuis la base.

---

## 6. Règle de conception (pour la suite)

> Toute opération qui nécessite une intervention technique (SQL/SSH) doit devenir un **geste dans
> l'interface**. À chaque nouvelle capacité du moteur, on prévoit le bouton/écran correspondant.

## 7. Liens

- [[17-Referentiel-DALKIA-Import]] — détail technique du référentiel et des connexions
- [[../../08-Inventaire-fonctionnalites-developpees-2026-06-02]] — inventaire complet + état prod
- [[../../09-Vision-produit-et-navigation-UX]] — navigation cible et backlog d'opérabilité
- [[12-OS3-Prix-gaz]] — prix gaz et formule de révision
