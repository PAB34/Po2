# Factures & décisions V1 — décisions UX & contrôles (fichier de travail partagé)

> **À quoi sert ce fichier**
> Fichier commun, tenu à jour par Claude, pour la refonte de la page `/refonte-v1/factures`.
> Il recense **tous les contrôles / écarts** affichés, par **tiers facturant**, leur traitement
> décidé, et **toutes les questions ouvertes** à trancher avec Pierre‑André pour que l'interface
> reflète exactement ses attentes. Une ligne = un sujet. On édite ici **avant** de coder.
>
> Convention de verdict cible :
> - **A — Écart réel** : anomalie de facturation exploitable → badge rouge « ÉCART », compté en *Écarts*.
> - **C — Non contrôlable** : référence/donnée manquante côté plateforme → badge « N/C », compté en *Bloqués*.
> - **I — Info / alerte** *(à créer)* : information pertinente mais ni écart ni bloquant → discret (ex. triangle orange en bout de ligne), **non compté** en Écarts ni en Bloqués.
> - **Supprimé** : le contrôle n'est plus émis du tout.
>
> Page : [InvoicesDecisionPageV1.tsx](../../saas/frontend/src/features/invoices/InvoicesDecisionPageV1.tsx) ·
> Moteur énergie : [invoice_analysis.py](../../saas/backend/app/services/invoice_analysis.py) ·
> Moteur CPE : [cpe_accounting.py](../../saas/backend/app/services/cpe_accounting.py)

---

## 1. Décisions déjà prises (historique)

| Date       | Sujet                                                               | Décision                                                                            | Commit        |
| ---------- | ------------------------------------------------------------------- | ----------------------------------------------------------------------------------- | ------------- |
| 2026‑06‑28 | Faux écarts EDF (PRM/BPU)                                           | Reclassés « non contrôlable » (set `NON_CONTROLABLE_CODES` élargi)                  | `7c90158`     |
| 2026‑06‑28 | Contrôle **TURPE / acheminement**                                   | **Supprimé** (faux positifs, réf. non alignées)                                     | `7c90158`     |
| 2026‑06‑29 | Recalcul EDF (.csv)                                                 | `_recompute_invoice_import` : recontrôle sur le parse stocké si fichier ≠ PDF       | `8eb8e1b`     |
| 2026‑06‑29 | `UNKNOWN_PRM`, `ENEDIS_CONSUMPTION_MISSING`, `ENEDIS_POWER_MISSING` | **Supprimés** (donnée externe absente ≠ écart)                                      | `cea3c89`     |
| 2026‑06‑29 | Contrôle **PUISSANCE** complet (`_check_power_controls`)            | **Supprimé** : « Puissance atteinte… » n'a pas sa place dans le contrôle de facture | _(ce commit)_ |

**Principe directeur validé** : une **donnée externe absente** (référentiel ENEDIS non chargé, courbe de charge, etc.) **n'est jamais un écart de facturation** et ne doit pas bloquer la facture.

---

## 2. Inventaire des contrôles — Fluides (ENGIE / EDF, moteur énergie)

### 2.1 Vrais écarts (A) — à conserver
| Code | Message | Statut |
|---|---|---|
| `BPU_PRICE_MISMATCH` | Prix facturé ≠ prix BPU | A ✅ |
| `BPU_TARIFF_POSTE_INCONSISTENCY` | Prix cohérent mais mauvais poste/tarif | A ✅ |
| `TOTAL_TTC_MISMATCH` | Somme des FIC ≠ total facture | A ✅ |
| `LINE_AMOUNT_MISMATCH` | Ligne incohérente (qté × PU ≠ montant) | A ✅ |
| `VAT_TOTAL_MISMATCH` / `VAT_RECALC_MISMATCH` / `HT_TOTAL_MISMATCH` / `INVOICE_VAT_TOTAL_MISMATCH` | Incohérences HT/TVA/TTC | A ✅ |
| `PERIOD_INVALID` | Période incohérente (fin avant début) | A ✅ |
| `DUPLICATE_INVOICE_NUMBER` | N° de facture déjà importé | A ✅ |
| `MISSING_INVOICE_NUMBER` / `MISSING_TOTAL_TTC` | Donnée d'identité critique absente | A ✅ |
| `SUPPLIER_UNKNOWN` | Fournisseur non reconnu (hors ENGIE/EDF) | A ✅ |

