---
type: index
status: actif
read_policy: toujours
source_of_truth: true
related:
  - 04-Etat-actuel-du-dev.md
  - 05-Conventions-IA.md
  - Backlog.md
do_not_auto_read:
  - Archives/
  - Sessions/
---

# Po2 — Index de la documentation IA

> Vault partagé entre toutes les IA (Claude Code, Codex) du projet **PatrimoineOp / Po2**.
> **Règle de lecture** : ne pas lire les dossiers `Archives/`, le journal ou `Sessions/` sauf demande
> explicite ou besoin justifié. Ne pas suivre automatiquement tous les liens Markdown. Respecter
> `read_policy` quand il existe.

## 🔥 Mémoire chaude — lire au démarrage

| Fichier | Rôle |
|---|---|
| [[01-Vision-Utilisateur]] | But, utilisateur, contexte métier |
| [[02-Architecture]] | Stack, où vit quoi, conventions de code |
| [[04-Etat-actuel-du-dev]] | Présent : prod, chantiers ouverts, **section Reprise** |
| [[05-Conventions-IA]] | Passation IA-à-IA ⚠️ lire avant toute modif |
| [[07-Environnement-poste-entreprise]] | Contrainte zéro install locale |
| [[Backlog]] | Quoi faire ensuite, ordre, dépendances |
| [[03-Roadmap-fonctionnalites]] | 13 fonctionnalités cibles + statuts |

## 🟡 Mémoire tiède — lire si la tâche concerne le sujet

**Tranche en cours**
- [[49-Spec-execution-refonte-Factures-Decisions-V1]] — **spec active** Factures & décisions (état d'implém. §0). Glossaire métier : `refonte-v1/factures-glossaire-controles.md`
- `refonte-v1/suivi-financier-budget-atterrissage-cadrage.md` — **cadrage prochaine tranche** : budget par marché + suivi financier / atterrissage
- [[35-Contrat-ecran-Factures-Decisions-V1]] · [[34-Contrat-ecran-Fluides-V1]] · [[36-Contrat-ecran-Cockpit-Sites-V1]] — contrats d'écran
- [[37-Plan-migration-React-refonte-V1]] · [[38-Modele-backend-matrices-comptables-versionnees]] · [[40-Analyse-factures-reelles-pour-matrice-comptable]] · [[13-Matrice-routes-fonctionnalites-refonte-api]]

**Modules métier** (1 fichier par bloc) — `Modules/`
- [[Modules/Patrimoine]] · [[Modules/Gestion-technique]] · [[Modules/Energie-Consommation]] · [[Modules/Energie-Gaz]] · [[Modules/GRDF-API]]
- [[Modules/Energie-Facturation]] · [[Modules/Energie-BPU]] · [[Modules/Energie-Preconisations]] · [[Modules/Energie-TURPE]]
- [[Modules/Conformite-OPERAT]] · [[Modules/Maintenance-Contrats]]
- CPE DALKIA (référence métier) → `energie/CPE-DALKIA/00-Index.md`

**Décisions durables (ADR)** — `Decisions/`
- [[Decisions/000-format-ADR]] · [[Decisions/008-referentiel-patrimoine-et-rapprochements]] · [[Decisions/009-environnement-staging]]
- [[Decisions/010-matrices-comptables-versionnees]] · [[Decisions/011-assistant-matrices-et-decisions-factures-V1]] · [[Decisions/012-auto-validation-et-semantique-controle-factures-V1]]
- ADR 001→007 : voir le dossier `Decisions/`

**Specs techniques** : [[Specs]] (catalogue `saas/specs/`)

## 🧊 Mémoire froide — NE PAS lire par défaut

- `Archives/` — audits datés, questionnaires, cartographies, décisions intermédiaires (index : `Archives/README.md`)
- `Archives/Journal-etat-dev-2026.md` — journal chronologique complet (ex-04)
- `Sessions/` — une note par session de travail IA
- `prototype-refonte-v1/`, `api-cartographie/`, `branding/` — artefacts visuels/outillage

## 🔁 Workflow IA-à-IA (version courte)

```
1. Lire : 00-Index → 04-Etat-actuel (section Reprise) → 05-Conventions-IA
2. Vérifier la contrainte poste entreprise : 07-Environnement
3. Identifier sa tâche : Backlog (statut "todo"/"en cours")
4. Pour une tâche : ouvrir le Module concerné + la spec active. NE PAS lire Archives/ ni Sessions/.
5. Fin de session : réécrire la section "Reprise" de 04 + créer Sessions/AAAA-MM-JJ + ADR si choix durable.
```

Détail complet : [[05-Conventions-IA]].

## 🔗 Liens externes

- Repo : https://github.com/PAB34/Po2 · Prod : https://patrimoineaucarre.com
- VPS (Po2 + FTP ENEDIS) : `ubuntu@135.125.152.112` via clé SSH `po2_vps2`
