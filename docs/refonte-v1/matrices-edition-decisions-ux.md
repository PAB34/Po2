# Édition de la matrice versionnée (/refonte-v1/matrices) — décisions UX

> Fichier de travail « fil du dev ». Sujet : remplacer le tiroir lecture-seule de `/refonte-v1/matrices`
> par une **fenêtre pleine page éditable** (plus de colonnes comptables + import/export XLSX).
> Page : `saas/frontend/src/features/matrices/MatrixAdminPageV1.tsx` · API : `/api/accounting-matrices/*`.

## 1. Deux écrans « matrice » distincts (à ne pas confondre)

| Écran | Système | État édition |
|---|---|---|
| `/factures` (`EnergieAccountingMatrix`) | tables **à plat** `energy_accounting_*` (ENGIE/EDF) et `cpe_accounting_*` (DALKIA) | **éditable en direct** + import/export XLSX (déjà livré) |
| `/refonte-v1/matrices` (`MatrixAdminPageV1`) | matrice **versionnée** `accounting_matrix_*` (ADR 010, cible générique tous tiers) | **lecture seule** (tiroir 5 colonnes) + export/import XLSX déjà présent |

C'est le 2ᵉ (versionné) que vise cette tâche. La saisie de test des 32 PRM ENGIE vit dans le 1ᵉʳ.

## 2. Constat sur le tiroir actuel de `/refonte-v1/matrices`