### 2.2 Non contrôlable (C) — référence manquante
| Code | Message | Statut |
|---|---|---|
| `BPU_CONFIG_MISSING` / `BPU_LINES_MISSING` | Aucun BPU configuré | C ✅ |
| `BPU_REFERENCE_MISSING` / `BPU_PRICE_MISSING` | Pas de ligne/prix BPU pour ce tarif | C ✅ |
| `MISSING_MARKET_REFERENCE` / `MARKET_REFERENCE_MISMATCH` | Réf. marché (ENGIE only) | C ✅ |
| `MISSING_PRM` | PRM absent sur un site | C ✅ |
| `SUPPLIER_CONTRACT_MISMATCH` | PRM rattaché à un autre fournisseur ENEDIS | C ✅ |
| `TAX_TOTALS_MISSING` | Totaux HT/TVA/TTC incomplets | C ✅ |
| `MISSING_INVOICE_DATE` / `MISSING_REGROUPEMENT` | Donnée d'entête absente | C ✅ |

### 2.3 Supprimés (plus émis)
| Code | Ancien message | Raison |
|---|---|---|
| `UNKNOWN_PRM` | « PRM inconnu dans les donnees energie » | Donnée externe absente |
| `ENEDIS_CONSUMPTION_MISSING` | « Aucune consommation ENEDIS disponible… » | Donnée externe absente |
| `ENEDIS_POWER_MISSING` | « Aucune courbe de charge ni puissance max ENEDIS… » | Donnée externe absente |
| `TURPE_*` | Écarts d'acheminement | Réf. non alignées, faux positifs |
| `POWER_*` (toute la famille) | « Puissance atteinte… / souscrite / dépassement » | Hors périmètre contrôle facture |

