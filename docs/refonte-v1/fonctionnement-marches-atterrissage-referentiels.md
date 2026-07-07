# Fonctionnement — Marchés, atterrissage électrique, référentiels & indices

> Documentation **explicative** (business-readable) des fonctionnalités travaillées lors de la session
> 2026-07-07. Objectif : **pouvoir donner des explications** sur ce que fait la plateforme, sans lire le
> code. Périmètre = uniquement les sujets de cette session. Écrans concernés : `/refonte-v1/referentiels`,
> `/refonte-v1/marches`.

---

## 1. Hub « Référentiels marchés » (`/refonte-v1/referentiels`)

**À quoi ça sert** : un point d'entrée unique pour consulter les **référentiels de prix contractuels** des
marchés, sans réécrire les outils existants. Deux sous-onglets :

- **DPGF DALKIA (CPE)** : le « dossier de marché » DALKIA (état en vigueur + journal des actes, moteur de
  diff entre versions). Page déjà complète, **embarquée telle quelle** (pas de refonte : elle est déjà
  cohérente, la refaire n'apporterait qu'un gain cosmétique pour un vrai risque).
- **BPU Hérault Énergies** : les Bordereaux de Prix Unitaires du marché groupé d'électricité (et gaz).
  Vue **curée** en 2 sous-onglets :
  - **Consultation** : quels BPU sont en vigueur (fournisseur × année × lot × avenant), + détail des prix
    par composante au clic.
  - **Évolution** : graphe historique des prix.
  - L'admin (import, édition) est repliée derrière un bouton « Gérer » ; la pédagogie est en infobulle.

**Pourquoi on ne voit pas TotalEnergies ici** : la liste des fournisseurs affichés = ceux **présents dans
les BPU chargés**. Le BPU **gaz TotalEnergies (Lot 7)** n'est pas chargé en base (le script d'import
électricité ne sait pas parser les lignes gaz — elles ressortent en « INCONNU » sans prix). Pour l'afficher,
il faut un **import gaz dédié** (chantier à part).

---

## 2. Atterrissage électrique (`/refonte-v1/marches` → ENGIE / EDF → « Atterrissage »)

**Ce qu'est l'atterrissage** : une **estimation du coût de fin d'année** d'un marché, par point de livraison
(PRM). Formule générale, par PRM :

> **Atterrissage = réalisé à date (factures déjà reçues) + reste de l'année projeté.**

Chaque facture est décomposée en **part fixe** (abonnement, gestion, comptage, CTA, TURPE fixe) et **part
variable** (consommation × prix). Le « reste projeté » = **consommation mensuelle attendue × prix de
référence** sur les mois non encore facturés.

- **Consommation attendue** :
  - **ENGIE** (bâtiments) : historique **ENEDIS N-1** corrigé du climat, mais **seulement sur la part
    thermosensible** (chauffage/clim) — la base (éclairage, bureautique…) n'est pas corrigée du DJU.
  - **EDF** (éclairage public) : conso N-1 reconduite, répartie sur l'année selon la **photopériode**
    (heures de nuit, plus l'hiver) — pas de correction climat (l'éclairage n'est pas thermosensible).

- **Prix de référence variable** = fourniture (énergie) + réseau (TURPE) + taxes. Voir §3 pour la
  **révision** du prix.

**« Prévision de référence »** affichée = un **repère** (conso attendue × prix de référence sur l'année),
pas un budget officiel. L'**écart atterrissage − référence** indique si on est au-dessus/en-dessous de ce
repère (surconsommation ou dérive de prix).

### 2.1 Révision du prix par **typologie du marché Hérault Énergie** (pas par fournisseur)

Point **fondamental** : le prix de fourniture vient du **marché groupé Hérault Énergie**, indexé par
**typologie d'abonnement** (classe tarifaire ENEDIS), **pas par le fournisseur qui facture**. ENGIE, EDF,
TotalEnergies ne sont que l'**attributaire** du lot pour une année donnée (le nouveau marché 2026 = ENGIE
+ EDF + TE ; l'ancien = EDF + TE).

- **Typologies (classes ENEDIS)** : `HTA` = C1/C2/C3 (haute tension) · `BT > 36 kVA` = C4 · `BT ≤ 36 kVA`
  = C5 (bâtiments) · éclairage public.
- La **révision** compare le prix de fourniture de l'**année Y** à celui de l'**année N-1** pour la **même
  typologie**, quel que soit le fournisseur attributaire. C'est ce qui permet de comparer « ENGIE 2026 »
  à « EDF 2025 » pour un même abonnement quand l'attributaire a changé.
- Sur l'indicateur : « **BPU appliqué (n/n PRM)** » = la révision est bien calculée. S'il est indisponible
  (un seul millésime, segment non couvert), le prix est **tenu au niveau du N-1 réel** (mention explicite ;
  chiffres justes, révision non chiffrée).

### 2.2 Budget de référence quand un marché **n'a pas d'historique** (ex. ENGIE démarré en 2026)

Problème : la « prévision de référence » était bâtie sur les **factures de l'année précédente**. Or ENGIE
a démarré en 2026 → **aucune facture N-1** → référence = 0 (comparatif inexploitable).

Solution (« référence année en vigueur ») : quand il n'y a pas de N-1, on bâtit la référence sur les
**prix du marché en vigueur** (fourniture BPU par typologie) **× la consommation attendue ENEDIS N-1**, au
lieu d'un historique de factures. La vue indique « **X PRM sans historique N-1** (marché démarré cette
année) ». Résultat concret : le budget de référence ENGIE 2026 est passé de ~0 à ~**1,15 M€**, exploitable.

### 2.3 Précision : typologies de bâtiment 2026 « granulaires »

Le nouveau marché 2026 range les bâtiments sous un usage unique « Bâtiment », subdivisé par **tension**
(HTA / BT>36 / BT≤36). L'import regroupait tout sous une seule étiquette (perte de la distinction de
classe). Désormais l'import **préserve la tension** (`BATIMENT_HTA` / `BATIMENT_BT` / `BATIMENT_BT36`), ce
qui rend la révision par typologie plus juste **et** permet au **contrôle de factures** de vérifier aussi
les bâtiments **C2 et C4** (avant : non contrôlés).

