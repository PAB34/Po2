# 37 — Plan de migration React refonte V1

> Date : 2026-06-25  
> Statut : plan de chantier avant codage  
> Objectif : transformer le prototype `docs/prototype-refonte-v1/` en frontend React raccordable, sans casser l’application existante.

## Décision de principe

La refonte ne doit pas remplacer brutalement le frontend actuel. Elle doit être construite en parallèle, sous une architecture propre, puis raccordée tranche par tranche.

Raison : beaucoup de fonctionnalités existent déjà, mais le frontend actuel mélange pages historiques, logique métier dense, appels API et styles globaux. Une bascule directe créerait un risque inutile sur les imports, les contrôles facture et les pages CPE/énergie déjà utiles.

## Périmètre de la première tranche

La première tranche React V1 couvre :

1. le shell produit moderne ;
2. le cockpit par profil ;
3. Factures & décisions ;
4. Fluides ;
5. Sites 360° ;
6. les composants communs nécessaires à ces écrans.

Les modules CPE détaillé, SPIE, technique avancée, administration, imports lourds et écrans historiques restent accessibles pendant la migration.

## Routes cibles

| Route cible | Rôle | Source prototype | État recommandé |
|---|---|---|---|
| `/` | Cockpit V1 | Cockpit personnalisé + chaîne de décision | Remplacer progressivement `HomePage` |
| `/factures` | Factures & décisions | Import, décision, matrices comptables | Refondre en premier après le shell |
| `/fluides` ou `/energie` | Portefeuille Fluides | Page Fluides du prototype | Conserver alias `/energie` si nécessaire |
| `/sites` ou `/patrimoine/sites` | Portefeuille Sites 360° | Vue Sites 360° | À créer sans supprimer `/buildings/list` au départ |
| `/sites/:siteId` | Fiche Site 360° | Drill-down Site 360° | À brancher progressivement sur patrimoine réel |
| `/marches` | Marchés & contrats | À détailler plus tard | Garder page existante provisoire |
| `/technique` | Technique & PPT | À détailler plus tard | Garder page existante provisoire |

## Architecture frontend proposée

Créer une zone V1 progressive dans `saas/frontend/src` :

```text
src/
  app/
    AppShellV1.tsx
    navigationV1.ts
  design-system/
    tokens.css
    components/
      Button.tsx
      Card.tsx
      Drawer.tsx
      KpiCard.tsx
      StatusBadge.tsx
      DataTable.tsx
      FilterBar.tsx
      SegmentControl.tsx
  features/
    cockpit/
      CockpitPage.tsx
      cockpit.mock.ts
      cockpit.types.ts
    invoices/
      InvoicesDecisionPage.tsx
      AccountingMatrixDrawer.tsx
      InvoiceDecisionDrawer.tsx
      invoices.mock.ts
      invoices.types.ts
    fluids/
      FluidsPortfolioPage.tsx
      SubscriptionDrawer.tsx
      fluids.mock.ts
      fluids.types.ts
    sites/
      SitesPortfolioPage.tsx
      Site360Page.tsx
      sites.mock.ts
      sites.types.ts
```

Ce découpage évite de continuer à grossir `App.tsx`, `api.ts` et `styles.css`.

## Design system à extraire du prototype

### Tokens

- bleu nuit PO² : `#1D3150` ;
- vert accent : `#74B44A` ;
- gris techniques ;
- ambre pour arbitrage ;
- corail pour anomalie ;
- thème clair/sombre via variables CSS ;
- titres Montserrat, texte Source Sans Pro ou police système compatible.

### Composants prioritaires

| Composant | Usage | Priorité |
|---|---|---:|
| `AppShellV1` | navigation, topbar, profil, thème | P0 |
| `KpiCard` | cockpit, fluides, sites | P0 |
| `Panel` / `Card` | structure des écrans | P0 |
| `StatusBadge` | conforme, anomalie, à valider, info | P0 |
| `Drawer` | fiche facture, matrice, abonnement | P0 |
| `DataTable` | factures, sites, matrices | P0 |
| `FilterBar` | recherche/filtres | P1 |
| `DecisionRail` | chaîne de décision cockpit | P1 |
| `EvidenceList` | trace de contrôle et preuves | P1 |

## Données mockées puis raccordement

La première passe React doit fonctionner avec des mocks typés. Ensuite seulement, les mocks sont remplacés par React Query + API.

