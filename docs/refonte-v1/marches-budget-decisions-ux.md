# Marchés & Budget V1 — décisions UX (fichier de travail partagé)

> **À quoi sert ce fichier**
> Même principe que `factures-decisions-ux.md` : fichier commun, tenu à jour par Claude, pour la
> tranche « Budget par marché / suivi financier » (`/refonte-v1/marches`) et le sujet connexe
> « édition de la matrice comptable ». Une entrée = un sujet + une question. On répond directement
> dans ce fichier (ou en conversation), avant de coder la suite.
>
> Page budget : `saas/frontend/src/features/marches/MarketsBudgetPageV1.tsx` ·
> Page matrices : `saas/frontend/src/features/matrices/MatrixAdminPageV1.tsx` ·
> Cadrage : `refonte-v1/suivi-financier-budget-atterrissage-cadrage.md`

---

## 1. Bug bloquant constaté (2026-07-01)

Sur staging, le formulaire « Saisie du budget » n'apparaît pas quand tu cliques sur
DALKIA - C00025811F. Cause trouvée : ton compte staging (`pierreandre.borja@gmail.com`, id 1)
a le rôle `USER` en base, qui n'est **pas** dans la liste des rôles autorisés à écrire
(`ADMIN, SUPERADMIN, DIRECTION, RESPONSABLE_MAINTENANCE, PATRIMOINE, FINANCE, COMPTA, COMPTABILITE`).
Cette liste a été copiée telle quelle du module Matrices comptables existant — donc **le même
blocage existe probablement déjà sur `/refonte-v1/matrices`**, juste jamais remarqué parce que
les matrices actuelles ont été créées par seed/script plutôt que par saisie manuelle en UI.

**Q1 — Comment débloquer ?**
- (a) Je passe ton compte staging (et prod le moment venu) de `USER` à `ADMIN` en base — reflète
  que tu es le seul utilisateur/propriétaire du système aujourd'hui.
- (b) J'ajoute `USER` à la liste des rôles autorisés à écrire (matrices + budget) — moins propre
  sémantiquement, mais n'importe quel futur compte `USER` aurait aussi le droit d'écrire.
- (c) Autre chose (préciser) ?

→ *Recommandation Claude : (a).* `USER` est un rôle par défaut à la création de compte, pas un
rôle métier ; le jour où d'autres comptes existeront (Fluides, Technicien CVC...), on ne voudra
sûrement pas qu'un `USER` générique ait les droits d'écriture financière.

**Ta réponse :**

---

## 2. Matrice comptable — entrée pour l'éditer

**État constaté** (relecture du code, 2026-07-01) : l'édition de la matrice comptable
(`accounting_matrix_rules` — le lien entre un élément facturé et l'écriture comptable côté Ville)
**n'existe aujourd'hui que via un aller-retour XLSX** :
1. Exporter la version active en `.xlsx` depuis `/refonte-v1/matrices`.
2. L'éditer dans Excel (en dehors de l'app).
3. Réimporter le fichier complété → génère une nouvelle version **brouillon**.
4. Activer cette version brouillon manuellement.

Il n'y a **pas de formulaire d'édition ligne à ligne dans l'app** (pas de bouton « ajouter une
règle » ni « éditer cette règle » dans le tableau « Règles de la version »). L'API backend le
permet déjà (`POST /accounting-matrices/versions/{id}/rules`,
`PATCH /accounting-matrices/rules/{id}`), mais rien n'est branché côté écran.

L'entrée actuelle dans la navigation : section **« Référentiels & admin »** → **« Matrices
comptables »** (`/refonte-v1/marches` est dans une section différente, **« Moteurs métiers »**).
Donc aujourd'hui, depuis la page Marchés, il n'y a **aucun lien** vers la matrice du marché
sélectionné — il faut changer de section de nav et rechercher le bon contrat matrice.

**Q2 — Que veux-tu exactement ?**
- (a) Un **lien/raccourci direct** depuis la carte du marché sur `/refonte-v1/marches` vers sa
  matrice comptable (`/refonte-v1/matrices` avec le contrat déjà sélectionné), en gardant l'édition
  XLSX telle quelle pour l'instant ?
- (b) Une **édition ligne à ligne dans l'app** (formulaire ajouter/modifier une règle), sans passer
  par Excel, à un endroit à définir ?
- (c) Les deux : (a) maintenant, (b) plus tard ?
- (d) Autre chose (préciser où tu imaginais cette « entrée ») ?

**Ta réponse :**

---

## 3. Autres points en suspens du cadrage budget (rappel §7, non bloquants pour coder la suite)

Déjà tranchés le 2026-07-01 : marché pilote = DALKIA (CPE), granularité = annuelle, atterrissage
v1 = pro-rata temporel. Restent ouverts si besoin :

- **Engagé** : pas de source « commandes/marchés notifiés » aujourd'hui → v1 reste budget vs
  facturé uniquement, sans colonne « engagé ». Je pars sur cette hypothèse sauf avis contraire.
- **Référentiel des opérations** : aujourd'hui, `operation_number` se saisit en texte libre dans le
  formulaire budget (aucune liste déroulante). Si tu veux une liste des opérations existantes
  (issues de la matrice comptable) plutôt qu'une saisie libre, dis-le ici.

**Ta réponse (si besoin) :**
