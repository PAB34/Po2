---
type: archive
status: historique
read_policy: ne_pas_lire_par_defaut
source_of_truth: false
---

# Archives documentaires Po2

> **NE PAS LIRE par défaut.** Ces fichiers sont des artefacts de raisonnement à usage unique
> (audits datés, questionnaires, cartographies, décisions intermédiaires) conservés pour traçabilité.
> Ils ne sont **pas nécessaires** à une session de travail normale.
> Les conclusions durables ont été remontées vers les sources de vérité actives :
> `../04-Etat-actuel-du-dev.md`, `../Decisions/`, `../Modules/`, et la spec active citée dans `../00-Index.md`.

N'ouvrir un fichier ci-dessous que si une tâche précise le justifie explicitement.

## Journal d'état

| Fichier | Contenu |
|---|---|
| `Journal-etat-dev-2026.md` | Journal chronologique complet (ex-04), mises à jour 2026-05 → 2026-06 |

## Audits & inventaires (one-shot)

| Fichier | Sujet | Remonté dans |
|---|---|---|
| `06-Rapport-audit-projet-obsidian-2026-05-19.md` | Audit code + vault | Backlog / Modules |
| `08-Inventaire-fonctionnalites-developpees-2026-06-02.md` | Inventaire transversal du code | Backlog (PO2-AUDIT-001) |
| `09-Vision-produit-et-navigation-UX.md` | Cartographie produit / nav | Modèle V1 |
| `10-Audit-moteurs-et-experience-utilisateur-2026-06-15.md` | Audit moteurs + UX cible | Backlog / cap direction |
| `11-Analyse-backend-et-socle-refonte-UX.md` | 279 endpoints, graphe relations | `13-Matrice-routes` (actif) |
| `15-Validation-P0-factures-finance.md` | Preuves parcours P0 | — |
| `16-Audit-moteur-contractuel-BPU-Herault.md` | Audit BPU Hérault | Modules/Energie-BPU |
| `23-Seconde-passe-audit-fonctionnel-et-angles-morts.md` | Audit différentiel | Backlog (PO2-CORE-001) |
| `26-Audit-couverture-atelier-BPMN-2026-06-22.md` | Couverture BPMN | — |

## Cadrages & cartographies refonte (one-shot)

| Fichier | Sujet | Remplacé / remonté par |
|---|---|---|
| `12-Plan-plateforme-cible-et-tri-endpoints.md` | Tri endpoints cible | `13` (actif) |
| `14-Catalogue-fonctionnalites-commentees-et-reaffectation.md` | Lecture métier endpoints | `13` (actif) |
| `17-Refonte-frontend-capacites-metier.md` | Cadrage refonte front | `37-Plan-migration` (actif) |
| `18-Registre-raccordement-frontend.md` | Plan de câblage | `37` / `49` |
| `19-Atelier-cartographie-frontend.md` | Atelier HTML cartographie | `37` / `49` |
| `20-Cap-direction-2026-...md` | Cap direction P0 | `04` (chantiers) / Backlog |
| `21-Cartographie-fonctionnelle-vers-experience-utilisateur.md` | Méthode capacité→écran | Modèle V1 |
| `22-Developpement-deux-pistes-et-profils-utilisateurs.md` | Stratégie 2 pistes | Backlog |
| `24-Cockpit-canonique-reconstruction-produit-frontend.md` | Registre capacités | — |
| `25-Atelier-BPMN-produit-UX.md` | Atelier BPMN | — |
| `27-Modele-V1-plateforme-operationnelle.md` | Projection V1 | Contrats d'écran 34/35/36 |
| `41-Cartographie-existant-avant-refonte-et-raccord-UX.md` | Cartographie existant | `49` |

## Questionnaires & décisions intermédiaires (consolidés ailleurs)

| Fichier | Sujet | Décisions durables remontées dans |
|---|---|---|
| `28-Questions-arbitrage-avant-refonte-V1.md` | 26 arbitrages | `32` puis Backlog |
| `29-Prototype-frontend-V1-sans-backend.md` | Prototype HTML | `prototype-refonte-v1/` |
| `30-Questions-pour-atteindre-100-pourcent-refonte-frontend.md` | Registre préparation | `32` |
| `31-Analyse-charte-graphique-et-alignement-prototype.md` | Charte / tokens | `branding/` + tokens.css |
| `32-Consolidation-reponses-et-audit-matrice-DALKIA.md` | Consolidation 95/100 | Backlog |
| `33-Dernieres-questions-utilisateur-avant-contrats-ecran.md` | 6 choix Fluides | `34-Contrat-Fluides` |
| `39-Questions-avant-raccord-factures-matrices-V1.md` | Questions matrices | `49` |
| `42-Questions-ciblees-apres-cartographie-existant.md` | Questions cartographie | `43` → ADR 011 |
| `43-Decisions-apres-reponses-assistant-matrices-V1.md` | Décisions assistant matrices | **`../Decisions/011-...`** |
| `44-Questions-suite-refonte-matrices-factures.md` | Questions suite | `45` → ADR 011 |
| `45-Decisions-suite-refonte-matrices-factures.md` | Décisions suite | **`../Decisions/011-...`** |
| `46-Diagnostic-environnement-local-API-base.md` | Diagnostic env local | ADR 009 (staging) |
| `47-Plan-staging-refonte-V1-sans-docker-local.md` | Plan staging | ADR 009 (staging) |
| `48-Preview-Factures-decisions-V1.md` | Preview statique Factures | **`../49-Spec-...Factures`** (actif) |