| Domaine | Mock initial | API/raccordement prévu |
|---|---|---|
| Cockpit | `cockpit.mock.ts` | agrégations à créer depuis factures, fluides, budget, CVC |
| Factures | `invoices.mock.ts` | endpoints existants factures ENGIE/EDF/Total/DALKIA à unifier |
| Matrices comptables | `invoices.mock.ts` | modèle backend à créer : contrat, version, règles, snapshot facture |
| Fluides | `fluids.mock.ts` | ENEDIS/GRDF existants + futur portefeuille multi-fluides |
| Abonnements | `fluids.mock.ts` | moteur puissance/CAR/eau à créer ou consolider |
| Sites | `sites.mock.ts` | patrimoine, bâtiments, compteurs, CVC, contrats |

## Ordre de chantier recommandé

### Incrément 1 — Socle visuel sans backend

- créer tokens CSS V1 ;
- créer composants communs ;
- intégrer logo PO² ;
- créer `AppShellV1` ;
- brancher une route de test interne ou remplacer `HomePage` uniquement si stable ;
- conserver les routes historiques.

Validation : build frontend.

### Incrément 2 — Cockpit mocké

- créer `CockpitPage` ;
- reprendre les KPI par profil ;
- reprendre la chaîne de décision V1 ;
- ajouter thème auto/sombre/clair ;
- ne pas encore appeler le backend.

Validation : navigation, responsive, build.

### Incrément 3 — Factures & décisions mocké

- créer `InvoicesDecisionPage` ;
- intégrer workflow import → contrôle → imputation → décision ;
- ajouter drawer facture ;
- ajouter drawer matrice comptable ;
- garder `EnergieInvoicesPage` disponible tant que le raccordement n’est pas terminé.

Validation : build + comparaison métier avec contrat d’écran 35.

### Incrément 4 — Premier raccordement réel Factures

- identifier un DTO commun de facture ;
- mapper ENGIE/EDF/Total/DALKIA vers une structure unique ;
- conserver les détails spécifiques en sous-sections ;
- brancher progressivement la trace de contrôle existante ;
- ne pas bloquer la V1 sur CIRIL, confirmé hors périmètre.

Validation : échantillon réel par fournisseur.

### Incrément 5 — Fluides et Sites 360°

- porter les pages mockées ;
- raccorder d’abord les données déjà fiables ;
- afficher explicitement les zones `À construire` pour l’eau, SPIE ou les moteurs non terminés ;
- relier Site 360° aux compteurs, factures et équipements quand les identifiants sont disponibles.

## Points de vigilance

### 1. Ne pas confondre Énergie et Fluides

Le libellé produit doit devenir Fluides, car l’eau arrivera. Les routes historiques `/energie` peuvent rester comme alias technique pendant la transition.

### 2. Ne pas faire du cockpit une page statique

Chaque alerte doit être ouvrable et traçable. Le cockpit doit être une file de décisions, pas un tableau PowerPoint.

### 3. Ne pas perdre les versions

Factures, matrices comptables, contrats, barèmes, DJU et recommandations doivent porter une version ou une date d’effet. Une décision doit conserver la preuve consultée au moment où elle est prise.

### 4. Ne pas tout raccorder avant de stabiliser l’UX

Les mocks typés sont utiles. Ils permettent de construire proprement l’interface avant de lutter contre toutes les variations API.

### 5. Ne pas casser les pages utiles existantes

Les anciennes pages restent des roues de secours jusqu’à ce que la nouvelle tranche soit validée sur cas réels.

## Critères de sortie de la première tranche

La première tranche est prête quand :

- le shell V1 est utilisable au quotidien ;
- le cockpit affiche les décisions prioritaires ;
- Factures & décisions fonctionne au moins sur un fournisseur raccordé ;
- la matrice comptable est visible ou simulée sans ambiguïté ;
- Fluides distingue bien distributeurs, fournisseurs, DJU et abonnements ;
- Site 360° donne le contexte transversal ;
- le build frontend passe ;
- l’ancien parcours reste accessible tant que le nouveau n’est pas complet.

## Prochaine action Codex

Commencer l’incrément 1 : créer le socle frontend V1 dans `saas/frontend/src` avec tokens, composants communs minimaux et shell moderne, en gardant l’application existante fonctionnelle.


## Avancement incrément 1 - 2026-06-25

Socle créé dans `saas/frontend/src` :

