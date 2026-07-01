# Matrice comptable multi-tiers (DALKIA / ENGIE / EDF) — synthèse et décisions

> **À quoi sert ce fichier**
> Même principe que `factures-decisions-ux.md` et `marches-budget-decisions-ux.md` : je récapitule
> ce qui existe déjà, ce que j'ai vérifié en direct sur staging (pas de suppositions), et je pose les
> questions à trancher avant de coder. On répond directement dans ce fichier ou en conversation.
>
> Code existant : `saas/backend/app/models/accounting_matrix.py`,
> `saas/backend/app/services/accounting_matrix*.py`,
> `saas/frontend/src/features/matrices/MatrixAdminPageV1.tsx` ·
> Docs de référence : `38-Modele-backend-matrices-comptables-versionnees.md`,
> `35-Contrat-ecran-Factures-Decisions-V1.md`, `Decisions/010-...`, `Decisions/011-...`

---

## 1. Ce qui est déjà posé (architecture + décisions actées)

**Le socle technique est solide et ne demande pas à être refait** (ADR 010, doc 38) :
- Table `accounting_matrix_contracts` = **une matrice par contrat/lot/marché**, `accounting_matrix_versions`
  (une seule version `active` à la fois, jamais modifiée en place), `accounting_matrix_rules` (règles de
  ventilation), `invoice_accounting_snapshots` (imputation figée par facture, garde la version utilisée).
