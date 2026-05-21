# Roadmap Po2 — Module CPE DALKIA

tags: #roadmap #développement #Po2 #CPE #intéressement #facturation #alertes

> Ce document liste les fonctionnalités à développer dans Po2 pour couvrir l'ensemble des enjeux contractuels du CPE DALKIA : contrôle des cibles, vérification des factures, pénalités, calendrier et pilotage APE.

---

## Vue d'ensemble des phases

```
Phase 1 — Q3 2026 : Moteur de cibles + calcul intéressement
Phase 2 — Q4 2026 : Vérificateur de factures + calendrier d'alertes
Phase 3 — 2027    : Simulation, benchmark, suivi APE
```

> **Urgence Phase 1** : la première période d'intéressement court du 01/01/2026 au 31/12/2026. La facture/avoir DALKIA doit arriver avant le 31/01/2027. Le moteur de calcul doit être opérationnel avant fin 2026.

---

## Phase 1 — Moteur de cibles énergétiques

### 1.1 Import GRDF ADICT → QT par site

- Intégrer l'API GRDF ADICT (accès en attente de formation/droits)
- Stocker les index gaz mensuels par compteur et par site (code site conforme [[04-Cibles-par-site]])
- Format attendu de DALKIA en parallèle : EXCEL + CSV, avant le 5e jour ouvrable du mois

**Modèle de données :**
```
GazIndex(site_id, compteur_id, date, index_kwh_pci, date_releve)
```

### 1.2 Calcul NC (consommation chauffage nette)

```python
NC = QT - (m × qECS)
```

- `QT` : consommation gaz totale site (MWhPCI, cumul annuel)
- `m` : volume ECS annuel produit par chaudière gaz (m³)
- `qECS` : coefficient de conversion ECS spécifique au site (MWhPCI/m³)
- Voir [[03-Cibles-et-intéressement]] pour les valeurs par site

### 1.3 Source DJU automatisée

- Intégrer un flux DJU base 18°C, station Montpellier (COSTIC ou Météo-France)
- Stocker les DJU mensuels → cumul annuel de chauffage
- DJU de référence contractuelle : **1 426 DJU** (1981-2010)
- Si publication COSTIC tardive : calculer DJU provisoires depuis relevés Météo-France

**Formule N'B :**
```python
N_prime_B = NB × (DJU_réels / 1426)
```

### 1.4 Calcul intéressement / pénalité

Voir [[03-Cibles-et-intéressement]] pour les formules complètes.

```python
ecart = N_prime_B - NC

if ecart > 0:   # DALKIA a économisé → intéressement
    I = 0.5 × min(ecart, N_prime_B × 0.15) × Pu
    type = "facture"
else:           # DALKIA a dépassé la cible → pénalité
    P = abs(ecart) × Pu
    type = "avoir"
```

- `Pu` : prix unitaire gaz de l'exercice (€/MWhPCI, issu de la facture P1)
- Intéressement plafonné à **½ × N'B × 15%**
- Pénalité : **sans plafond**
- P2.4 réduite à **50%** si pénalité → voir [[06-Facturation-et-indices]]

### 1.5 Alerte révision NB

Déclencher une alerte si les conditions de renégociation sont atteintes :
- Écart NC/NB > **8%** sur **2 saisons consécutives**
- Écart NC/NB > **12%** sur **1 saison**

---

## Phase 2 — Vérification contradictoire des factures

### 2.1 Vérificateur de révision P1 (gaz)

Formule contractuelle :
```
Pugaz = Pugaz0 × (a + b×PEG/PEG0 + c×TVD/TVD0 + d×CEE/CEE0 + e×TICGN/TICGN0)
```

- Stocker les valeurs publiées de PEG, TVD, CEE, TICGN chaque mois (avec source et date)
- Recalculer Pugaz indépendamment et comparer avec la facture DALKIA
- Résultat : **OK / écart / à contester**

### 2.2 Vérificateur de révision P2 (entretien/conduite)

```
P2 = P20 × (0,15 + 0,70 × ICHT-IME/ICHT-IME0 + 0,15 × FSD2/FSD20)
```

- Révision au 1er janvier de chaque année civile
- Valeurs de base (01/01/2025) : ICHT-IME = 141,4 — FSD2 = 169,8
- Vérifier les 4 acomptes trimestriels et l'absence de régularisation

### 2.3 Vérificateur de révision P3 (garantie totale)

```
P3 = P30 × (0,15 + 0,30 × ICHT-IME/ICHT-IME0 + 0,55 × BT40/BT400)
```

