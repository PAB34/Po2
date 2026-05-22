# Implémentation Po2 — Module CPE DALKIA (Phase 1)

tags: #implémentation #développement #Po2 #CPE #backend #frontend #migration

> Commit de livraison : **`043fd40`** — branche `main`  
> Date : 2026-05-22  
> Statut : ✅ En production (à migrer via `alembic upgrade head`)

---

## Périmètre réellement couvert

La Phase 1 implémente le **moteur de performance énergétique** du CPE, pas encore le contrôle complet du marché :

| Couvert au 22/05/2026 | À construire ensuite |
|-----------------------|----------------------|
| Sites CPE, relevés gaz, import DALKIA, prix gaz, DJU | Factures CPE et justificatifs rattachés par poste P1/P2/P3 |
| Calcul `NB / N'B / NC` | Rapprochement DALKIA vs GRDF pour fiabiliser les quantités P1 |
| Intéressement et pénalités énergétiques potentielles | Vérification des révisions P1/P2/P3 et des échéances |
| Vue énergétique multi-sites | Registre commun des écarts, avoirs, pénalités et validations |

Le frontend `/cpe` présente désormais ce découpage dans un **cockpit CPE** et conserve le bilan existant dans la vue `Performance et consommations`.

Voir [[10-Roadmap-Po2]] pour le plan de développement par poste.

---

## Preview export finances DALKIA

La premiere brique facturation ajoutee au cockpit `/cpe` est une analyse non persistante du CSV finances exporte depuis l'espace client DALKIA.

| Element | Implementation |
|---------|----------------|
| Endpoint | `POST /api/cpe/finances/preview` |
| Service | `services/cpe_finance_preview.py` |
| Frontend | bouton `Analyser l'export` dans le cockpit CPE |
| Sortie | marches, types de facture, contrats, montants, codes sites CPE detectes, alertes |

Ce preview est volontairement separe de l'import de releves gaz `POST /api/cpe/import/csv` :
- le CSV finances decompose les factures et plusieurs contrats ;
- le CSV releves alimente les consommations mensuelles QT ;
- les lignes finances doivent etre filtrees et rattachees au bon contrat avant persistance.

Voir [[13-Export-finances-DALKIA]] pour l'analyse de l'export du 22/05/2026.

## Import finances CPE DALKIA persiste

La tranche suivante persiste maintenant un registre exploitable pour le contrat CPE cible :

| Element | Implementation |
|---------|----------------|
| Filtre d'entree | Contrat DALKIA `C00190116O`, marches `P1`, `P2`, `P3` |
| Tables | `cpe_finance_import_batches`, `cpe_finance_invoices`, `cpe_finance_lines` |
| Endpoints | `GET/POST /api/cpe/finances/imports`, `GET /api/cpe/finances/imports/{id}`, `GET /api/cpe/finances/imports/{id}/lines` |
| Service | `services/cpe_finance_imports.py` |
| UI | cockpit `/cpe` : import du lot, resume P1 et table de rapprochement lignes/sites |

Le lot conserve le hash du fichier et evite de dupliquer un meme export reimporte. Les lignes retenues gardent la granularite DALKIA : facture, poste `P1/P2/P3`, service vendu, poste facture, montant, prix exposes, consommation/index s'ils existent et detail de prestation.

### Rapprochement site CPE

Chaque ligne porte maintenant :
- le code site detecte dans le detail DALKIA ;
- le site CPE trouve automatiquement quand le code est connu ;
- un statut de validation initial : `auto_matched`, `site_unknown` ou `site_code_missing`.

Cette table devient la file de reconciliation avant le controle contradictoire : un code inconnu n'est pas corrige silencieusement et une ligne sans code reste visible.

### Premiere vue P1

Le cockpit ouvre le controle P1 a partir des lignes persistees :
- total P1, types de factures `AC` / `DE` / autres et postes factures P1 ;
- lecture des accessoires exposes par DALKIA via les postes factures ;
- nombre de sites P1 rapproches et nombre de ces sites ayant deja un PCE ;
- nombre de lignes avec consommation ou index pour preparer le futur rapprochement GRDF.

Cette tranche ne valide pas encore un decompte P1. Elle rend visibles les acomptes, les decomptes, les accessoires et les trous de rapprochement necessaires avant le controle de prix et de volume.

---

## Architecture générale

```
Frontend /cpe          →  CpeDalkiaPage.tsx (bilan multi-sites)
Frontend /cpe/sites/:id →  CpeSiteDetailPage.tsx (saisie mois par mois)
                           ↕
API FastAPI /api/cpe/  →  api/routes/cpe.py
                           ↕
                        services/cpe.py        (calcul + CRUD)
                        services/cpe_import.py (import CSV)
                           ↕
DB PostgreSQL           →  cpe_sites
                           cpe_gaz_releves
                           cpe_prix_gaz
                           cpe_resultats_annuels
                           ↕ (lecture)
Fichier CSV             →  energie/DJU/dju_sete.csv (DJU quotidiens)
```

