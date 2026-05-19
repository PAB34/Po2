# 005 - Poste entreprise zero installation locale

> **Statut** : Accepte
> **Date** : 2026-05-19
> **Decideur(s)** : PAB34
> **Session liee** : session Codex du 2026-05-19, suite audit Obsidian

## Contexte

L'utilisateur travaille sur un ordinateur entreprise. Il n'est pas possible d'installer localement des bibliotheques Python, Node, npm, outils systeme ou dependances projet.

Le projet Po2 utilise pourtant des dependances backend, frontend, OCR/PDF, tests et build. Si les futures IA supposent un poste local complet, elles vont proposer des actions impossibles ou fragiles.

## Decision

Le poste utilisateur est considere comme un poste de pilotage, pas comme un environnement de developpement local.

Toute dependance doit etre ajoutee au repository et validee via CI, conteneur, VPS, Codespaces ou environnement Codex deja equipe.

## Consequences

### Positives

- Workflow compatible avec les restrictions entreprise.
- Moins de dependances cachees installees sur une machine personnelle.
- Les validations deviennent reproductibles dans CI/conteneur.
- Les handoffs IA sont plus fiables : aucune commande ne suppose un poste local prepare.

### Negatives / couts assumes

- Certaines validations locales rapides ne seront pas possibles.
- Les cycles de test peuvent dependre de GitHub Actions, du VPS ou d'un conteneur.
- Les nouvelles dependances doivent etre pensees avec Docker/CI des leur introduction.

### Alternatives ecartees

- **Installer les outils localement** - Non compatible avec le poste entreprise.
- **Maintenir un environnement Python/Node user-scope** - Trop fragile et non garanti.
- **Ne pas ajouter de nouvelles dependances** - Trop restrictif pour le parser BPU, PDF/OCR et les futurs connecteurs.

## Liens

- Contrainte operationnelle : [[07-Environnement-poste-entreprise]]
- Backlog : [[Backlog]]
- Conventions IA : [[05-Conventions-IA]]

