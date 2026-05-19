# 2026-05-19 - Audit projet + Backlog zero install

> IA : Codex GPT-5
> Duree approximative : ~45 min
> Precedente session : [[Sessions/2026-05-19 — Renommage + Templates + ADRs]]

## Objectif de la session

Analyser l'etat du projet Po2, les travaux deja developpes, ce qui reste a developper, les liens entre taches dans Obsidian, puis produire un rapport et une organisation exploitable.

Information utilisateur importante recue pendant la session : le poste est un ordinateur entreprise. Aucune installation locale de bibliotheques Python, Node, npm ou dependances projet ne doit etre supposee.

## Ce qui a ete fait

### Audit code + Obsidian

- Creation de [[06-Rapport-audit-projet-obsidian-2026-05-19]]
- Analyse des modules existants : patrimoine, gestion technique, ENEDIS, factures, TURPE, BPU, preconisations.
- Identification des priorites : BPU fiable, ENEDIS async prod, audit facture ENGIE, CVC/enveloppe, baux.

### Backlog operationnel

- Creation de [[Backlog]]
- Ajout d'une table de priorites avec IDs : `PO2-BPU-001`, `PO2-ENEDIS-001`, `PO2-FACT-001`, etc.
- Ajout d'un graphe Mermaid des dependances entre chantiers.

### Contrainte poste entreprise

- Creation de [[07-Environnement-poste-entreprise]]
- Creation de l'ADR [[Decisions/005-poste-entreprise-zero-install-local]]
- Mise a jour de [[05-Conventions-IA]] pour supprimer l'hypothese d'un environnement Python/Node local.

### Nettoyage Obsidian

- Correction de placeholders de templates qui pouvaient polluer le graphe.
- Mise a jour de [[00-Index]] pour pointer vers le backlog, le rapport, la contrainte entreprise et l'ADR 005.

## Ce qui reste a faire / handoff

### Priorite 1 - Corriger la doc des routes factures

- **Statut** : fait dans la suite de session.
- **Probleme traite** : plusieurs notes parlaient de `/api/energie/factures/*`, alors que le code expose les imports factures sous `/api/billing/invoices/imports/*`.
- **Fichiers modifies** : `docs/Modules/Energie-Facturation.md`, `docs/03-Roadmap-fonctionnalites.md`, `docs/Backlog.md`, `docs/06-Rapport-audit-projet-obsidian-2026-05-19.md`.
- **Backlog** : `PO2-DOC-001`.

### Priorite 2 - Choisir le prochain chantier produit

Recommandation Codex :

1. `PO2-BPU-001` - Parser BPU fiable ou saisie corrective. Statut : en cours, phase 1 implementee sans nouvelle dependance.
2. `PO2-ENEDIS-001` - Finaliser backfill async prod.
3. `PO2-FACT-001` - Audit facture ENGIE complet.

### Suite BPU realisee

- Fichier chantier cree : [[Chantiers/PO2-BPU-001-Parser-BPU-fiable]]
- Code modifie : `saas/backend/app/services/bpu.py`, `saas/backend/requirements.txt`, `saas/backend/app/scripts/report_bpu_import_quality.py`
- Test ajoute : `saas/backend/tests/test_bpu_parser.py`
- Validation locale : `python -m compileall ...` OK
- Tests pytest : non lances, car `pytest` et `sqlalchemy` ne sont pas disponibles sur le poste utilisateur.
- Phase 2 ajoutee : `pdfplumber==0.11.9` pour extraction cellule par cellule des tableaux PDF dans l'image backend.
- Script de mesure ajoute : `python -m app.scripts.report_bpu_import_quality --min-components 20`.

### Contrainte permanente

Ne jamais demander a l'utilisateur d'installer une dependance locale. Toute dependance doit etre versionnee dans le repo et validee via CI, conteneur, VPS, Codespaces ou environnement Codex deja equipe.

## Notes & decisions

- Decision durable formalisee : [[Decisions/005-poste-entreprise-zero-install-local]]
- Le backlog devient le point de pilotage operationnel ; la roadmap reste la vision produit.

## Pour la prochaine IA - entree en matiere

```
J'ai lu :
- docs/07-Environnement-poste-entreprise.md
- docs/Backlog.md
- docs/06-Rapport-audit-projet-obsidian-2026-05-19.md
- docs/04-Etat-actuel-du-dev.md
- docs/Sessions/2026-05-19 - Audit projet + Backlog zero install.md

Je sais que le poste utilisateur est verrouille entreprise : aucune installation locale ne doit etre demandee.
Je comprends que la prochaine action recommandee est PO2-DOC-001 ou PO2-BPU-001 selon arbitrage utilisateur.
Je propose de commencer par corriger la doc des routes factures, puis d'attaquer le parser BPU.
```