### 2.4 ⚠️ À TRANCHER (actuellement comptés en *Bloqués*, ne devraient pas l'être)
| Code | Message | Situation actuelle | Proposition Claude | **Question** |
|---|---|---|---|---|
| `PERIOD_GAP` | « Trou de facturation detecte sur… » | C (Bloqué) | **I — info**, triangle orange en bout de ligne, non bloquant | Voir §3 Q1 |
| `PERIOD_OVERLAP` | « Chevauchement de periode sur… » | C (Bloqué) | **I — info** (idem PERIOD_GAP) | Voir §3 Q1 |
| `LINE_PERIOD_OUTSIDE_SITE_PERIOD` | « Ligne facturee hors periode FIC… » | C (Bloqué) | **I — info** ? ou supprimé ? | Voir §3 Q2 |
| `CONSUMPTION_REFERENCE_MISSING` | « Consommation facturee ou periode incomplete… » | C (Bloqué) | À clarifier (voir §3 Q3) | Voir §3 Q3 |
| `CONSUMPTION_ENEDIS_MISMATCH` / `CONSUMPTION_LOAD_CURVE_MISMATCH` | Conso facturée ≠ ENEDIS | C | **I — info** (écart d'estimation, pas de facturation) ? | Voir §3 Q4 |
| `ENEDIS_CONSUMPTION_PARTIAL` / `LOAD_CURVE_CONSUMPTION_PARTIAL` | Données ENEDIS partielles | C | Supprimé (bruit) ? | Voir §3 Q4 |

---

## 3. Questions ouvertes (à répondre par Pierre‑André)

**Q1 — `PERIOD_GAP` (trou) & `PERIOD_OVERLAP` (chevauchement).**
Pertinents mais **non bloquants, non écart**. Proposition : nouvelle catégorie **« Info »** affichée par un **triangle orange ⚠️ en bout de ligne** (tooltip au survol), + une section « Informations » dans le tiroir. N'entre ni dans *Écarts* ni dans *Bloqués*.
→ *Ce design te convient‑il ? Le triangle en bout de ligne suffit‑il, ou tu veux aussi un filtre dédié « factures avec trou de période » ?*
Alors ce sont deux vrais sujets qui devront permettre si avéré d'envoyer un mail au contact de ce fournisseur pour explication. J'aimerais quand même que ce soit un sujet qu'on puisse suivre dans le temps avec une représentation graphique. Je pense que le mieux serait qu'à l'image de l'encart affichant le graphique "Charge annuelle", il y ai un graphique en dessous permettant de représenter le nombre de factures ce chevauchant et avec un trou. Peut être alors deux graphiques l'un en dessous de l'autre. Mais quand dans le tiroir de la facture on doit avoir un bouton pour demander des explications sur les écarts et sur ces PERIOD GAP/OVERLAP

**Q2 — `LINE_PERIOD_OUTSIDE_SITE_PERIOD`** (« ligne facturée hors période FIC »).
→ *Info comme Q1, ou suppression pure ?*
Je ne sais pas ce qu'est la période FIC, c'est quoi ? Et que représente cette anomalie ?

> **Réponse Claude (FIC) :** dans l'export, **chaque ligne = un site (FIC) pour une période**.
> Un « FIC » est le **numéro de facture individuelle de ce point de livraison** (ENGIE : champ
> « N° Facture ou Avoir » ; EDF : `id_contrat`). La « période FIC » = la période de facturation
> de ce site (date début → date fin de conso). L'anomalie `LINE_PERIOD_OUTSIDE_SITE_PERIOD`
> signale qu'**une ligne de détail** de ce site porte des dates **hors** de cette période (ex. une
> régularisation de décembre apparaissant dans la facture de janvier). C'est souvent **légitime**
> (rattrapage / régularisation) → faux positif fréquent.
> **Décision proposée : Supprimé** (bruit), sauf si tu veux le voir en « Info ». → **Q7**

**Q3 — `CONSUMPTION_REFERENCE_MISSING` — explication.**
Ce n'est **pas** un écart de prix. Il se déclenche quand, pour un site, la facture **n'a pas fourni** au moins l'un de : PRM, date de début, date de fin, **ou quantité de consommation** (kWh). Autrement dit : *le parseur n'a pas réussi à extraire une conso pour ce site*. Deux lectures possibles :
  - soit la facture ne porte effectivement pas de conso sur ce site (normal pour certaines lignes) → **à ignorer** ;
  - soit le **parseur** rate l'extraction (vrai sujet **technique**, à corriger côté parsing, pas à afficher comme écart).
→ *Veux‑tu (a) le supprimer de l'affichage, et (b) que je liste à part les sites où la conso n'est pas extraite, pour vérifier si c'est un trou de parsing ?*
Il faut vérifier par toi meme en manuel le parsing et le garder comme bloquant si avéré et devra être intégré au rapport  à fournir au contact du fournisseur pour demande de rectification ete xplication.

> **Vérification Claude (2026‑06‑29) : faux positif systématique côté EDF, corrigé.**
> Le parser EDF (`edf_csv.py`) crée ses lignes via `_line(...)` qui ne porte **qu'un montant € (`amount_ht`),
> jamais de quantité kWh**. Or `_invoice_site_consumption_kwh` ne lisait la conso que depuis la `quantity`
> des lignes ou les relevés → il **ignorait** `total_consumption_kwh` du site (rempli par EDF via
> `conso_elec_facturee_kwh`). Résultat : `CONSUMPTION_REFERENCE_MISSING` se déclenchait sur **toutes**
> les factures EDF alors que la conso est bien là. **Corrigé** (commit `<ce commit>`) : repli sur la conso
> site quand aucune quantité de ligne/relevé. Le contrôle ne reste donc bloquant que si la conso est
> **réellement** absente (vrai sujet → à intégrer au rapport fournisseur). ✅