---

## Modèles de données

### `cpe_sites` — Référentiel des sites contractuels

| Colonne | Type | Description |
|---------|------|-------------|
| `code_site` | String(50) UNIQUE | Ex : `VDS-ENS 02`, `VDS-SPORT 03`, `CCAS 04` |
| `nom_site` | String(255) | Nom complet du bâtiment |
| `categorie` | String(20) | `ENS` / `SPORT` / `BAM` / `CULT` / `CCAS` |
| `nb_mwh_pci` | Float | NB contractuel (Annexe 5.1 AE) |
| `ecs_ref_m3_an` | Float | Volume ECS de référence (m³/an) |
| `q_ecs_mwh_pci_per_m3` | Float NULL | qECS (€/MWhPCI/m³) — null si inconnu |
| `dju_reference` | Float | 1 426,0 (fixe contractuellement) |
| `cible_elec_mwh` | Float NULL | Cible électricité (Annexe 5.2, info) |
| `tarif` | String(5) NULL | `T1` / `T2` / `T3` — type tarifaire GRDF (OS N°3) |
| `pce` | String(50) NULL | Identifiant PCE GRDF du compteur gaz |

> 65 sites présents dans le seed courant `scripts/seed_cpe_sites.py`, dont les ajouts OS N°3 CULT/CCAS.
> Voir [[12-OS3-Prix-gaz]] pour la liste complète PCE/tarif.

### `cpe_gaz_releves` — Relevés mensuels QT

| Colonne | Type | Description |
|---------|------|-------------|
| `cpe_site_id` | FK | Lien vers cpe_sites |
| `annee` + `mois` | Int | Contrainte UNIQUE sur (site, annee, mois) |
| `qt_mwh_pci` | Float NULL | Consommation gaz totale mensuelle (MWhPCI) |
| `volume_ecs_m3` | Float NULL | Volume ECS mensuel (m³) |
| `source` | String(30) | `csv_dalkia` / `grdf_api` / `saisie_manuelle` |

> Alimenté par import CSV DALKIA (5e jour ouvrable) ou saisie manuelle.  
> Prêt pour GRDF ADICT quand les droits d'accès seront obtenus.

### `cpe_prix_gaz` — Prix unitaire par tarif et par exercice

| Colonne | Type | Description |
|---------|------|-------------|
| `annee` | Int | Exercice |
| `tarif` | String(5) NULL | `T1` / `T2` / `T3` — unique(annee, tarif) |
| `pu_eur_mwh_pci` | Float | Prix en €/MWhPCI (converti depuis PCS × 1,1068) |
| `source` | String(30) | `os3_fixe` / `contrat_p1` / `saisie_manuelle` |

> **2026-2030** : prix fixes OS N°3 — pré-chargés via `scripts/seed_cpe_prix_gaz.py` (T1=118,50, T2=82,13, T3=78,42 €/MWhPCI).  
> **2031+** : révision annuelle via décompte définitif P1 DALKIA (15/02/N+1).  
> Conversion PCS→PCI : `Pu_PCI = Pu_PCS × 1,1068` (GRDF zone Languedoc-Roussillon).

### `cpe_resultats_annuels` — Résultats calculés

| Colonne | Type | Description |
|---------|------|-------------|
| `nb` | Float | NB de l'exercice |
| `dju_reels` | Float NULL | DJU mesurés (Open-Meteo/COSTIC) |
| `n_prime_b` | Float NULL | NB × (DJU_réels / 1426) |
| `qt_total` | Float NULL | Somme QT mensuelle |
| `nc` | Float NULL | QT – (m × qECS) |
| `pu_mwh` | Float NULL | Prix gaz de l'exercice |
| `ecart` | Float NULL | N'B – NC |
| `type_resultat` | String(20) | `interessement` / `penalite` / `equilibre` |
| `montant_ht` | Float NULL | Montant HT (€) |
| `p2_4_taux` | Float | 1,0 ou 0,5 |
| `alerte_revision_nb` | Boolean | Seuil 12% atteint |
| `statut` | String(20) | `partiel` / `calcule` / `valide` / `conteste` |

---

## Moteur de calcul — `services/cpe.py`

### Fonctions pures (sans effet de bord)