Le tableau « Règles de la version » n'affiche que : `Cle stable`, `Scope`, `Poste / perimetre`, `Nature`, `%`.
Or le modèle `accounting_matrix_rules` porte bien plus (toutes utiles à l'écriture comptable) :
`accounting_service`, `accounting_function`, `accounting_antenna`, `operation_number`, `accounting_label`,
`priority`, `is_active`, `comment`, + les clés de rapprochement `site_code`, `meter_id`,
`billed_item_pattern`, `supplier_item_code`. **Rien n'est éditable** dans l'écran (l'API le permet pourtant :
`POST .../versions/{id}/rules`, `PATCH .../rules/{id}`).

## 3. Demande utilisateur (2026-07-01)

- Remplacer le **tiroir** par une **fenêtre en superposition quasi pleine page**.
- **Éditer la matrice** depuis cette fenêtre (toutes les colonnes comptables).
- Pouvoir **exporter / importer** pour mise à jour (déjà là, à intégrer dans la nouvelle fenêtre).

## 4. ⚠️ Contrainte structurante : versions immuables (ADR 010)

Invariant du système versionné : **une version `active` (ou `archived`) n'est jamais modifiée en place**.
Le backend **refuse** `create_rule`/`update_rule` sur une version active. Or la version affichée pour
DALKIA `C00025811F` est justement **`active`**. Donc « éditer la matrice » se heurte à cet invariant.

Deux façons de concilier édition + versioning (**Q1**) :
- **(a) Édition via nouvelle version (recommandé)** : quand tu édites une matrice active, la plateforme
  **clone** automatiquement la version active en un **brouillon** éditable ; tu modifies le brouillon ;
  un bouton **« Activer »** bascule (l'ancienne s'archive). On garde l'audit et l'historique des factures.
- **(b) Édition directe de la version active** : plus simple pour l'utilisateur, mais **casse** la garantie
  « une facture validée garde sa version » (les décisions passées deviennent réécrivables). Déconseillé.

## 5. Questions à trancher

- **Q1 — Modèle d'édition vs versioning** : (a) clone→brouillon→activer, ou (b) édition directe ? (cf. §4)
- **Q2 — Colonnes à éditer** dans la fenêtre pleine page : je propose le jeu complet — Poste/pattern, Scope,
  Site, Compteur, **Service, Fonction, Antenne, Opération**, Nature, Libellé nature, %, Priorité, Actif,
  Commentaire. OK, ou tu veux en retirer/ajouter ?
- **Q3 — Périmètre de cette itération** : (a) on ne touche QUE l'écran versionné `/refonte-v1/matrices`
  (fenêtre pleine page éditable), ou (b) on vise aussi à **unifier** avec les éditeurs à plat de `/factures`
  (pour n'avoir qu'un seul endroit d'édition à terme) ? [b = plus gros chantier, à cadrer à part]

**Tes réponses (2026-07-01) :** Q1 = **(b) édition directe** (archivées figées) · Q2 = **axes comptables
uniquement** · Q3 = **(a) écran versionné seulement**. → livré (PR #35).

---

## 6. Itération 2 — retours du 2026-07-01 (vérifiés sur données réelles) + recommandations

> Rappel « fil du dev » : ci-dessous chaque point est **vérifié en base / dans les fichiers**, avec ma
> recommandation puis une question quand une décision t'appartient.

### 6.1 Antenne prise au mauvais endroit (DALKIA) — **bug confirmé, correction claire**
Le seed écrit `accounting_antenna = antenna_label or antenna_code` (`accounting_matrix.py` l.302 et 355) :
il prend donc le **libellé long**. Or en base, `antenna_code` **est déjà le nom court** attendu
(ex. `LIDO`, `MUSEE P VA`, `A VARDA`) et `antenna_label` le long (`COMPLEXE DU LIDO GYMNASE + STADE`).
→ **Reco (ferme)** : utiliser **`antenna_code`** pour l'axe Antenne (idem raisonnement possible pour
Service/Fonction : code vs libellé). Correction du seed **+** correction des données déjà en base
(re-seed ou UPDATE ciblé sur staging). **Pas de question** — je corrige, sauf avis contraire.

### 6.2 Numéro d'opération : lié au poste facturé ou au site ? — **décision métier (Q4)**
Aujourd'hui l'opération vient du **mapping site** (`Sites vers codes` → une opération par site/bâtiment).
Mais dans le classeur, un poste **travaux** porte sa propre opération (P3.4 = « opération 98023 »).
Donc c'est **mixte** : dépense courante P1/P2 = opération **du site** ; travaux P3.x = opération **du poste**.
→ **Reco** : garder l'opération **par site** par défaut (cohérent doc 32 « opération = maille budgétaire »),
**et** autoriser une **opération au niveau du poste** qui prime pour les postes travaux. **Q4 : ok pour
cette règle mixte, ou tu veux l'opération strictement au poste ?**

### 6.3 Première colonne « Désignation site » (extraite de la facture) — **faisable, données déjà là**
Vérifié : la désignation existe déjà en base pour les 3 tiers —
DALKIA `cpe_finance_lines.detail` (« LIEU OU DÉTAIL DE LA PRESTATION »),
ENGIE `energy_invoice_sites.site_name` (« Désignation Site »),
EDF idem (« nom_site »). Le hic : la matrice **versionnée** repère ses lignes de site par `site_code`
(DALKIA) ou `meter_id`/PRM (ENGIE/EDF), sans jointure vers la désignation facture.
→ **Reco** : ajouter une **1ʳᵉ colonne lecture-seule « Désignation site »** dans l'éditeur, résolue en
joignant la règle (site_code/PRM) aux sites de facture. Nécessite d'enrichir l'endpoint des règles
(renvoyer la désignation). **Pas de question** sur le principe ; je le construis.

### 6.4 Antenne ENGIE/EDF = nom court dérivé de la désignation — **cohérent, à valider (Q5)**
Constat : côté DALKIA, `antenna_code` est **déjà** un nom court du site (ex. `LIDO`). Côté ENGIE/EDF il
n'existe pas encore. Ta demande (antenne = nom court construit depuis « Désignation Site ») est donc
**cohérente** avec la logique DALKIA — ce n'est pas une aberration.
→ **Reco (v1)** : générer un `antenna_code` court par **heuristique** depuis la désignation (majuscules,
retrait des mots vides type « ESPACE / LOCAL / APPART », troncature ~16 car., dédoublonnage). Ex.
`CINEMA LE PLANET` → `CINEMA PLANET`, `ESPACE AMITIE CHATEAU VERT RDC` → `AMITIE CHATEAU VERT`.
La compta pourra corriger ensuite. **Q5 : ok pour une antenne dérivée automatiquement (modifiable), ou tu
préfères l'antenne vide tant que la compta ne l'a pas saisie ?** ⚠️ Contrôle : « antenne » reste une
dimension comptable ; ici on l'amorce avec un nom court de site, ce qui est acceptable en v1 mais à
garder en tête si un vrai découpage par antennes/services arrive.

### 6.5 En-têtes triables — **UI, je le fais**
Reco : clic sur l'en-tête = tri asc/desc (indicateur ▲▼). Sans question.

### 6.6 Largeur de colonnes ajustable — **UI, option à choisir (Q6)**
Deux approches : (a) **poignées de redimensionnement** par colonne (drag) — plus riche, plus de code ;
(b) colonnes à **largeur min + défilement horizontal**, plus quelques largeurs préréglées. 
→ **Reco** : (a) redimensionnement au drag (persisté en local). **Q6 : ok pour le drag, ou (b) suffit ?**

### 6.7 Recommandation transverse (importante)
Tes 3 demandes fortes (désignation, antenne dérivée, données de site) **vivent nativement dans le
système à plat** (`energy_accounting_*` / `cpe_accounting_*`, déjà joint aux factures et déjà éditable
sur `/factures`). La matrice **versionnée** est un cran plus loin de la facture. 
→ **Reco à trancher (Q7)** : soit (a) on **enrichit l'éditeur versionné** en le joignant aux données de
facture (ce que je décris ci-dessus), soit (b) on **repense la source des lignes de site de la matrice
versionnée** pour qu'elles soient **construites depuis les sites de facture** (désignation + antenne
dérivée incluses) via un seed/bootstrap enrichi — plus propre à terme, mais c'est un refactor. **Q7 :
(a) enrichir l'éditeur au fil de l'eau, ou (b) planifier le refactor de la source ?**

**Tes réponses Q4–Q7 :**
