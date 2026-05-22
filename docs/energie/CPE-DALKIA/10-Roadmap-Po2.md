# Roadmap Po2 — Module CPE DALKIA

tags: #roadmap #développement #Po2 #CPE #intéressement #facturation #alertes

> Ce document liste les fonctionnalités à développer dans Po2 pour couvrir l'ensemble des enjeux contractuels du CPE DALKIA : contrôle des cibles, vérification des factures, pénalités, calendrier et pilotage APE.

---

## Vue d'ensemble des phases

| Phase | Période | Statut |
|-------|---------|--------|
| Phase 1 — Moteur de cibles + calcul intéressement | Q2-Q3 2026 | ✅ **LIVRÉ** — commit `043fd40` |
| Phase 2 — Vérificateur de factures + calendrier d'alertes | Q4 2026 | 🔲 À faire |
| Phase 3 — Simulation, benchmark, suivi APE | 2027 | 🔲 À faire |

> **Urgence Phase 1** : la première période d'intéressement court du 01/01/2026 au 31/12/2026. La facture/avoir DALKIA doit arriver avant le 31/01/2027. ✅ Moteur opérationnel.

Voir [[11-Implémentation-Po2]] pour le détail technique de ce qui a été construit.

---

## Recentrage du module au 22/05/2026

Le développement déjà livré est utile, mais il couvre surtout le **contrôle de performance énergétique gaz** :
- relevés mensuels DALKIA ou saisie manuelle ;
- calcul des cibles corrigées DJU `NB / N'B / NC` ;
- estimation de l'intéressement et des pénalités énergétiques.

L'entrée `/cpe` ne doit pas laisser croire que ce moteur constitue à lui seul le suivi complet du CPE. Le pilotage cible doit distinguer :

| Axe | Objet de contrôle | Données principales |
|-----|-------------------|---------------------|
| Performance et consommations | Écarts DALKIA vs cibles contractuelles, puis DALKIA vs GRDF | QT, GRDF, ECS, DJU, NB/N'B/NC |
| P1 | Fourniture gaz et décompte définitif | Factures DALKIA, volumes, prix gaz, pièces fournisseur, GRDF |
| P2 | Exploitation-maintenance et obligations | Factures P2.1 à P2.4, indices, livrables, objectifs |
| P3 | Garantie totale et renouvellement | Factures P3.1 à P3.4, compte P3, travaux, pénalités |

### Ordre de développement recommandé

1. **Cockpit CPE** : rendre ce découpage visible dans `/cpe` et conserver le bilan énergétique dans une vue dédiée.
2. **Socle de contrôle des factures CPE** : document/facture par poste `P1/P2/P3`, exercice, période, montant, statut et pièces justificatives.
3. **Contrôle P1** : rapprocher les consommations DALKIA des données GRDF puis vérifier les factures gaz et le décompte définitif.
4. **Contrôle P2** : vérifier les révisions, livrables et conséquences contractuelles de P2.4.
5. **Contrôle P3** : suivre le compte P3, les travaux et les écarts entre facturation et exécution.
6. **Registre des écarts** : qualification commune en clarification, contestation, avoir attendu, pénalité ou validation.

> Première tranche lancée le 22/05/2026 : `/cpe` est recadré en cockpit CPE avec une vue séparée pour le suivi énergétique existant.

---

## ✅ Phase 1 — Moteur de cibles énergétiques (LIVRÉ)

### 1.1 Import QT par site ✅

- Import CSV des fichiers mensuels DALKIA (avant le 5e jour ouvrable) — **opérationnel**
- Endpoint POST `/api/cpe/import/csv` — détecte délimiteur, parse dates, upsert par site/mois
- Saisie manuelle mois par mois sur `/cpe/sites/:id` — **opérationnel**
- ⏳ Import API GRDF ADICT — en attente droits d'accès ; viendra compléter automatiquement

### 1.2 Calcul NC ✅

```python
NC = QT - (m × qECS)
```
Implémenté dans `services/cpe.py::calcul_nc()`. Si qECS non renseigné → NC = QT.

### 1.3 DJU automatisés ✅

