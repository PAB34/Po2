# Implémentation Po2 — Module CPE DALKIA (Phase 1)

tags: #implémentation #développement #Po2 #CPE #backend #frontend #migration

> Commit de livraison : **`043fd40`** — branche `main`  
> Date : 2026-05-22  
> Statut : ✅ En production (à migrer via `alembic upgrade head`)

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
| `code_site` | String(50) UNIQUE | Ex : `VDS-ENS 02`, `VDS-SPORT 03` |
| `nom_site` | String(255) | Nom complet du bâtiment |
| `categorie` | String(20) | `ENS` / `SPORT` / `BAM` / `CULT` |
| `nb_mwh_pci` | Float | NB contractuel (Annexe 5.1 AE) |
| `ecs_ref_m3_an` | Float | Volume ECS de référence (m³/an) |
| `q_ecs_mwh_pci_per_m3` | Float NULL | qECS (€/MWhPCI/m³) — null si inconnu |
| `dju_reference` | Float | 1 426,0 (fixe contractuellement) |
| `cible_elec_mwh` | Float NULL | Cible électricité (Annexe 5.2, info) |

> 54 sites pré-chargés via `scripts/seed_cpe_sites.py` depuis l'Annexe 5.1 AE.

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

### `cpe_prix_gaz` — Prix unitaire annuel (Pu)

| Colonne | Type | Description |
|---------|------|-------------|
| `annee` | Int UNIQUE | Exercice |
| `pu_eur_mwh_pci` | Float | Prix moyen €/MWhPCI |
| `source` | String(30) | `contrat_p1` / `saisie_manuelle` |

> Issu du décompte définitif P1 DALKIA (facture au 15/02/N+1). Saisie manuelle en attendant.

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
# 1. Migrer la base de données
alembic upgrade head

# 2. Charger les 54 sites contractuels (Annexe 5.1 AE)
python -m app.scripts.seed_cpe_sites --city-id 1

# Prévisualiser sans écrire :
python -m app.scripts.seed_cpe_sites --dry-run
```

Ensuite via l'interface `/cpe` :
1. **Saisir le Pu** — prix unitaire gaz de l'exercice (décompte définitif P1 au 15/02/N+1)
2. **Importer le CSV** DALKIA mensuel (ou saisir mois par mois)
3. **Recalculer le bilan** → intéressement/pénalité calculé par site

---

## Données manquantes à compléter

| Donnée | Sites concernés | Action |
|--------|----------------|--------|
| `q_ecs_mwh_pci_per_m3` (qECS) | Tous sauf ENS13, ENS15, ENS17.04, ENS18 | Récupérer dans le BPU complet (Annexe 7 AE) |
| Pu gaz 2026 | Exercice 2026 | Saisir après réception décompte P1 (15/02/2027) |
| QT mensuels 2026 | Tous sites | Import CSV DALKIA chaque mois |
| qECS : ENS13=1,0 — ENS15=3,3 — ENS17.04=0,9 — ENS18=2,7 | Déjà chargés | ✅ |

> Tant que qECS est null, le moteur pose NC = QT (NC légèrement surestimé, côté sécurité pour la collectivité).

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
- [[03-Cibles-et-intéressement]] — formules contractuelles complètes
- [[04-Cibles-par-site]] — NB et qECS par site
- [[06-Facturation-et-indices]] — P1/P2/P3, Pu, indices de révision
- [[07-GTC-et-données]] — format CSV DALKIA attendu, APIs futures
- [[08-Gouvernance]] — calendrier des livrables DALKIA (alertes Phase 2)