**Q4 — Rapprochement conso ENEDIS** (`CONSUMPTION_ENEDIS_MISMATCH`, partiels).
C'est une comparaison conso facturée vs relevés ENEDIS (donnée externe, estimative).
→ *On garde en simple « Info », ou on supprime tout le rapprochement conso comme on l'a fait pour la puissance ?*
A supprimer mais cette anomalie rentrera dans une nouvelle section "Anomalie"

**Q5 — Dépassement de puissance réellement FACTURÉ.**
En supprimant la famille puissance, on a aussi retiré `POWER_OVERRUN_BILLED` qui détectait une **ligne de dépassement facturée en €**. C'était le seul contrôle puissance touchant un vrai montant.
→ *On le laisse supprimé, ou tu veux le réintroduire comme écart réel (A) « dépassement de puissance facturé : X € » ?*
A supprimer mais cette anomalie rentrera dans une nouvelle section "Anomalie"

---

## 4. Marché DALKIA (moteur CPE) — à passer en revue

Le moteur CPE distingue déjà nativement `ok` / `error` / `blocked`. À revoir ensemble si certains
`error` doivent devenir « Info », ou si des `blocked` polluent.

| control_type | Verdicts produits | À discuter ? |
|---|---|---|
| `invoice_total_ht` | ok / error | — |
| `invoice_period` / `invoice_timeline` / `invoice_type` | ok / error / blocked | timeline : dates édition/échéance, bloquant ? |
| `p1_gaz_pu_os3` / `p1_gaz_acompte_dpgf` / `p2p3_base_dpgf` | ok / error (/ blocked) | écart de révision = normal (cf. mémoire P1 DPGF) → Info ? |
| `revision_p2` / `revision_p3` / `p2_4_objectives` | ok / error / blocked | — |
| `accounting_nature` / `accounting_site` | ok / blocked | imputation comptable manquante = bloquant légitime ? |

**Question DALKIA (Q6)** : *passe‑t‑on en revue ces contrôles maintenant, ou après avoir figé les fluides ?* On passe en revue les fluides déjà et après on contrôle tout

---

## 5. SPIE & SUEZ (à venir)

Sources à ajouter (cf. backlog). À l'ajout, **repartir de ce tableau** : pour chaque contrôle,
décider A / C / I / Supprimé / Anomalie **par tiers**, car le périmètre diffère (ex. SPIE = maintenance CVC,
SUEZ = eau). Section à compléter quand les parseurs seront branchés.

---

## 6. Synthèse des réponses (2026‑06‑29) → nouveau modèle à 4 catégories

Tes réponses font émerger une **4ᵉ catégorie** en plus de Écart / Bloqué / OK :

> **« Anomalie »** — un fait avéré qui n'est pas une erreur de prix exploitable directement, mais
> qui justifie de **demander une explication au fournisseur** et de **se suivre dans le temps**.
> Affichage : badge/section dédiés, **suivi graphique**, et **bouton « Demander des explications »**
> dans le tiroir (mail pré‑rempli au contact du fournisseur). Ni « Écart » ni « Bloqué ».

**Décisions enregistrées :**