Lecture depuis `DJU/dju_sete.csv` (Open-Meteo → méthode COSTIC, synchro quotidienne existante).
Endpoint GET `/api/cpe/dju/{annee}` — cumul annuel base 18°C, station Sète/Montpellier.

### 1.4 Calcul intéressement / pénalité ✅

Voir [[03-Cibles-et-intéressement]] pour les formules complètes.
Implémenté dans `services/cpe.py::calcul_interessement()`.
- Intéressement plafonné à **½ × N'B × 15%**
- Pénalité : **sans plafond**
- P2.4 réduite à **50%** si pénalité

### 1.5 Alerte révision NB ✅

Champ `alerte_revision_nb` dans `CpeResultatAnnuel` — déclenché si `|NC-NB|/NB ≥ 12%`.
Seuil sur 2 saisons (8%) : à implémenter en Phase 2 (nécessite historique N-1).

---

## 🔲 Phase 2 — Vérification contradictoire des factures

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

- Valeurs de base (01/01/2025) : ICHT-IME = 141,4 — FSD2 = 169,8
- Vérifier les 4 acomptes trimestriels

### 2.3 Vérificateur de révision P3 (garantie totale)

```
P3 = P30 × (0,15 + 0,30 × ICHT-IME/ICHT-IME0 + 0,55 × BT40/BT400)
```

- Valeur de base (01/01/2025) : BT40 = 128,4
- Révision au 1er octobre de chaque saison

### 2.4 Répertoire des indices de révision

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

## 🔲 Phase 3 — Pilotage avancé

### 3.1 Simulation de fin d'exercice

À partir des consommations connues (mois 1→N) et des DJU restants projetés :
- Estimer NC final de l'exercice
- Afficher la trajectoire : intéressement probable ou pénalité probable
- Utile dès le mois de septembre pour anticiper P2.4

### 3.2 Détection d'anomalies de consommation

- **M vs M-1** : variation anormale sur le mois
- **M vs M-1 de N-1** corrigé DJU : dérive annuelle
- Un pic anormal = problème équipement ou fuite → à remonter en réunion hebdo

### 3.3 Benchmark inter-sites (kWh/m²)

- Ratios de consommation par m² par bâtiment
- Comparer bâtiments de même nature (écoles entre elles, gymnases entre eux)
- Identifier les outliers **avant DALKIA** → force de négociation

### 3.4 Suivi des APE (Actions de Performance Énergétique)

Chaque APE doit être réalisée avant le **31/12/2029** :
- Inventaire avec statut (planifié / en cours / réalisé)
- Impact énergétique prévu vs mesuré (IPMVP Option B)
- Alerte si le planning global glisse vers 2029

### 3.5 Rapport IPMVP automatisé

- Option A : économies gaz (NB/N'B/NC + calcul intéressement)
- Option B : impact des APE sur consommations électriques

---

## Données externes — état d'intégration

| Source | Donnée | Statut |
|--------|--------|--------|
| GRDF ADICT API | QT gaz mensuel par site | ⏳ En attente droits d'accès |
| CSV DALKIA mensuel | QT gaz (fichier 5e jour ouvrable) | ✅ Import opérationnel |
| ENEDIS API | Consommation électricité par site | ✅ Déjà intégré |
| Open-Meteo / COSTIC | DJU mensuels base 18°C | ✅ Intégré (dju_sete.csv) |
| INSEE BDM | ICHT-IME, FSD2 | 🔲 Phase 2 |
| BSCC | BT40 | 🔲 Phase 2 |
| Marché PEG | Prix gaz (EIKON / ICIS) | 🔲 Phase 2 |
| GTC API DALKIA | Températures, statuts équipements | 🔲 Sous réserve mise en place |

---

## Liens

- [[11-Implémentation-Po2]] — détail technique de l'implémentation Phase 1
- [[03-Cibles-et-intéressement]] — formules NB/N'B/NC et pseudo-code
- [[04-Cibles-par-site]] — valeurs NB contractuelles par site
- [[06-Facturation-et-indices]] — formules de révision P1/P2/P3 et indices
- [[07-GTC-et-données]] — APIs, formats de données, intégration technique
- [[08-Gouvernance]] — calendrier des livrables et obligations DALKIA
- [[05-Pénalités-et-sanctions]] — montants des pénalités par type de manquement
