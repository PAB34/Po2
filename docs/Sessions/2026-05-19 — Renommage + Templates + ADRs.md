# 2026-05-19 — Renommage tirets + Template session + Dossier Décisions ADR

> IA : Claude Sonnet 4.5
> Durée : ~25 min
> Précédente session : [[Sessions/2026-05-19 — Intégration specs historiques au vault]]

## 🎯 Objectif

3 décisions de l'utilisateur à matérialiser :
1. Renommer fichiers du vault en `00-Index.md` (tirets au lieu d'espaces) pour le tri Obsidian
2. Créer `Sessions/_template.md` comme squelette pré-rempli
3. Créer un dossier `Decisions/` style ADR pour tracer les choix durables

## ✅ Ce qui a été fait

### 1. Renommage des fichiers
Tous renommés via `git mv` (preserve l'historique) :

| Avant | Après |
|---|---|
| `00 Index.md` | `00-Index.md` |
| `01 Vision & Utilisateur.md` | `01-Vision-Utilisateur.md` |
| `02 Architecture.md` | `02-Architecture.md` |
| `03 Roadmap fonctionnalités.md` | `03-Roadmap-fonctionnalites.md` |
| `04 État actuel du dev.md` | `04-Etat-actuel-du-dev.md` |
| `05 Conventions IA.md` | `05-Conventions-IA.md` |
| `Modules/Gestion technique.md` | `Modules/Gestion-technique.md` |
| `Modules/Énergie - BPU.md` | `Modules/Energie-BPU.md` |
| `Modules/Énergie - Consommation.md` | `Modules/Energie-Consommation.md` |
| `Modules/Énergie - Facturation.md` | `Modules/Energie-Facturation.md` |
| `Modules/Énergie - Préconisations.md` | `Modules/Energie-Preconisations.md` |
| `Modules/Énergie - TURPE.md` | `Modules/Energie-TURPE.md` |

Convention : tirets entre les mots, pas d'accents dans les noms de fichiers (compat URLs, slugs, scripts), accents préservés dans les titres et le contenu.

Sessions/ conservent le format `AAAA-MM-JJ — Titre.md` (le tiret cadratin `—` reste, c'est lisible et la date suffit pour le tri).

### 2. Liens `[[...]]` mis à jour
Script Python qui parcourt tout `docs/` et applique 16 substitutions de regex. **11 fichiers modifiés** automatiquement, aucun lien orphelin.

### 3. Sessions/_template.md
Squelette complet avec :
- En-tête (IA, durée, session précédente)
- 🎯 Objectif
- ✅ Ce qui a été fait (avec section par chantier)
- 🛠️ Outils découverts
- 🚧 Handoff (priorités numérotées, fichiers, commandes, pièges)
- 📝 Notes & décisions (avec rappel : créer une ADR si durable)
- 🔁 Modèle de message d'ouverture pour la prochaine IA

### 4. Dossier `Decisions/` (ADR — Architecture Decision Records)
Convention : on utilise `Decisions/` (sans accent) pour la compatibilité scripts/URLs.

5 fichiers créés :
- `_template.md` — structure type (Statut / Date / Contexte / Décision / Conséquences / Alternatives / Liens)
- **000-format-ADR.md** — pourquoi ce format, quand créer une ADR (oui/non)
- **001-vault-obsidian-versionne-dans-git.md** — décision rétroactive du jour
- **002-bpu-schema-normalise-5-tables.md** — décision rétroactive (PR #11/#12)
- **003-enedis-async-ftp-meme-vps-que-po2.md** — décision rétroactive (plan ENEDIS antérieur)
- **004-specs-restent-dans-saas-specs.md** — décision rétroactive (session précédente du jour)

### 5. Mise à jour des fichiers cardinaux
- `00-Index.md` → ajout section "🧠 Décisions durables (ADR)" + référence aux templates
- `05-Conventions-IA.md` → section B simplifiée (copier template), nouvelle section C "Créer une ADR si durable", renumérotation (D = commit/push)

## 🚧 Handoff

Pas de chantier en suspens sur ce sujet. Les 3 demandes utilisateur sont réalisées.

**Reste à arbitrer côté utilisateur (reporté depuis la session BPU)** :
- Priorité prochaine session : `parser BPU` (pdfplumber), `baux locataires`, `GRDF`, ou `dette ENEDIS async` (filtrage PRM + découpe batch) ? → Utilisateur a répondu "AUCUNE IDEE POUR LINSTANT", donc à reprendre quand il aura tranché.

## 📝 Notes & décisions

Décisions matérialisées dans cette session (cf. [[Decisions/000-format-ADR]] et suivantes) — ne se réécrivent pas ici.

## 🔁 Pour la prochaine IA — entrée en matière

```
J'ai lu :
- docs/00-Index.md
- docs/04-Etat-actuel-du-dev.md
- docs/Sessions/2026-05-19 — Renommage + Templates + ADRs.md

Je comprends que les 3 chantiers prioritaires possibles sont :
- Parser BPU (pdfplumber)
- Module Baux locataires
- Connecteur GRDF
- Dette ENEDIS async

L'utilisateur n'a pas encore tranché — je propose de lui poser la question
avec un récap court de chaque option (effort estimé, impact métier).
```
