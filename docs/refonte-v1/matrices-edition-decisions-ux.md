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

**Tes réponses :**