- Import/export XLSX déjà fonctionnel avec `stable_rule_key` pour l'aller-retour fiable (PR #27).
- Application à la facture + snapshot déjà fonctionnelle (PR #28).

**Décisions produit déjà actées (ADR 011, 2026-06-25)**, donc ta demande d'aujourd'hui n'est pas une
surprise — c'était déjà le plan, on l'exécute maintenant :
- Noyau V1 prioritaire explicitement acté : **DALKIA, ENGIE, EDF, TotalEnergies** (SUEZ/SPIE après).
- Rôles autorisés à écrire une matrice : tous **sauf** `FLUIDES`/`TECHNICIEN_CVC` (lecture ouverte à
  tous). Ton compte est maintenant `ADMIN` des deux côtés (staging + prod) — tu es autorisé.
- **Ce qui change aujourd'hui** : ADR 011 disait *« V1 : la compta complète un XLSX hors plateforme.
  Plus tard : accès plateforme limité lecture/écriture ciblée »*. Tu demandes maintenant l'édition
  **en ligne** directement — c'est une évolution assumée du plan, pas un retour en arrière. Je le note
  ici plutôt que de rouvrir l'ADR (rien de durable ne change dans le schéma, juste l'UX d'édition).

---

## 2. État réel des données (vérifié en direct sur staging, 2026-07-01)

### CPE DALKIA — matrice déjà créée, partiellement active

| Élément | Valeur |
|---|---|
| Contrats matrice `domain=cpe` | **7** (`C00025811F`, `C00025812G`, `C00032657J`, `C00107051V`, `C00157795L`, `C00190116O`, `C00190155J`) |
| Règles de nature comptable (`cpe_accounting_nature_rules`) | **43** |
| Mappings site → axes (`cpe_accounting_site_mappings`) | **75**, dont **75/75 (100 %)** avec service+opération renseignés |
| Règles générées par contrat (nature + site) | ~80 par contrat |
| Versions actives | **1 seul contrat actif** (`C00025811F`), les 6 autres en `draft` |

Natures déjà utilisées côté CPE (à réutiliser telles quelles, convention M14/M57 déjà en place) :
`60611` eau/assainissement · `60612` électricité · `60613` chauffage urbain · `60621` combustibles ·
`611` prestations de services · `6156` maintenance · `615221` bâtiments/investissement.

→ Ce que tu appelles « incomplet côté ville » concerne probablement soit la couverture des 43 règles
de nature (est-ce que tous les postes facturés DALKIA ont une règle ?), soit les 6 contrats non
encore activés. **Question Q1 ci-dessous.**

### ENGIE / EDF — quasiment tout est à construire

| Élément | Valeur |
|---|---|
| Contrats matrice `domain=fluides` | **0** — aucune matrice créée à ce jour |
| Règles de nature comptable (`energy_accounting_nature_rules`) | **0** |
| Mappings site → axes (`energy_accounting_site_mappings`) | **496** lignes, mais **0 % (0/496)** avec un axe rempli (service/fonction/antenne/opération tous vides) |

Concrètement : la liste des 496 PRM existe (probablement dérivée du patrimoine), mais **aucune n'est
rattachée à un service/une fonction/une antenne/une opération**, et **aucune règle ne dit à quelle
nature comptable correspond un poste facturé** (abonnement, consommation, TURPE, CSPE, CTA...).
C'est un chantier plus lourd que DALKIA, sur deux axes différents (nature + site).

---

## 3. Proposition de modèle de nature comptable ENGIE/EDF (arbitraire, à valider)

Les parseurs EDF/ENGIE distinguent déjà ces postes facturés (code en prod) :

| Famille | Poste | Nature comptable proposée |
|---|---|---|
| `electricity` | Fourniture électricité, Abonnement, Mécanisme de capacité, Contribution CEE | **60612 — Électricité** |
| `network` | Acheminement (TURPE part fixe), Dépassement de puissance souscrite | **60612 — Électricité** |
| `taxes` | CSPE, CTA Élec, Taxe communale (CCFE), Taxe départementale (DCFE) | **60612 — Électricité** |

**Justification** : en comptabilité M14/M57, l'acheminement (TURPE) et les taxes/contributions d'une
facture d'électricité ne sont **pas** des comptes séparés — c'est le même bien acheté (l'électricité
livrée), donc une seule nature 60612 pour toute la facture. C'est **exactement la convention déjà
utilisée côté CPE** (`Selon service vendu → 60612 électricité / 60611 eau / 60621 chauffage`), donc
cohérent avec l'existant, pas une invention isolée.

**Q2 — Cette proposition (tout ENGIE/EDF → nature unique 60612) te convient-elle, ou la Ville
distingue-t-elle déjà comptablement fourniture / acheminement / taxes sur des comptes différents ?**

---

## 4. Le vrai chantier : les axes analytiques (service/fonction/antenne/opération)

C'est le point le plus lourd : **496 sites ENGIE/EDF sans aucun axe renseigné**, contre 75/75 pour
CPE. Or c'est justement `operation_number` qui alimente le réalisé du nouveau module Budget
([marches-budget-decisions-ux.md](marches-budget-decisions-ux.md)) — sans ces axes, le budget
énergie restera vide même une fois la nature comptable posée.

**Q3 — Comment veux-tu attaquer ces 496 sites ?**
- (a) Import en masse depuis une source externe si elle existe (fichier finances déjà utilisé pour
  le patrimoine, export compta existant...) — précise si un tel fichier existe.
- (b) Dérivation automatique depuis le patrimoine (ex. type de bâtiment/service déjà connu dans
  `buildings`/`sites`) comme première passe, à corriger ensuite — je peux évaluer la faisabilité si
  tu valides cette piste.
- (c) Saisie manuelle progressive par la compta via export/import XLSX (comme prévu ADR 011),
  aucune automatisation.
- (d) On commence petit : un sous-ensemble prioritaire de sites (lesquels ?) plutôt que les 496 d'un coup.

---

## 5. Édition en ligne — ce qu'il faut construire côté écran

Aujourd'hui `/refonte-v1/matrices` (`MatrixAdminPageV1.tsx`) fait : lister les contrats, voir les
règles d'une version **en lecture seule**, exporter/importer un XLSX. Il n'y a **aucun formulaire**
pour ajouter/modifier une règle directement dans l'app (l'API le permet déjà côté backend,
`POST .../rules` et `PATCH .../rules/{id}`, juste pas branché à l'écran).

**Q4 — Niveau d'édition en ligne attendu pour cette itération ?**
- (a) Édition **ligne à ligne** dans un tableau (ajouter une règle, modifier nature/axes/% directement
  dans l'app) — remplace ou complète le circuit XLSX.
- (b) Édition **en masse simplifiée** : un formulaire pour appliquer une nature/des axes à un groupe
  de règles filtrées (ex. « toutes les règles ENGIE famille `taxes` → nature 60612 ») plutôt que
  ligne à ligne.
- (c) Garder le XLSX comme mode d'édition principal, ajouter juste un **lien direct** depuis chaque
  contrat vers son export/import (pas de formulaire dans l'app pour l'instant).

**Q5 — Le service finance édite-t-il dans l'app, ou toujours via export/import XLSX (juste rendu plus
accessible) ?** Ça détermine si on construit un vrai formulaire ou si on soigne seulement le circuit
XLSX + son accès depuis la page Marchés.

---

## 6. Séquencement proposé (si les réponses ci-dessus le confirment)

1. Répondre aux questions Q1-Q5 ci-dessus.
2. Créer les 1-3 matrices ENGIE/EDF (`domain=fluides`, une par fournisseur, cohérent avec le
   regroupement déjà utilisé côté CPE) + règles de nature (§3) — rapide, pas besoin des axes de site
   pour ça.
3. Construire l'édition en ligne retenue en Q4/Q5.
4. Attaquer les axes analytiques des 496 sites (§4, le plus gros morceau) selon l'option choisie en Q3.
5. Lier `/refonte-v1/marches` (budget) aux nouvelles matrices ENGIE/EDF une fois les axes posés, pour
   que le réalisé énergie apparaisse dans le suivi budget.

**Tes réponses :**