```python
calcul_n_prime_b(nb, dju_reels, dju_ref=1426.0) → float
    # N'B = NB × (DJU_réels / DJU_ref)

calcul_nc(qt, m, q_ecs) → float
    # NC = QT – (m × qECS)
    # Si q_ecs is None ou m=0 → NC = QT

calcul_interessement(n_prime_b, nc, pu) → dict
    # ecart = N'B – NC
    # Si ecart > 0 : I = ½ × min(ecart, N'B×15%) × Pu  → "interessement"
    # Si ecart < 0 : P = |ecart| × Pu                  → "penalite"
    # Retourne : {type_resultat, montant_ht, ecart, p2_4_taux}
```

### Lecture DJU

```python
get_dju_annuel(annee) → CpeDjuAnnuel
    # Lit energie/DJU/dju_sete.csv (colonne dju_chauffage_base_18)
    # Cumul des jours du 01/01 au 31/12 de l'exercice
```

### Calcul + persistance

```python
calculer_resultat_site(db, site_id, annee) → CpeResultatAnnuel
    # Lit DJU, prix gaz, relevés → calcule → upsert cpe_resultats_annuels

get_bilan_annuel(db, annee, city_id) → CpeBilanAnnuel
    # Vue consolidée tous sites (recalcul à la volée, sans persister)
```

---

## Import CSV DALKIA — `services/cpe_import.py`

Format d'entrée (DALKIA envoie avant le 5e jour ouvrable du mois) :

```
code_site;date_releve;qt_mwh_pci;volume_ecs_m3;etat_chauffe
VDS-ENS 02;2026-01-31;11.3;3.2;O
VDS-SPORT 03;2026-01-31;9.8;;O
```

**Colonnes reconnues** (insensibles à la casse, avec gestion des accents) :
- `code_site` — obligatoire
- `qt_mwh_pci` ou `consommation_gaz` ou `qt`
- `volume_ecs_m3` ou `ecs_m3`
- `etat_chauffe` ou `etat_marche` — O/N/1/0/True/False
- `date_releve` ou `date` — formats YYYY-MM-DD, MM/YYYY, YYYY-MM
- `annee` + `mois` — alternative à date_releve

**Séparateurs** : `;` `,` ou `\t` — détection automatique.

---

## Endpoints API — `api/routes/cpe.py`

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/cpe/sites` | Liste des sites CPE |
| POST | `/api/cpe/sites` | Créer un site |
| GET | `/api/cpe/sites/{id}` | Détail d'un site |
| PATCH | `/api/cpe/sites/{id}` | Modifier NB / qECS / actif |
| GET | `/api/cpe/sites/{id}/releves` | Relevés mensuels d'un site |
| POST | `/api/cpe/sites/{id}/releves` | Saisir / mettre à jour un relevé |
| POST | `/api/cpe/import/csv` | Import fichier CSV DALKIA |
| GET | `/api/cpe/dju/{annee}` | DJU réels de l'exercice |
| GET | `/api/cpe/prix-gaz/{annee}` | Prix unitaire gaz d'un exercice |
| POST | `/api/cpe/prix-gaz` | Saisir / modifier le Pu |
| GET | `/api/cpe/bilan/{annee}` | Bilan consolidé tous sites |
| POST | `/api/cpe/bilan/{annee}/calculer` | Recalculer + persister tous les sites |
| POST | `/api/cpe/sites/{id}/bilan/{annee}/calculer` | Recalculer un site |

---

## Frontend

### `/cpe` — `CpeDalkiaPage.tsx`

- 4 KPI : DJU réels vs référence, Pu saisi, total intéressement, total pénalités
- Bouton **"Recalculer le bilan"** → POST `/api/cpe/bilan/{annee}/calculer`
- Bouton **"Importer CSV DALKIA"** → POST `/api/cpe/import/csv`
- Saisie rapide du Pu (formulaire inline)
- Tableau tous sites : NB / N'B / NC / écart / résultat / montant / mois renseignés / statut
- Filtres par catégorie (ENS / SPORT / BAM / CULT)
- Totaux filtrés intéressement + pénalité

### `/cpe/sites/:id` — `CpeSiteDetailPage.tsx`

- Tableau mois par mois avec saisie inline
- Champs : QT (MWhPCI) + ECS (m³) optionnel
- Affiche la source (CSV / API / saisie)
- Total QT annuel + compteur mois renseignés

---

## Mise en service

```bash
# 1. Migrer la base de données (inclut migration 0020 — tarif/pce)
alembic upgrade head

# 2. Charger les 65 sites du seed CPE courant
#    Met aussi à jour tarif et pce sur les sites existants
python -m app.scripts.seed_cpe_sites --city-id 1

# 3. Charger les prix gaz OS N°3 (T1/T2/T3 pour 2026-2030)
python -m app.scripts.seed_cpe_prix_gaz

