# Référentiel BPU Hérault Énergies — décisions UX (avant code)

> Doc « fil du dev » — 2026-07-06. Objet : retravailler l'UX de l'onglet **BPU — Hérault Énergies** du hub
> `/refonte-v1/referentiels` pour une lecture **pertinente**. Aujourd'hui = page legacy `EnergieBpuPage`
> (thème sombre) qui **empile beaucoup de contenu** (pédagogie, indicatif) autour du cœur. Décider AVANT de coder.

## 1. Inventaire de l'existant (`EnergieBpuPage`, 4 onglets)

| Onglet | Contenu | Nature |
|---|---|---|
| **Timeline** | Filtres (segment/poste/fournisseur/lot) · graphe évolution des composantes · expression de la formule · **4 cartes de définition** des composantes (fourniture/capacité/CEE/GO, avec exemples) | cœur (graphe) + **pédagogie** (cartes) |
| **TURPE** | « Qu'est-ce que le TURPE ? » · **camembert facture 52/8/23/17 codé en dur (indicatif)** · graphe indice base 100 · table des points CRE | **pédagogie + indicatif** ; ⚠️ redondant avec *Indices & variables* de `/refonte-v1/marches` |
| **Documents & Import** | Stats (BPU stockés, OK/à revoir) · filtres · **table des BPU importés** (fournisseur/année/MS/lot/avenant/statut/confiance/fichier) · import xlsx (source de vérité) · import PDF/OCR (avancé) | **cœur** (table) + **admin** (imports) |
| **Édition tableau** | Édition des prix unitaires en BDD | **admin** |

## 2. Classification (proposée)

- **CŒUR (à quoi sert un référentiel)** : *quels BPU sont en vigueur* (table des documents, filtrable) et
  *quels prix* (composantes par période ; graphe d'évolution en appui).
- **ADMIN (secondaire, à replier)** : import xlsx / PDF-OCR, édition des prix.
- **PÉDAGOGIE / INDICATIF (empilé, « utile mais pas le sujet »)** : définitions des composantes,
  « Qu'est-ce que le TURPE », **camembert facture codé en dur**.
- **REDONDANT / MAL PLACÉ** : le bloc **TURPE** (tarif réseau réglementé, pas un BPU fournisseur ; déjà
  suivi dans *Indices & variables*).

## 3. Cible proposée (à valider par les questions §5)

Vue BPU curée, orientée **consultation** :
1. **Par défaut = « Quels prix s'appliquent »** : table des BPU en vigueur (fournisseur × année × lot ×
   avenant × statut), filtrable ; **statut/confiance discret** (pastille), pas 4 gros KPIs.
2. **Détail d'un BPU** (clic) → ses composantes de prix par période (drill-down), + lien PDF source.
3. **« Évolution » en appui** (secondaire) : le graphe timeline, pour l'analytique.
4. **Aide contextuelle** : définitions des composantes en **infobulle**, pas en blocs pleine page.
5. **Admin replié** : import + édition derrière un bouton « Gérer / Admin » (garde l'accès legacy complet).
6. **TURPE** : **retiré** du référentiel BPU (renvoi vers *Indices & variables*).

## 4. Enjeu structurant : reconstruire vs nettoyer en place
- **Option A — reconstruire une vue curée au design-system V1** pour l'onglet BPU du hub (remplace
  l'embarquement de `EnergieBpuPage` **dans le hub uniquement** ; la page legacy `/energie/bpu` reste
  intacte pour l'admin/full). → UX propre et cohérente, mais on re-câble lecture + drill-down.
- **Option B — nettoyer `EnergieBpuPage` en place** (retirer/replier les blocs) : plus rapide, mais garde
  le thème sombre legacy et impacte aussi `/energie/bpu`.

## 5. Questions ouvertes (à trancher avant de coder)
1. **Q1 — Job principal** de la vue BPU : consulter *le prix applicable* (opérationnel) ? voir *l'évolution
   historique* (analytique) ? les deux, avec lequel par défaut ?
2. **Q2 — Reconstruire (A) ou nettoyer en place (B)** ? (cf. §4)
3. **Q3 — TURPE** dans le référentiel BPU : retirer (reco), garder, ou déplacer ailleurs ?
4. **Q4 — Contenu pédagogique** (définitions composantes, « qu'est-ce que le TURPE ») : infobulle repliable,
   ou retirer complètement ?
5. **Q5 — Camembert « poids TURPE dans la facture »** (chiffres codés en dur, indicatifs) : supprimer ?
6. **Q6 — Admin (import/édition)** : replier derrière « Gérer », ou garder visible dans la vue ?
7. **Q7 — Le même traitement pour l'onglet DPGF DALKIA** plus tard, ou on se concentre sur BPU d'abord ?
