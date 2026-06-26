# Plan staging refonte V1 sans Docker local

Date : 2026-06-25

## Decision

Ne pas chercher a installer Docker Desktop sur le poste entreprise. Docker n'est pas un outil portable simple : il requiert services systeme, virtualisation/WSL2/Hyper-V et droits eleves. Sur un poste entreprise, cela risque de bloquer ou de declencher des alertes securite.

La voie retenue pour tester les vraies donnees est donc :

1. previews UX locales sur `http://127.0.0.1:5173` ;
2. staging distant pour les donnees reelles ;
3. prod uniquement pour lecture/verification prudente, jamais comme bac a sable.

## Staging disponible

URL active testee :

- `https://staging.135-125-152-112.sslip.io`
- health API : `https://staging.135-125-152-112.sslip.io/api/health`

Resultat du test :

```json
{"status":"ok","app":"PatrimoineOp API (staging)","version":"0.1.0-staging"}
```

Le DNS `staging.patrimoineaucarre.com` ne resolvait pas au moment du test. Ce n'est pas bloquant, car `sslip.io` resout automatiquement vers l'IP du VPS.

## Role de chaque environnement

| Environnement | URL | Role |
|---|---|---|
| Local preview | `http://127.0.0.1:5173/refonte-v1/matrices-preview` | Valider UX sans backend |
| Local React | `http://127.0.0.1:5173` | Developpement frontend |
| Staging | `https://staging.135-125-152-112.sslip.io` | Tester branches + donnees reelles copiees |
| Production | `https://patrimoineaucarre.com` | Usage reel, pas de bac a sable |

## Regle de securite produit

Pour la refonte Matrices/Factures :

- les previews locales peuvent utiliser des donnees fictives ;
- les actions d'ecriture doivent etre testees sur staging ;
- la production ne doit pas servir a tester les mutations matrices/factures ;
- toute fonctionnalite qui genere/valide/exporte une decision doit etre testee sur staging avant merge/deploiement prod.

## Workflow recommande

### 1. Developper ou ajuster la preview locale

Exemple :

- `/refonte-v1/matrices-preview` pour UX Matrices ;
- future preview possible `/refonte-v1/factures-preview` pour UX Factures & decisions.

Objectif : valider la forme, les statuts, la lisibilite, la logique utilisateur.

### 2. Raccorder la vraie route React

Exemple :

- `/refonte-v1/matrices` raccordee a `/api/accounting-matrices/*` ;
- future `/refonte-v1/factures` raccordee aux snapshots comptables et controles factures.

Objectif : garder la preview pour discuter, mais faire vivre la vraie page sur API.

### 3. Deployer la branche sur staging

Workflow GitHub : `Deploy staging`

Input : nom de branche ou commit a deployer.

URL de test : `https://staging.135-125-152-112.sslip.io`

### 4. Valider sur donnees representatives

Pour Matrices :

- liste fournisseurs/contrats ;
- versions ;
- export XLSX ;
- import retour compta ;
- preview diff ;
- creation brouillon ;
- activation seulement si le flux est maitrise.

Pour Factures & decisions :

- facture nouvelle ;
- facture deja traitee ;
- facture reimportee identique ;
- facture reimportee modifiee ;
- controle OK/ecart ;
- imputation complete/incomplete ;
- decision utilisateur ;
- export finance.

## Garde-fous a conserver

1. Les connecteurs externes doivent rester coupes en staging sauf test volontaire.
2. Les credentials staging doivent etre distincts de la prod.
3. La base staging doit etre separee de la prod.
4. Les actions sensibles doivent rester protegees par role.
5. Les exports ou validations doivent produire une trace visible dans l'interface.

## Prochaine tranche recommandee

Construire une preview avancee `Factures & decisions V1`, puis la raccorder progressivement aux endpoints existants.

Le parcours cible :

> Import facture -> parsing -> controle facture -> proposition matrice comptable -> decision -> historique -> export finance.

Cette tranche doit etre concue en gardant en tete les fournisseurs V1 :

- DALKIA ;
- ENGIE ;
- EDF ;
- TotalEnergies.

## Decision immediate

Utiliser le staging `sslip.io` comme environnement de verification reelle. Le local reste dedie a l'UX et au frontend, sans tenter d'installer Docker sur le poste entreprise.