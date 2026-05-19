# 2026-05-19 — Intégration des specs historiques au vault Obsidian

> IA : Claude Sonnet 4.5
> Durée : ~30 min (audit + rédaction)
> Précédente session : [[Sessions/2026-05-19 — BPU + Codespaces + Vault Obsidian]]

## 🎯 Objectif

L'utilisateur a signalé que des specs existaient dans `saas/specs/` (9 fichiers, avril-mai 2026) et a demandé de les évaluer pour savoir si elles méritaient d'être intégrées au vault Obsidian fraîchement créé.

## ✅ Ce qui a été fait

### 1. Audit des 9 specs
Verdict produit par fichier (cf. [[Specs]] pour le catalogue complet) :

| # | Statut |
|---|---|
| 01 fonctionnalités v0.2 | 🟡 Partiel — workflow consolidation DGFiP intégré à [[Modules/Patrimoine]] |
| 02 architecture v0.1 | 📦 Obsolète — déplacée dans `saas/specs/_archives/` |
| 03 plan facturation | 🟡 Partiel — cadre Hérault Énergies intégré à [[Modules/Energie-Facturation]] |
| 04 mapping ENGIE | ✅ Canonique — référencée |
| 05 matrice contrôles | ✅ Canonique — référencée |
| 06 préconisations V1 | ✅ Canonique — marges 20/12/5 % intégrées à [[Modules/Energie-Preconisations]] |
| 07a plan exécution | 🟡 Partiel — phases ouvertes versées dans [[03-Roadmap-fonctionnalites]] |
| 07b TURPE 7 | ✅ Canonique — nouveau module [[Modules/Energie-TURPE]] créé |
| 08 kit ENEDIS async | ✅ Canonique — gaps techniques intégrés à [[Modules/Energie-Consommation]] |

### 2. Nouveaux fichiers Obsidian
- [[Specs]] — catalogue complet avec verdicts et pépites
- [[Modules/Energie-TURPE]] — nouveau module dédié au référentiel TURPE 7

### 3. Modules enrichis (sections ajoutées)
- [[Modules/Patrimoine]] → "Workflow de consolidation DGFiP → bâtiment métier"
- [[Modules/Energie-Facturation]] → "Cadre contractuel Hérault Énergies" + "Documents de référence" (liens vers specs 04 et 05)
- [[Modules/Energie-Preconisations]] → "Seuils V1 (canoniques)" avec table marges 20/12/5 %
- [[Modules/Energie-Consommation]] → "Dette technique ENEDIS Async" avec table gaps + limites plateforme

### 4. Mise à jour des fichiers racine
- [[00-Index]] → ajout liens vers [[Modules/Energie-TURPE]] et [[Specs]]
- [[04-Etat-actuel-du-dev]] → section "Specs historiques" + 2 chantiers ouverts (dette ENEDIS async + refresh TURPE 2026-08-01)

### 5. Archivage
- `saas/specs/02_architecture_technique.md` → `saas/specs/_archives/02_architecture_technique_v01_obsolete.md` via `git mv`

## 📐 Principe retenu pour les specs

Décision implicite : **on ne déplace PAS les specs dans `docs/`**. Elles restent dans `saas/specs/` parce que :
1. C'est leur emplacement historique
2. Elles font partie du repo (versionnées)
3. Le vault Obsidian sert à coordonner / synthétiser, pas à dupliquer du contenu de spec

Donc le pattern est : **les modules Obsidian référencent les specs** (lien `saas/specs/NN_xxx.md`) plutôt que d'en recopier le contenu. Seules les pépites chiffrées (codes erreur, marges, seuils) sont matérialisées dans les modules pour qu'elles soient lisibles depuis Obsidian sans ouvrir le PDF/MD source.

## 🚧 Handoff suivant

Rien de bloquant — toute la session est dans le commit + push.

Les chantiers prioritaires restent les mêmes (cf. [[04-Etat-actuel-du-dev]] section "Chantiers ouverts") :
1. Parser BPU (passer à pdfplumber)
2. Module Baux locataires
3. Connecteur GRDF
4. **Nouveau** : traiter la dette ENEDIS async (filtrage PRM + découpe batch) — cf. spec 08

## 📝 Décisions encore ouvertes pour l'utilisateur

Reportées de la session précédente, pas encore arbitrées :
- [ ] Renommer fichiers en `00-Index.md` (tirets) ?
- [ ] Créer `Sessions/_template.md` ?
- [ ] Dossier `Décisions/` style ADR ?
- [ ] Priorité prochaine session : parser BPU / baux locataires / GRDF / dette ENEDIS async ?