| Sujet | Décision |
|---|---|
| `PERIOD_GAP` (trou) / `PERIOD_OVERLAP` (chevauchement) | → **Anomalie**. Vrais sujets, non bloquants. Suivi par **graphique sous « Charge annuelle »** (2 graphes empilés : nb factures avec trou / avec chevauchement). Bouton « Demander des explications » dans le tiroir. |
| `CONSUMPTION_ENEDIS_MISMATCH` + `CONSUMPTION_LOAD_CURVE_MISMATCH` | → **Anomalie** (retirés des « Bloqués »). |
| `ENEDIS_CONSUMPTION_PARTIAL` / `LOAD_CURVE_CONSUMPTION_PARTIAL` | **Supprimés** (bruit). |
| `POWER_OVERRUN_BILLED` (dépassement puissance **facturé €**) | Réintroduit **en Anomalie** (le reste de la famille puissance reste supprimé). |
| `CONSUMPTION_REFERENCE_MISSING` | Faux positif EDF **corrigé** (repli conso site). Reste **Bloquant** uniquement si conso réellement absente → à intégrer au **rapport fournisseur**. |
| `LINE_PERIOD_OUTSIDE_SITE_PERIOD` | Proposé **Supprimé** (cf. Q7). |
| DALKIA | On finit les fluides d'abord, puis revue complète (Q6 ✅). |

**Le tiroir d'une facture aura donc :** Écarts (A) · Non contrôlable/Bloqués (C) · **Anomalies** (nouveau) · + bouton **« Demander des explications »** (mail pré‑rempli) couvrant écarts ET anomalies.

### Questions de suite (avant de coder la section Anomalie)

**Q7 —** `LINE_PERIOD_OUTSIDE_SITE_PERIOD` : on **supprime** (reco) ou on le met en Anomalie ?
Alors je comprends mieux il ne faut pas le supprimer ni en anomalie. Si je comprends bien ca peut être "rattrapage / régularisation", c'est à dire si il y a un chevauchement ou un trou de facturation cela peut être rattrapé dans cette facture ? Si c'est bien le cas alors ce serait intéressant que si le détail existe sur ce "rattrapage / régularisation" d'avoir les informations précises de la période concernés car cela peut résoudre un problème de chevauchement ou un trou de facturation. Donc la question queje me pose c'est est-ce qu'un chevauchement ou un trou de facturation doit être mis en "Anomalie", j'ai besoin de ton avis et de propositions.

**Q8 — Mécanisme « Demander des explications ».** Tu avais aussi demandé « Préparer une réclamation »
(pré‑rempli, **sans envoi**). Est‑ce le **même** bouton (un seul courrier qui couvre écarts + anomalies),
ou deux actions distinctes ? Et l'envoi : **`mailto:` pré‑rempli** (s'ouvre dans ta messagerie, tu
valides/envoies) — recommandé pour commencer — ou **envoi automatique depuis la plateforme** (nécessite
SMTP + annuaire des contacts fournisseurs) ?
Oui on avait dit pour commencer "**`mailto:` pré‑rempli** (s'ouvre dans ta messagerie, tu
valides/envoies) — recommandé pour commencer" mais c'est un sujet, car il faut penser que des factures auront été traiter et que dans cette nouvelle section il faut pouvoir traiter que les factures qui sont en statut "Contestée". D'ailleurs question est-ce que le statut refusée" à lieur d'être car avant de la refuser ne faut-il pas la contester ? J'ai besoin de ton avis et de propositions

**Q9 — Contacts fournisseurs.** Pour pré‑remplir le mail, il faut un **annuaire** (contact ENGIE / EDF /
DALKIA…). Tu as ces emails quelque part (fichier, doc) ou je prévois une page de paramétrage pour les saisir ? Oui prévoir une page paramètre du marché pour saisir les noms, prénoms, adresse mail, entreprise, rôle des contacts

**Q10 — Graphiques de suivi.** Confirmes‑tu : **2 graphiques empilés** sous « Charge annuelle »
(1 = nb factures avec **trou** de période / mois, 2 = nb avec **chevauchement** / mois) ? Périmètre =
le portefeuille filtré courant ? Et plus tard un 3ᵉ pour les autres anomalies (conso/puissance) ?
La question n'est pas réglé tant que tu ne m'auras pas répondu à la question **Q7. Tu devras certainement faire une recherche en manuel pour confirmer ou non. Rappel 
ENGIE : "C:\Users\pa.borja\Documents\Po2\saas\energie\ENGIE\FACTURES\MesFactures_20260609132103.xlsx"
EDF "C:\Users\pa.borja\Documents\Po2\saas\energie\EDF\20260612_141002814868_EDF160626.csv"

