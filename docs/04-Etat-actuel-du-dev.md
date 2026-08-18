---
type: state
status: actif
read_policy: toujours
source_of_truth: true
related:
  - 00-Index.md
  - 49-Spec-execution-refonte-Factures-Decisions-V1.md
  - Backlog.md
do_not_auto_read:
  - Archives/Journal-etat-dev-2026.md
---

# État actuel du développement

> Snapshot du **présent** : ce qui tourne en prod, les chantiers ouverts, et où reprendre.
> Détail chronologique des mises à jour passées → `Archives/Journal-etat-dev-2026.md` (ne pas lire par défaut).
> Détail par session → `Sessions/` (ne pas lire par défaut).

## 🔜 Reprise prochaine session

> Mise à jour : **2026-08-18** (session Claude — référentiel patrimoine historique ASTECH).

- **✅ EN PROD — Référentiel patrimoine historique (ASTECH)** (PR #98, migration **0070**) :
  nouvelle page **`/patrimoine/astech`** (menu Patrimoine) pour l'aller-retour avec le fichier
  patrimoine de la collectivité.
  - **Import** d'un export ASTECH : détection automatique de la feuille exploitable (`Feuil1`
    porte la clé `CODE_BIEN` renseignée, `BAT` l'a vidée), **en-têtes conservés à l'octet près**
    (contrainte de réinjection : ASTECH n'accepte le fichier modifié que si en-têtes et code bien
    sont inchangés), payload des 317 colonnes conservé pour le futur réexport. Import idempotent.
  - **Rapprochement** : réutilise `_site_similarity` (cvc.py, déjà en prod). L'adresse ne sert
    qu'à départager. Deux garde-fous : ambiguïté entre candidats proches (sauf nom identique) et
    plusieurs biens visant le même bâtiment.
  - **Écran unique** : file des biens à gauche, carte à droite avec **marqueur violet déplaçable**
    (seul le point sélectionné), et bouton **« Attribuer IGN »** qui réutilise tel quel
    `POST /buildings/{id}/ign-attachment`. Aucun moteur dupliqué, `/buildings/list` inchangé.
  - **Mesuré sur données réelles** : 866 lignes lues → 399 biens importés, 26 hors périmètre,
    **78 rattachés automatiquement**, 295 à traiter.
  - **Reste à faire — incrément 3** : le **réexport** ASTECH (feuille réduite, normalisation
    d'adresse, `REFCAD`, coordonnées à virgule décimale, feuille de traçabilité).
  - **En attente de la référente ASTECH** : périmètre exact importé (Q2), confirmation qu'ASTECH
    accepte un import de mise à jour par clé, largeur du champ `REFCAD`. Chacun est un
    **paramètre**, pas une hypothèse enfouie.
  - **Doc** : `refonte-v1/patrimoine-fichier-historique-rapprochement-decisions.md` (audit,
    décisions Q1-Q13, mapping des colonnes, hypothèses de travail).

> Reprise précédente : **2026-07-07** (session Claude — atterrissage électrique : révision BPU + budget sans N-1).

- **✅ EN PROD — Référentiels** : vue **BPU curée** (`BpuReferentielV1`, PR #43 mergée) dans le hub
  `/refonte-v1/referentiels` ; **DPGF DALKIA = pas de cure** (Q7 close, PR #44 : page déjà refondue, seul
  gain cosmétique pour un risque réel → sans suite). Chantier « moteur métier / référentiels » **terminé**.
- **✅ EN PROD — Atterrissage électrique** (`/refonte-v1/marches`, onglets ENGIE/EDF, service
  `app/services/engie_elec_budget_revise.py`) :
  - **Révision BPU par typologie** (PR #46) : le prix de référence est résolu par **typologie du marché
    Hérault Énergie** (tous fournisseurs), plus par fournisseur facturant → le ratio Y/N-1 marche quand
    l'attributaire change (ENGIE 2026 vs EDF 2025). Passé de 0 % à **100 % des PRM** révisés.
  - **Budget de référence sans historique N-1** (PR #47) : marché neuf (ENGIE démarré 2026) → bascule
    « année en vigueur » (prix Y + fourniture BPU × conso ENEDIS N-1). ENGIE 2026 réf. **136 € → ~1,14 M€**.
  - **Import granulaire typologies 2026** (PR #48, + **re-import BPU prod** `import_xlsx` fichier élec
    `force=True`) : `BATIMENT` collapse → **BATIMENT_HTA/BT/BT36** ; résolveur partagé par **jeu de codes
    candidats** (additif). Effet : **contrôle factures gagne C2/C4 bâtiments** (0→4/5, C5 5/5, zéro régression).
- **🟢 Finding B (EDF réalisé 2026 vide) = CLOS sans action** : décalage de facturation EDF (factures émises
  2026 = conso 2025, déjà en base). La conso 2026 n'est pas encore facturée ; l'atterrissage projette. RAS.
- **▶️ Prochaines étapes possibles** (rien de bloquant en attente) : (a) charger le **BPU gaz TE** en prod
  (absent ; fichier `_herault`, impact module gaz — tâche séparée) ; (b) **Suivi des indices/variables**
  (`/refonte-v1/marches`, transversal) ; (c) solder la **PR #32 factures** (validée staging, non mergée).
- **📄 Docs du chantier** : `atterrissage-bpu-elec-decisions.md` (§8-11 typologie), `atterrissage-elec-budget-sans-n1-decisions.md`,
  `bpu-import-granulaire-2026-decisions.md` (import granulaire + re-import).
- **🛠️ Env / infra** : **node dispo** (portable) → typecheck front via jonction `node_modules` + `tsc.cmd -b`.
  Déploiement staging via API : payload `{"ref":"main","inputs":{"ref":"<branche>"}}` (inputs.ref sinon
  déploie main). Staging = base SÉPARÉE `po2-staging-db` ; re-import BPU = `import_xlsx(..., force=True)`
  (remplacement propre du doc).

> Reprise **2026-07-06** (référentiels marchés) conservée pour trace :
> hub `/refonte-v1/referentiels` (PR #42) embarquant DPGF DALKIA + BPU ; vue BPU curée alors en cours (#43).
> Docs : `moteur-metier-referentiels-decisions.md` §0bis-0ter, `referentiel-bpu-ux-decisions.md` §4bis.

> Reprise précédente (**2026-07-03**, Codex/Claude — budget révisé élec + cadrage moteur métier) conservée
> ci-dessous pour trace. ⚠️ La cible « onglet Référentiel par tier » y est **supplantée** par le hub central.

- **PR #41 MERGÉE EN PROD** (santé 200) : atterrissage **ENGIE élec** + **EDF éclairage public** (moteur élec
  générique fixe/variable par PRM, conso attendue = ENEDIS + DJU thermosensible ENGIE / photopériode EDF,
  prix BPU+TURPE fallback N-1), **calque « Cible conso & intéressement » DALKIA** (`/refonte-v1/marches`),
  **tri des colonnes** (DALKIA/ENGIE/EDF/gaz), **fix parser ENGIE** (soutirage variable : montant mal placé
  dans la colonne prix), et **DJU auto-sync planifié** (Open-Meteo, `scheduler.py`). Aucune migration.
- **Données prod corrigées** : 52 lignes ENGIE soutirage variable (6,50 M€ → 1 224 €). Vérifié prod : ENGIE
  2026 réalisé 724 923 € (0 anomalie, ENEDIS 176 PRM) ; EDF 2026 prévision 87 816 € (ENEDIS 326).
- **Infra** : staging a désormais un volume `energie_data` inscriptible + `ENERGIE_DIR` (repo monté `:ro`) ;
  prod = bind mount déjà inscriptible. ⚠️ **ENEDIS sur staging = snapshot figé copié de prod** (pas de creds
  live) ; DJU se récupèrent seuls (Open-Meteo) partout maintenant.
- **⚠️ Action utilisateur en attente** : **importer le lot de factures ENGIE N-1 (2025)** (case « Importer et
  mettre à jour ») → sinon la prévision ENGIE reste ≈ 0 (prix non dérivables sans historique).
- **🎯 Prochain chantier = MOTEUR MÉTIER** : centraliser les **référentiels de marché DPGF/BPU** (DALKIA CPE +
  Hérault Énergies ENGIE/EDF/TotalE, à venir SUEZ/SPIE) sous `/refonte-v1/marches` (onglet **Référentiel** par
  tier), avec cohérence des adresses. **Audit complet écrit** → `docs/refonte-v1/moteur-metier-referentiels-marches-audit.md`.
  Aujourd'hui les référentiels sont éclatés en legacy : DPGF = `/cpe/dalkia-import`, BPU = `/energie/bpu`.
  **Décision structurante à prendre (Q1 du doc)** : regrouper BPU+DPGF sous « Marchés » (vision user) vs BPU
  sous « Énergie » (doc 13). Réutilise le backend existant (`cpe-dalkia-ref`, `bpu`) = portage UX.
- **Poste entreprise** : tests via `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 DATABASE_URL='sqlite:///./test.db' python -m pytest <tests_ciblés> -p no:cacheprovider`. npm/node absents → typecheck front via CI.

### Précédent — 2026-07-02 (handoff Codex)

> Detail complet -> `Sessions/2026-07-02 - Indices variables marches staging.md`.

- **PR #37 MERGEE EN PROD** : budget contractuel revise par coefficient trimestriel DALKIA (P2/P3, P1 gaz exclu).
- **PR #38 DRAFT SUR STAGING** (`codex/indices-variables`) : nouvelle vue lecture seule **Indices & variables** sur `/refonte-v1/marches` + endpoint `GET /api/marches/indices-variables?year_from=&year_to=`. CI verte (`backend`, `frontend`). Staging redeploye apres correction, health 200, revue UI Chrome OK.
- **Correction importante deja faite dans #38** : coefficients observes DALKIA agreges a **un point par marche/trimestre** (moyenne ponderee par `line_count`) pour eviter les lignes quasi dupliquees en table.
- **Prochaine decision** : l'utilisateur relit staging ; si OK, passer #38 ready puis merger `main` (prod auto) et surveiller prod. Ne pas merger prod sans accord explicite.
- **Suite fonctionnelle apres #38** : budget revise fiable en reconstitution **FIXE/VARIABLE**, maille **site/PRM**, en branchant les moteurs existants (gaz TotalEnergies conseille en premier, puis ENGIE/TURPE+BPU+ENEDIS, puis EDF cible a definir).
- **Poste entreprise** : `pytest.exe` peut bloquer en collecte. Utiliser `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, `DATABASE_URL=sqlite:///./test.db`, `python -m pytest <tests_cibles> -p no:cacheprovider`.

> **Contexte antérieur (2026-07-01 soir) — PR #32, #33, #34, #35 mergées sur `main` et déployées en PROD** (migration 0066 en prod).

- **État global** : tout le travail de la session est **en production** (`patrimoineaucarre.com`, santé 200) :
  - **Budget par marché v1** (PR #33) : `accounting_budget_lines` (migration 0066), API `/api/accounting-budget/*`, module front « Marchés » (`/refonte-v1/marches`). Décisions : pilote DALKIA, annuel, atterrissage pro-rata.
  - **Import codification DALKIA** (PR #34) : lit le « Code contrat » de la feuille « Poste facturé vers Nature ctpab » + colonnes de validation compta. Classeur canonique = `MATRICE_DALKIA-COMPATBILITE.xlsx`. Règle process « fil du dev » actée (05-Conventions §2 + AGENTS/CLAUDE).
  - **Matrice versionnée éditable** (PR #35) : `/refonte-v1/matrices` = fenêtre pleine page éditable (axes comptables, tri, colonnes redimensionnables, import/export). Édition directe version active (archivée figée). Colonne « Désignation site » (facture). Antenne DALKIA = code court. Enrichissement suggested_antenna via **référentiel CIRIL** (`saas/backend/app/data/index_compta.json`). `prefill_energy_matrices()` pré-remplit ENGIE/EDF (antenne 100%, service/fonction best-effort, opération vide car élec=fonctionnement).
- **⚠️ Données ENGIE/EDF : faites sur STAGING, PAS en PROD.** Le code `prefill_energy_matrices` + seed est déployé en prod mais **pas encore exécuté** (prod n'a aucune matrice seedée). Pour activer en prod : lancer via container `prefill_energy_matrices(db, city_id)` puis `seed_from_existing`, après validation. Idem la correction antenne DALKIA (UPDATE) : faite sur staging seulement.
- **Objectif probable prochaine session** : (1) décider si on **rejoue le setup matrices en prod** (DALKIA seed + ENGIE/EDF prefill) ; (2) **service/fonction best-effort** ne couvrent que ~10-18% des PRM (bâtiments typés) → la compta complète le reste via l'éditeur ; (3) **grille_9 CIRIL = pôle/direction « BÂTIMENTS »** — pas encore un axe de matrice, à intégrer si besoin ; (4) budget : réalisé fiable dépend toujours des extracteurs de lignes (PO2-FIN-001).
- **⚠️ Staging vs migrations** : la base staging était stampée `0066` par les déploiements de branche ; maintenant que `main` a `0066`, les déploiements staging depuis `main` sont cohérents.
- **À ne pas faire sans validation** : rejouer prefill/seed en prod sans accord ; confondre atterrissage financier et intéressement (`cpe_atterrissage.py`) ; toucher les fichiers Codex (`PRONO/*`, `knockout_mc.py`).
- **Niveau de confiance** : élevé (v1 codée et déployée conformément au cadrage validé ; reste la revue utilisateur sur staging avant merge).

## 🟢 Ce qui tourne en prod (https://patrimoineaucarre.com)

| Module | Route | État |
|---|---|---|
| Auth | `/login`, `/register`, `/account` | Stable |
| Patrimoine — liste / détail | `/buildings`, `/buildings/:id` | Stable ; rattachement manuel PRM/PCE/eau avec contexte fournisseur/contrat |
| Patrimoine — création / import hiérarchique | `/buildings/create-edit` | `SITE`→`Site`, `BATIMENT`→`Building.site_id`, `LOCAL`→`Local.building_id` |
| Patrimoine — rapprochements (file) | `/patrimoine/rapprochements` | PRM ENEDIS + PCE GRDF → candidat Bâtiment/Site, lien canonique |
| Gestion technique SYPEMI | `/buildings/technique` | Stable (310 équip.) + onglet Terrain (import CVC) |
| CVC fluides — cockpit F-Gaz / ESP | `/buildings/cvc-fluides` | Cockpit, Registre F-Gaz, Actions, ESP/DESP, Import |
| Énergie — vue / détail PRM / préconisations | `/energie`, `/energie/:prmId`, `/energie/preconisations` | Stable ; collecte ENEDIS sync de secours |
| Factures ENGIE/EDF | `/energie/factures`, `/energie/factures/:id` | Stable (parser XLSX ENGIE, contrôle BPU/TURPE/ENEDIS, décision, lots, 9 filtres facettes) |
| Factures gaz TotalEnergies | onglet Factures marché > Hérault Énergie | Import + contrôle cohérence/fourniture/acheminement/taxes |
| Facturation TURPE | `/energie/facturation` | Stable |
| CPE DALKIA | `/cpe` | Avancé : cockpit finance, contrôle factures, référentiel DALKIA, conso multi-fluides |
| BPU | `/energie/bpu` | Timeline · TURPE · Documents/Import · Édition tableau |
| Matrices comptables versionnées | API `/api/accounting-matrices/*` | Backend complet mergé `main` (schéma + XLSX + apply/snapshots) |
| Refonte React V1 (labo) | `/refonte-v1/*` | `/matrices` branché API réelle ; `/factures` **mergé `main`** (PR #32) ; `/marches` = budget par marché (PR #33) + onglet **« Budget contractuel (poste) »** (PR #36, non mergée) |
| Atterrissage budget contractuel CPE | API `/api/cpe/finances/contract-budget-landing` | PR #36 non mergée : budget contractuel (prévu DPGF) − réalisé (factures CPE) par poste ; calcul à la volée |

## 📦 Migrations alembic

HEAD prod constaté (2026-08-18) : **`0070_add_patrimoine_legacy_assets`** (référentiel patrimoine
historique ASTECH). Précédent : `0066_add_accounting_budget_lines` (budget par marché, maille opération, branche `feat/budget-marches` PR #33 — non encore sur `main`). Dernière migration sur `main` : `0065_add_supplier_contacts`.
Jalons : `0017` hiérarchie sites · `0041` seed CPE scope · `0048` CVC F-Gaz · `0056` rapprochements
patrimoine · `0057` gas_invoices · `0064` matrices. Liste complète prod → journal archivé.

## 🔥 Chantiers ouverts (présent)

| ID Backlog | Chantier | État / prochaine action |
|---|---|---|
| PO2-FIN-001 | Factures + matrice comptable + atterrissage | Backend matrices mergé ; reste extracteurs réels de lignes facture sur `apply`, droits par rôle. Bloque la fiabilité du réalisé du nouveau module Budget (PR #33) |
| PO2-FIN-002 | Budget par marché + suivi financier | v1 codée (PR #33, pilote DALKIA) : `accounting_budget_lines`, réalisé pro-rata, module « Marchés ». Reste : validation staging, merge, extension autres marchés, atterrissage physique doc 34 §F04 (v2) |
| PO2-UX-002 | Refonte frontend React V1 | Tranche `Factures & décisions` (doc 49) ; Phase 5 à brancher |
| PO2-CPE-001 | Contrôle factures DALKIA CPE | Reimport CSV, rattacher codes piscines, parser DPGF Lot 1/2 |
| PO2-FACT-001 | Audit facture ENGIE + socle EDF | Reimport XLSX force update, valider fiche liaison finance |
| PO2-PAT-003 | Rapprochements patrimoine | V1 livrée ; reste sources CPE/maintenance, cible Local, matching par adresse |
| PO2-ENEDIS-001 | ENEDIS async prod | Bloqué côté ENEDIS ; contournement sync de secours en place |
| PO2-GRDF-001 | Connecteur GRDF gaz | Scaffolding Phases 0-1 ; reste Phases 2-5 |

> Le détail complet des chantiers, dépendances et statuts vit dans `Backlog.md` (source de vérité du « quoi faire ensuite »).

## 📊 Données en prod (ordre de grandeur)

`cities` 1 (Sète) · `buildings` ~530 · `equipment_references` 310 · `bpu_documents` 17 / `bpu_price_components` 523 · `enedis_async_jobs` 0 (scheduler en attente du canal validé).

## ⚙️ Invariant gaz (2026-05-22)

- `BuildingMeterLink` = point central bâtiment → compteur multi-fluides.
- Le flux GRDF alimente PCE et consommations gaz quel que soit le fournisseur.
- BPU gaz HÉRAULT ÉNERGIE lot 7 importable comme référence `TOTALENERGIES` (compteurs Ville).
- La cotation OS3 gaz du P1 DALKIA reste dans le module CPE ; ne pas la fusionner avec la référence BPU TotalEnergies.

## 🔐 Secrets et accès

- **GitHub PAT** : `git credential fill` depuis la machine de l'utilisateur.
- **SSH VPS** : `~/.ssh/po2_vps2` → `ubuntu@135.125.152.112`.
- **Password FTP ENEDIS** : `/root/.ftp_password_enedis` sur le VPS (root only).
- **Clé AES ENEDIS** : `.env` prod `ENEDIS_DECRYPTION_KEY`. **Canal ENEDIS** : `506350699`.
- ⚠️ **Ne JAMAIS afficher de password/clé en clair** (chat, commit, vault).

## Liens utiles

- Pilotage : [[Backlog]] · [[03-Roadmap-fonctionnalites]]
- Tranche active : [[49-Spec-execution-refonte-Factures-Decisions-V1]]
- Décisions durables : [[Decisions/010-matrices-comptables-versionnees]] · [[Decisions/011-assistant-matrices-et-decisions-factures-V1]] · [[Decisions/012-auto-validation-et-semantique-controle-factures-V1]]
- Historique : `Archives/Journal-etat-dev-2026.md` · `Sessions/` *(ne pas lire par défaut)*