### 2.4 Pourquoi le réalisé **EDF 2026** peut sembler vide

Ce n'est pas un trou de données : c'est le **décalage de facturation** d'EDF éclairage public. Les factures
émises mi-2026 portent en réalité la **consommation 2025**. La consommation 2026 n'est **pas encore
facturée** ; l'atterrissage la **projette** en attendant. Ça se remplira quand EDF facturera 2026.

---

## 3. Suivi des indices & variables (`/refonte-v1/marches` → tout tier → « Indices & variables »)

**À quoi ça sert** : voir, en lecture seule, les **variables de prix** qui pilotent les révisions de chaque
marché. Une carte + un graphe **par famille**, filtrés selon le marché ouvert :

- **DALKIA** : indices contractuels **ICHT-IME**, **FSD2**, **BT40** + **coefficient de révision observé**
  (P2 / P3), reconstitué depuis les factures.
- **Gaz (TotalEnergies)** : prix **PEG** de la fourniture.
- **Électricité — TURPE** : évolution annuelle du TURPE (réseau) + indice cumulé.
- **Électricité — prix fourniture BPU** *(ajouté cette session)* : évolution du **prix de fourniture** par
  typologie (HTA / BT>36 / BT≤36 / éclairage public), année par année, tirée du marché Hérault Énergie.
  Complète le TURPE (réseau) par le prix de **l'énergie**.

Le KPI « **Familles** » liste désormais **les familles réellement présentes pour le marché ouvert** (avant :
texte figé « DALKIA, gaz, electricite » sur tous les onglets — corrigé). Période par défaut : **2023 →
année en cours**.

---

## 4. Cible conso & intéressement (DALKIA gaz) (`/refonte-v1/marches` → DALKIA → « Cible conso »)

**À quoi ça sert** : comparer, par site CPE DALKIA, la **consommation cible contractuelle (NB)** à la
**consommation réalisée (NC)**, et projeter la fin d'année pour estimer l'**intéressement** (conso sous la
cible) ou la **pénalité** (au-dessus). Modèle v1 = **gaz** (NB/DJU). *La cible électricité (IPMVP) est un
incrément suivant.*

- **Période** : plus de sélecteur par trimestre *(retiré cette session)*. On prend automatiquement la
  **période entière** : année en cours = tout le réalisé à date ; année passée = année complète.

**Pourquoi certains sites n'ont aucune valeur (« — »)** : un site est **projetable** seulement s'il a **une
cible NB contractuelle** ET **de la consommation réalisée**. Les sites « sans donnée » (constaté : ~32 sur
76) sont dans un de ces cas :
- **pas de cible NB** (site hors cible contractuelle) ; ou
- **aucune consommation réalisée** sur l'année (0 relevé importé).

Ce n'est **pas un bug** mais une **complétude de données** (cibles manquantes et/ou relevés de conso pas
encore chargés).

---

## 5. Référentiel BPU — d'où viennent les prix (import xlsx)

Les prix BPU sont importés depuis un **classeur Excel canonique** d'extraction manuelle
(`saas/energie/HERAULT ENERGIE/HISTORIQUE BPU/…`). Deux fichiers existent :

- `extraction_tarifs_electricite_BPU.xlsx` : **élec seul** (EDF + ENGIE). **C'est celui utilisé.**
- `extraction_tarifs_BPU_herault.xlsx` : superset avec en plus le **gaz TotalEnergies** (Lot 7).

**Vérifié** : les données **électricité sont identiques** entre les deux fichiers (mêmes segments, postes,
prix). Le `_herault` ajoute seulement les lignes gaz TE — mais celles-ci **ne se parsent pas** par le
script élec (segment « INCONNU », prix vides). Donc pour l'élec, le fichier `electricite` est le bon choix
(et plus propre) ; le BPU gaz TE nécessitera un **parseur gaz dédié**.

Re-import = `python -m app.scripts.import_bpu_xlsx --xlsx <fichier> --force` (le mode `--force` fait un
**remplacement propre** : il supprime le document existant et le recrée).

---

## 6. Points « à venir » assumés (non des bugs)

- **Import de factures** (`/refonte-v1/factures`) : le bouton « Importer des factures » est **désactivé**
  (l'UI d'upload n'est pas encore branchée) — chantier à cadrer (`import-factures-ui-cadrage.md`).
- **BPU gaz TotalEnergies** dans les référentiels : à charger via un parseur gaz (`bpu-gaz-totalenergies-cadrage.md`).
- **`/refonte-v1/fluides` vs `/energie`** : direction produit à cadrer (`fluides-vs-energie-cadrage.md`).