### Ordre d'implémentation proposé
1. **(fait)** Corriger faux positif conso EDF + retraits déjà actés.
2. Introduire la **catégorie « Anomalie »** (backend : marquer ces codes ; frontend : bucket + section tiroir + colonne/badge), **sans** mail ni graphes → débloque les factures.
3. **Graphiques de suivi** trou/chevauchement.
4. **Bouton « Demander des explications »** (mailto pré‑rempli) + annuaire contacts.
5. Revue **DALKIA**, puis **SPIE/SUEZ**.

---

## 7. Analyse des données réelles (2026‑06‑29) + propositions Claude

J'ai inspecté les vrais fichiers (`saas/energie/EDF/…csv` 489 lignes, `…ENGIE/…xlsx`).

### 7.1 Constat trou/chevauchement (EDF, 363 PRM)
- **0 trou**, **55 « chevauchements » bruts**.
- Après neutralisation des **avoirs** (33 lignes négatives, toutes avec `numero_facture_annulee`) et des factures annulées : **1 seul vrai chevauchement de périodes différentes** + 21 **doublons de période exacte** (réémissions).
- Exemple type (PRM CONSERVATOIRE) : facture +345,62 € → **avoir −345,62 €** → re‑facture 345,46 € → doublon 345,46 €, **tous sur la même période 10→31/12**. Ce n'est pas un chevauchement de cycles, c'est le **mécanisme facture / avoir / refacturation** d'EDF.
- ENGIE expose la même logique (colonne « N° Facture **ou Avoir** »).

➡️ **Conclusion : le contrôle PERIOD_OVERLAP brut est ~98 % de bruit.** Il faut d'abord **neutraliser avoirs + factures annulées + doublons exacts**, *puis* détecter les trous/chevauchements résiduels.

### 7.2 Réponse Q7 (régularisation / `LINE_PERIOD_OUTSIDE_SITE_PERIOD`)
- Ton intuition « rattrapage / régularisation » est **juste**, mais elle ne passe **pas** par `LINE_PERIOD_OUTSIDE_SITE_PERIOD` (qui ne se déclenche jamais sur EDF — pas de période par ligne). Le rattrapage se matérialise par **avoir + refacture** (EDF : `numero_facture_annulee`).
- **Proposition Claude :**
  1. `LINE_PERIOD_OUTSIDE_SITE_PERIOD` → **Supprimé** (faux signal).
  2. **Oui, mettre trou/chevauchement en « Anomalie »**, MAIS sur données **nettées** (hors avoirs/annulées/doublons). Un trou ou chevauchement *résiduel* est alors un vrai sujet fournisseur.
  3. Dans le tiroir, afficher la **chaîne de correction** (« facture X annule/remplace Y, même période ») → c'est l'info précise de période que tu voulais, et ça **explique** le pseudo‑chevauchement.

### 7.3 Réponse Q8 (workflow de statuts — mon avis)
Ton intuition est bonne : **on conteste avant de refuser**. Proposition de cycle :
- `À contrôler` → **`Validée`** (rien à signaler) **ou** `Contestée` (on demande explication).
- `Contestée` → **`Validée`** (explication reçue, OK) **ou** **`Refusée`** (rejet définitif, avoir attendu).
- Donc **`Refusée` n'est plus un choix direct** : c'est un **état terminal accessible uniquement depuis `Contestée`**.
- Le bouton **« Demander des explications »** = action unique qui (a) génère le **mailto pré‑rempli** (écarts + anomalies), (b) passe la facture en **`Contestée`**. C'est **le même** que « Préparer une réclamation » (un seul courrier).
- La **section de suivi** liste les factures **`Contestée`** (relances, réponses).
→ *Valides‑tu ce cycle à 3 états (À contrôler / Validée / Contestée→Refusée) ?*