- `design-system/tokens.css` : variables PO², thème automatique sombre via `prefers-color-scheme`, styles de base des composants ;
- `design-system/components/` : `Button`, `Card`, `KpiCard`, `StatusBadge`, `Drawer`, `DataTable`, `FilterBar`, `SegmentControl` ;
- `app/navigationV1.ts` : navigation cible Pilotage / Métiers / Ressources ;
- `app/AppShellV1.tsx` : shell V1 prêt à être utilisé sans remplacer encore `App.tsx` ;
- `features/cockpit/` : première page cockpit mockée, avec KPI et décisions prioritaires ;
- `main.tsx` importe désormais les tokens V1 avant le CSS historique.

Choix volontaire : ne pas brancher encore `AppShellV1` sur les routes existantes. Le socle est posé, mais l’application actuelle reste le chemin de production jusqu’à validation du premier écran V1.

Validation : `npm install` a installé les dépendances frontend, puis `npm run build` est passé avec succès le 2026-06-25. Le build signale seulement un avertissement de taille de bundle (> 500 kB) à traiter plus tard par découpage dynamique. `npm audit` signale 4 vulnérabilités hautes ; aucune correction automatique `--force` n’a été appliquée pour éviter une montée de versions non maîtrisée.


## Route laboratoire /refonte-v1

Une route protégée `/refonte-v1` a été ajoutée pour afficher le shell V1 et le cockpit mocké sans remplacer le parcours actif. Elle sert de banc d’essai pendant la migration.

Important : cette route n’est pas encore ajoutée à la navigation principale. Elle peut afficher le shell V1 à l’intérieur du shell historique tant que la bascule globale n’est pas faite ; c’est acceptable pour un laboratoire, pas pour la version finale.


## Avancement Factures V1 mockées - 2026-06-25

La première surface métier après le cockpit est portée en React mocké :

- `features/invoices/invoices.types.ts` ;
- `features/invoices/invoices.mock.ts` ;
- `features/invoices/InvoicesDecisionPageV1.tsx` ;
- route laboratoire `/refonte-v1/factures` via `pages/RefonteV1InvoicesPage.tsx`.

Le shell V1 accepte maintenant un `routePrefix` pour que la navigation du laboratoire reste sous `/refonte-v1` sans renvoyer vers les routes historiques.

Validation : `npm run build` réussi après ajout de la page Factures V1. Avertissement restant : chunk principal Vite > 500 kB.


## Avancement Fluides et Sites V1 mockés - 2026-06-25

Les deux surfaces restantes du premier lot laboratoire ont été portées en React mocké :

### Fluides

- `features/fluids/fluids.types.ts` ;
- `features/fluids/fluids.mock.ts` ;
- `features/fluids/FluidsPortfolioPageV1.tsx` ;
- route laboratoire `/refonte-v1/fluides`.

La page couvre : KPI fluides, dérives prioritaires, atterrissage annuel, surveillance des abonnements, distinction source distributeur / contrat fournisseur.

### Sites 360°

- `features/sites/sites.types.ts` ;
- `features/sites/sites.mock.ts` ;
- `features/sites/SitesPortfolioPageV1.tsx` ;
- route laboratoire `/refonte-v1/sites`.

La page couvre : portefeuille sites, recherche, sélection d’un site, synthèse site et décisions reliées au site.

### Shell laboratoire

`AppShellV1` mappe désormais les entrées du menu vers :

- `/refonte-v1` ;
- `/refonte-v1/factures` ;
- `/refonte-v1/fluides` ;
- `/refonte-v1/sites`.

Les entrées non encore portées restent dirigées vers les routes historiques.

Validation : `npm run build` réussi après ajout de Fluides et Sites. Avertissement restant : chunk principal Vite > 500 kB.


## Avancement DTO Facture V1 - 2026-06-25

Une couche de transition a été ajoutée pour préparer le raccordement réel de `/refonte-v1/factures` :

- `features/invoices/invoiceDecisionV1.types.ts` : DTO commun `InvoiceDecisionV1`, preuve `InvoiceProofV1`, statuts décision et statuts matrice ;
- `features/invoices/invoiceDecisionV1.adapters.ts` : adaptateurs depuis les modèles frontend existants `EnergyInvoiceImport`, `GasInvoice` et `CpeFinanceInvoice` ;
- `features/invoices/invoices.types.ts` réexporte les types communs pour limiter les changements dans la page ;
- `features/invoices/invoices.mock.ts` utilise désormais le DTO commun ;
- `InvoicesDecisionPageV1` est alignée sur `stableId`, `invoiceNumber`, `siteLabel`, `contractLabel`, `amountTtcLabel`, `proofs`.