# Prévisualiser sans écrire :
python -m app.scripts.seed_cpe_sites --dry-run
python -m app.scripts.seed_cpe_prix_gaz --dry-run
```

Ensuite via l'interface `/cpe` :
1. Les **prix gaz 2026-2030 sont pré-chargés** (OS N°3 — T1/T2/T3 automatiquement appliqués par site)
2. **Importer le CSV** DALKIA mensuel (ou saisir mois par mois)
3. **Recalculer le bilan** → intéressement/pénalité calculé par site avec le bon Pu selon son tarif

---

## Données manquantes à compléter

| Donnée | Sites concernés | Action |
|--------|----------------|--------|
| `q_ecs_mwh_pci_per_m3` (qECS) | Tous sauf ENS13, ENS15, ENS17.04, ENS18 | Récupérer dans le BPU complet (Annexe 7 AE) |
| Prix gaz 2026-2030 (T1/T2/T3) | Tous exercices | ✅ Pré-chargés via `seed_cpe_prix_gaz.py` (OS N°3) |
| QT mensuels 2026 | Tous sites | Import CSV DALKIA chaque mois |
| NB des 10 nouveaux sites | CULT 02.01/02/03, CULT 05, CCAS 01/04/05/07/08 | Récupérer dans Annexe 5.1 CCAS du marché |
| qECS : ENS13=1,0 — ENS15=3,3 — ENS17.04=0,9 — ENS18=2,7 | Déjà chargés | ✅ |

> Tant que qECS est null, le moteur pose NC = QT (NC légèrement surestimé, côté sécurité pour la collectivité).  
> Les 10 nouveaux sites CCAS/CULT ont NB=0 par défaut — les calculs d'intéressement ne démarrent que quand NB > 0.

---

## Points d'attention OS N°3 (migration 0020)

- **Prix par tarif** : `get_prix_gaz(db, annee, tarif)` prend maintenant un 3e paramètre. Sans tarif → fallback sur `tarif=None` (Pu global). L'ancien code qui passait 2 args reste compatible grâce au défaut `tarif=None`.
- **Conversion PCS/PCI** : `PCS_PCI_RATIO = 1.1068` dans `services/cpe.py`. Les prix OS N°3 sont stockés **déjà convertis en PCI** dans `cpe_prix_gaz.pu_eur_mwh_pci`. La conversion est faite une seule fois à l'import via `seed_cpe_prix_gaz.py`.
- **Bilan annuel** : `get_bilan_annuel()` charge maintenant un dict `{tarif: pu}` pour l'année, et applique le prix du tarif de chaque site. Le champ `pu_mwh` de `CpeBilanAnnuel` retourne le prix T2 pour l'affichage KPI.
- **10 nouveaux sites** : les sites CCAS (01/04/05/07/08/09) et CULT (02.01/02.02/02.03/05) ont `nb_mwh_pci=0` → le calcul retourne `insuffisant` tant que NB n'est pas saisi. Pas d'impact sur les totaux.
- **BAM 09 anomalie** : tarif='T3' stocké mais prix affiché dans l'OS N°3 = 74,17 (T2). À trancher avec DALKIA. En attendant le calcul utilise T3 (78,42 €/MWhPCI).
- **Endpoint `/prix-gaz/{annee}`** : retourne maintenant une **liste** (`list[CpePrixGazOut]`) et non plus un objet unique. Le frontend a été mis à jour en conséquence.

---

## Points d'attention pour les IA développeurs

- Le **champ `annee`** dans `cpe_gaz_releves` est l'exercice civil (01/01→31/12), pas la saison de chauffe
- Les **DJU réels** sont lus en cumul annuel (Jan→Déc) depuis `dju_sete.csv` — méthode COSTIC base 18°C
- Si le CSV DALKIA contient des virgules comme séparateur décimal, `cpe_import.py` les convertit en points
- Le `p2_4_taux` est posé à 0,5 **automatiquement** dès qu'il y a pénalité (NC > N'B) — à valider manuellement avant de le transmettre à DALKIA
- L'alerte `alerte_revision_nb` à 12% (1 saison) est calculée ; le seuil 8% sur 2 saisons nécessitera l'historique N-1 (Phase 2)
- Le champ `statut = "valide"` doit être posé manuellement via PATCH avant d'émettre la facture/avoir vers DALKIA

---

## Liens

- [[10-Roadmap-Po2]] — roadmap et phases suivantes
- [[12-OS3-Prix-gaz]] — OS N°3 : prix fixe 5 ans, tarifs T1/T2/T3, PCE, CCAS
- [[03-Cibles-et-intéressement]] — formules contractuelles complètes
- [[04-Cibles-par-site]] — NB et qECS par site
- [[06-Facturation-et-indices]] — P1/P2/P3, Pu, indices de révision
- [[07-GTC-et-données]] — format CSV DALKIA attendu, APIs futures
- [[08-Gouvernance]] — calendrier des livrables DALKIA (alertes Phase 2)