### 7.4 Réponse Q9 (contacts) ✅
Page **« Paramètres du marché »** pour saisir les contacts : nom, prénom, email, entreprise, rôle.

### 7.5 Réponse Q10 (graphiques)
OK pour 2 graphiques empilés sous « Charge annuelle » (trou / chevauchement par mois, périmètre filtré) — **mais alimentés par les compteurs NETTÉS** (sinon 55 faux vs 1 vrai). 3ᵉ graphe conso/puissance plus tard.

### 7.6 Nouvelles questions
**Q11 —** Valides‑tu le principe « **netter avoirs/annulées/doublons avant de détecter trou/chevauchement** » ? (sinon les graphes et la section Anomalie seront illisibles)
OUI
**Q12 —** Les **doublons de période exacte** (réémissions sans avoir) : on les traite comme doublons (masqués par « Purger les doublons ») ou comme une anomalie « réémission » à tracer ?
Si j'ai bien compris le FIC est un numéro individuel de facturation et ne doit plus jamais exister en double ? Si c'est le cas alors nous ici une solution pour traiter automatiquement (si 2 FIC identique) comme doublon et donc purger automatiquement et statut contester, on est d'accord ou je dis une ânerie ? Si classer comme contester alors anomalie ...

> **Réponse Claude (Q12) — attention, deux notions différentes :**
> Vérification sur le fichier réel EDF (489 lignes) :
> - `num_facture` n'est **pas** unique par site : **81 numéros distincts** pour 489 lignes. Un `num_facture` EDF est une **facture groupée** couvrant **plusieurs PRM**. Donc « un FIC ne doit jamais exister en double » n'est **pas** vrai littéralement : un même site apparaît normalement dans plusieurs factures groupées au fil du temps.
> - Le champ qu'on a appelé « FIC » côté EDF = `id_contrat` = l'**identifiant du site/contrat** (se répète, c'est normal).
>
> **Il faut distinguer 2 cas :**
> 1. **Vrai doublon d'import** = la **même facture groupée** (même `num_facture` / même document) réimportée. → **purge automatique** (hygiène d'import, aucune contestation, pas d'anomalie). C'est ce que fait déjà « Purger les doublons ».
> 2. **Même site + même période facturés dans DEUX factures groupées différentes** (montant identique, `num_facture` ≠) — **22 cas** dans le fichier. Ce **n'est pas** un doublon d'import : c'est potentiellement une **double facturation** (risque de payer 2×) **ou** une réémission qu'EDF aurait dû annuler par avoir. → **Anomalie « double facturation »** à **vérifier humainement**, pas à purger ni à contester automatiquement.
>
> **Reco :**
> - **Ne pas auto‑contester** : la contestation reste une décision humaine (sinon on spamme le fournisseur sur des faux positifs). La plateforme **signale**, la comptable **décide** puis clique « Demander des explications ».
> - Auto‑purge **uniquement** pour le cas 1 (document identique). Le cas 2 → **Anomalie** (la plus utile : elle attrape les vraies doubles facturations).
> → *D'accord avec cette distinction ? (auto‑purge = document identique seulement ; même site/période sur 2 factures = anomalie à valider, pas auto‑contestée)*

### 7.7 Décisions verrouillées pour la phase 2
- Q11 ✅ **netter** avoirs/annulées/doublons‑document **avant** de détecter trou/chevauchement.
- Cycle de statuts : `À contrôler → {Validée | Contestée}`, `Contestée → {Validée | Refusée}`. `Refusée` non accessible directement.
- Catégorie **Anomalie** = trou/chevauchement (nettés) + écart conso/ENEDIS + dépassement puissance facturé + **double facturation** (cas 2 ci‑dessus). Non bloquante, non écart.
- `LINE_PERIOD_OUTSIDE_SITE_PERIOD`, `*_PARTIAL` conso → **supprimés**.