Validation : `npm run build` réussi après ajout des adaptateurs.

### Prochain raccordement recommandé

Créer un hook `useInvoiceDecisionsV1` qui :

1. appelle `fetchEnergyInvoiceImports`, `fetchGasInvoices`, puis `fetchCpeFinanceInvoices` si le périmètre DALKIA doit être inclus ;
2. applique les adaptateurs ;
3. fusionne et trie par statut, échéance et date de facture ;
4. garde `invoicesMock` en fallback si les endpoints ne sont pas disponibles.

Ne pas écrire directement les appels API dans `InvoicesDecisionPageV1` : elle doit rester une surface de présentation et décision.


## Avancement hook Factures V1 - 2026-06-25

Le raccordement progressif de `/refonte-v1/factures` a commencé avec un hook dédié :

- `features/invoices/useInvoiceDecisionsV1.ts` ;
- appels préparés vers `fetchEnergyInvoiceImports`, `fetchGasInvoices`, `fetchCpeFinanceInvoices` ;
- usage de `Promise.allSettled` pour éviter qu’une source indisponible bloque toute la page ;
- fallback automatique vers `invoicesMock` si aucun endpoint ne répond ou si aucun token n’est présent ;
- tri par statut, échéance puis numéro de facture ;
- `InvoicesDecisionPageV1` consomme maintenant `invoices`, `isFetching` et `isUsingFallback` depuis ce hook.

Validation : `npm run build` réussi.

Limite volontaire : la page affiche encore des matrices comptables mockées ; le backend des matrices contractuelles versionnées reste à créer.


## Avancement synthèse Matrices V1 - 2026-06-25

Une couche frontend de synthèse des matrices comptables a été ajoutée :

- `features/invoices/accountingMatrixV1.ts` ;
- lecture des matrices énergie existantes via `fetchEnergySiteMappings` et `fetchEnergyNatureRules` ;
- lecture des matrices CPE existantes via `fetchCpeAccountingSiteMappings` et `fetchCpeAccountingNatureRules` ;
- synthèse en `AccountingMatrixSummary` pour affichage V1 ;
- fallback vers `accountingMatricesMock` pour EDF/TotalEnergies/DALKIA lorsque les sources réelles sont absentes ;
- `InvoicesDecisionPageV1` affiche si la matrice vient de la synthèse API ou des mocks.

Validation : `npm run build` réussi.

Limite importante : cette synthèse ne remplace pas le futur modèle durable de matrice versionnée. Elle agrège les codifications existantes pour avancer côté UX. Le backend cible devra gérer : contrat, lot, version, dates d’effet, lignes/règles, statut de validation, import/export XLSX, diff avant réimport et snapshot appliqué à la facture.

## Avancement cadrage backend Matrices V1 - 2026-06-25

Le document 38 précise le modèle durable nécessaire derrière la synthèse React actuelle : matrice par contrat, versions datées, règles, import/export XLSX, aperçu de différences et snapshots immuables appliqués aux factures.

Point important : la synthèse frontend actuelle des matrices reste une couche de transition construite depuis les codifications énergie/CPE existantes. Elle ne remplace pas le futur backend versionné.

Prochaine action recommandée : implémenter le backend minimal des matrices versionnées avant de raccorder définitivement /refonte-v1/factures aux règles comptables.


## Avancement backend matrices versionnées - 2026-06-25

La structure backend durable des matrices comptables est posée (tranche minimale), conformément au cadrage `docs/38-Modele-backend-matrices-comptables-versionnees.md`.

Livré dans `saas/backend` : modèles `accounting_matrix_contracts/versions/rules` + `invoice_accounting_snapshots`, schémas Pydantic, service portant les invariants versionnés, router `/api/accounting-matrices/*` (lecture, création contrat/version, activation/archivage, règles, snapshot facture en lecture) et migration `0064_add_accounting_matrices`.

Invariant respecté : une version active n'est jamais écrasée ; toute évolution passe par une nouvelle version (clone possible) puis une activation explicite qui archive l'ancienne active.

Différé phase suivante : import/export XLSX, application/écriture des snapshots (`apply`, `validate-snapshot`), seed depuis l'existant énergie/CPE, puis bascule de `/refonte-v1/factures` vers ces endpoints (remplacement de `useAccountingMatricesV1`).

Validation : `py_compile` OK ; runtime FastAPI et migration Alembic à valider en CI (deps absentes du poste). Détail dans le doc 38, section « Implémentation backend minimale ».
