---
read_policy: lire en premier pour reprendre l'outil thermique (passation Claude → Codex, 2026-09-22)
---

# Passation — outil thermique, lot E2

## 1. Où on en est

- Dépôt : worktree `C:\Users\pa.borja\Documents\Po2-thermique`, branche `feat/thermique-socle-raster`,
  alignée sur `main` au commit `56d3c0dd`, **en production** (thermique.patrimoineaucarre.com ; un push sur `main`
  déclenche le déploiement et `alembic upgrade head`).
- Méthode retenue : **plans lus comme des images (jamais les vecteurs du PDF)**, par des agents Claude Code, plus
  des algorithmes classiques de mesure, puis une **validation pièce par pièce par le thermicien**.
- Fait :
  - refondation de l'application (anciennes méthodes supprimées, migration 0082) ;
  - chaîne d'étude sur le poste ;
  - lecture des parois sur local non chauffé (D46) ;
  - **E1 : espace de travail du thermicien** (un seul écran : plans, panneaux Planche, Documents, Bibliothèque, Infos).

## 2. À lire, dans cet ordre

1. [espace-thermicien-decisions.md](espace-thermicien-decisions.md) — l'écran, D47 à D52, lots E1 à E5, réponses de
   l'utilisateur, E1 réalisé (§ 6).
2. [piece-par-piece-decisions.md](piece-par-piece-decisions.md) — D34 à D46 : stockage de l'étude, import,
   Remodéliser, versions, bibliothèque générale puis pièce par pièce, essai de lecture par local et ses résultats.
3. [chaine-analyse-plan-raster.md](chaine-analyse-plan-raster.md) — la chaîne d'étude d'un niveau.
4. Si besoin : `fiches-locaux-decisions.md` (D29 à D33), `locaux-decisions.md` (D24 à D28),
   `parcours-enveloppe-decisions.md`.

## 3. Prochain lot : E2 — import de l'étude d'un niveau et fiches en lecture

Objectif : dans l'espace de travail, déposer le fichier d'étude d'un niveau, voir ses locaux sur le plan, les
lister (chauffés d'abord), ouvrir la fiche d'un local (lecture seule).

1. **Fichier d'étude unique.** Ajouter à `saas/backend/scripts/run_etude_niveau.py` (fin de la restitution)
   l'écriture de `etude-<niveau>.json` : analyse (locaux intégrés, `locaux_ecartes`), manifeste de l'enveloppe,
   relevé résolu (éléments rattachés aux pièces, raccords), catalogue, fiches (`fiches_locaux`), synthèse par
   pièce, contrôle image (sans les cellules), demandes, version de format.
   - Données réelles pour tester sans lancer d'agent :
     `C:\Users\pa.borja\Documents\Codex\2026-09-18\tu\outputs\complement_R1\` (R+1 complet, D46 compris).
   - Analyse des locaux : `...\outputs\claude_agent_R1_locaux.json` ; plan : `C:\Users\pa.borja\Documents\Po2\Thermique\PLAN EXEMPLE PROJET 1\PC04-FRONT-NIVEAU1.pdf`.
2. **Serveur (D49, D50).** Tables `thermique_etudes` (une par planche : contenu JSON, état par local, plan de
   référence du projet à déplacer ici ou sur `thermique_projects`) et `thermique_etude_versions` (qui, quand,
   motif, contenu). Migration 0083 testée dans les deux sens (la chaîne complète ne tourne pas sous SQLite depuis
   0007 : tester la migration isolée, comme 0082). Routes : importer une étude sur une planche, la lire.
   Remodéliser et enregistrer viennent en E3.
3. **Interface.**
   - Dans `saas/frontend/src/thermique/workspace/` : bouton « Importer l'étude » dans le panneau Planche.
   - Locaux en surimpression sur le plan : `renderOverlay` de `TileSheetViewer`. Les points des locaux sont en
     repère feuille 0..1000 de l'image de l'analyse ; la conversion vers les points PDF est à établir et à tester,
     rotation de la planche comprise.
   - Liste des locaux dans la colonne de gauche : chauffés, puis circulations, puis non chauffés.
   - Nouvel onglet « Fiche » : côtés, adjacence, longueur, épaisseur, orientation, déperditif, parois et baies
     rattachées, parois sur local non chauffé, liaisons, alertes.
   - Étapes de la colonne de gauche allumées selon l'étude.
   - Le plan de référence choisi passe du navigateur (`localStorage`) au serveur.

Commencer par un fichier de décisions `docs/thermique/etude-niveau-E2-decisions.md` (existant vérifié, décisions,
questions numérotées) et le faire valider par l'utilisateur **avant de coder**.

## 4. Règles de l'utilisateur (impératives)

- Toujours répondre en **français** ; finir par « ce que j'ai fait, en clair » (non technique).
- **Fichier de décisions avant de coder** ; questions numérotées ; informer régulièrement.
- **Ne rien pousser sur GitHub sans autorisation explicite** (un push sur `main` met en production).
- Dépôt partagé avec Claude : `git status` avant, `git commit -- <chemins>`, jamais de force-push ; préserver les
  changements qui ne concernent pas le travail.
- Ne jamais afficher ni saisir de mot de passe, clé ou jeton ; ne pas copier d'identifiants.
- **Ne jamais revenir à une détection par les vecteurs du PDF** ; ne pas remplacer silencieusement Claude par un
  autre modèle pour la lecture des plans.
- Pas de connexion par API Claude : les agents tournent dans **Claude Code sur le poste** (mode session). Codex ne
  lance pas les agents Claude : il travaille sur les données déjà produites (§ 3.1) et sur l'application.
- Pas d'installation locale. Ne pas modifier `.claude/agents/thermicien-plan.md`.
- Poste de bureau seulement (pas de mobile) ; un seul panneau à droite ; locaux chauffés d'abord ; aucune hauteur
  par défaut.

## 5. Commandes

```bash
# tests serveur ciblés (depuis saas/backend)
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 DATABASE_URL=sqlite:///./test.db python -m pytest tests -k thermique -p no:cacheprovider
# interface (depuis saas/frontend)
npx tsc -b && npx vitest run src/thermique && npm run build
```

État à la passation : 117 tests serveur thermiques et 27 tests d'interface passent.