- Valeur de base (01/01/2025) : BT40 = 128,4
- Révision au 1er octobre de chaque saison

### 2.4 Répertoire des indices de révision

Stocker chaque mois les valeurs publiées :

| Indice | Source | Fréquence |
|--------|--------|-----------|
| ICHT-IME | INSEE (BDM) | Mensuelle |
| FSD2 | INSEE (BDM) | Mensuelle |
| BT40 | BSCC | Mensuelle |
| PEG | EIKON / ICIS | Quotidienne → moyenne mensuelle |

> Conserver source + date de publication pour reconstitution en cas de litige.

### 2.5 Calendrier contractuel avec alertes

Alertes automatiques sur les échéances DALKIA :

| Échéance | Livrable attendu | Pénalité si manquant |
|----------|-----------------|----------------------|
| 5e jour ouvrable/mois | Relevés compteurs (EXCEL + CSV) | 250 €/jour |
| 15 octobre N | Programme entretien préventif N+1 | 250 €/jour |
| 31 octobre N | Dernière facture P3 de l'exercice | 250 €/jour |
| 31 janvier N+1 | Factures/avoirs intéressement | 250 €/jour |
| 31 janvier N+1 | Bilan GMAO (préventif + correctif) | 250 €/jour |
| 31 janvier N+1 | Rapport IPMVP | 250 €/jour |
| 28 février N+1 | Mémoire annuel complet | 250 €/jour |
| 31 mars N+1 | Dernier acompte P2 | 250 €/jour |

Statut par livrable : **Attendu / Reçu / En retard / Contesté**

Voir [[08-Gouvernance]] pour le calendrier complet.

---

## Phase 3 — Pilotage avancé

### 3.1 Simulation de fin d'exercice

À partir des consommations connues (mois 1→N) et des DJU restants projetés :
- Estimer NC final de l'exercice
- Afficher la trajectoire : intéressement probable ou pénalité probable
- Utile dès le mois de septembre pour anticiper P2.4

### 3.2 Détection d'anomalies de consommation

Comparer pour chaque site :
- **M vs M-1** : variation anormale sur le mois
- **M vs M-1 de N-1** corrigé DJU : dérive annuelle

Un pic anormal = problème équipement ou fuite → à remonter en réunion hebdomadaire avec DALKIA.

### 3.3 Benchmark inter-sites (kWh/m²)

- Calculer les ratios de consommation par m² pour chaque site
- Comparer les bâtiments de même nature (écoles entre elles, gymnases entre eux)
- Identifier les outliers **avant DALKIA** → force de négociation lors des réunions trimestrielles

### 3.4 Suivi des APE (Actions de Performance Énergétique)

Chaque APE doit être réalisée avant le **31/12/2029** :
- Inventaire des APE par bâtiment avec statut (planifié / en cours / réalisé)
- Impact énergétique prévu vs mesuré (IPMVP Option B)
- Alerte si le planning global glisse vers 2029

Voir [[01-Structure-du-marché]] pour la liste des APE et [[08-Gouvernance]] pour les obligations IPMVP.

### 3.5 Rapport IPMVP automatisé

Générer automatiquement les éléments du rapport annuel IPMVP :
- Option A : économies gaz (NB/N'B/NC + calcul intéressement)
- Option B : impact des APE sur consommations électriques

---

## Données externes à intégrer

| Source | Donnée | Statut |
|--------|--------|--------|
| GRDF ADICT API | QT gaz mensuel par site | En attente droits d'accès |
| ENEDIS API | Consommation électricité par site | Déjà intégré |
| Météo-France / COSTIC | DJU mensuels base 18°C Montpellier | À intégrer |
| INSEE BDM | ICHT-IME, FSD2 | À intégrer |
| BSCC | BT40 | À intégrer |
| Marché PEG | Prix gaz (EIKON / ICIS) | À évaluer |
| GTC API DALKIA | Températures, statuts équipements | Sous réserve mise en place |

---

## Liens

- [[03-Cibles-et-intéressement]] — formules NB/N'B/NC et pseudo-code
- [[04-Cibles-par-site]] — valeurs NB contractuelles par site
- [[06-Facturation-et-indices]] — formules de révision P1/P2/P3 et indices
- [[07-GTC-et-données]] — APIs, formats de données, intégration technique
- [[08-Gouvernance]] — calendrier des livrables et obligations DALKIA
- [[05-Pénalités-et-sanctions]] — montants des pénalités par type de manquement
