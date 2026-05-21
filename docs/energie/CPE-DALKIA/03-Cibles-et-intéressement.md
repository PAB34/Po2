# Cibles énergétiques et mécanisme d'intéressement

tags: #intéressement #pénalités #DJU #NB #cibles #IPMVP

---

## Paramètres fondamentaux

| Paramètre | Définition | Valeur/Source |
|-----------|-----------|---------------|
| **DJU contractuels** | Base de calcul : X = 18°C | Station MONTPELLIER |
| **NB** | Conso théorique chauffage (MWhPCI) en année normale | Défini par site — Annexe 6 AE |
| **DJU-référence** | Moyenne trentenaire 1981/2010, Oct→Mai | **1 426 DJU** |
| **DJU-réels** | DJU effectivement mesurés pendant la saison | Station Montpellier |
| **N'B** | Cible corrigée par la rigueur climatique réelle | Calculé chaque année |
| **m** | Volume ECS réchauffé (m³) du 01/01 au 31/12 | Relevés compteurs |
| **qECS** | Énergie unitaire ECS (MWhPCI/m³) | Défini dans bordereau de prix par site |
| **QT** | Conso totale relevée aux compteurs gaz (MWhPCI) | 01/01 au 31/12 |
| **NC** | Conso nette chauffage (QT moins la part ECS) | Calculé |
| **Pu** | Prix unitaire du MWhPCI de gaz | Issu du contrat P1 en vigueur |

---

## Formules de calcul

### N'B — Cible annuelle corrigée
```
N'B = NB × (DJU-réels / 1426)
```
- Neutralise l'effet de la rigueur climatique : si hiver doux, la cible baisse ; si hiver rigoureux, elle monte
- En cas d'interruption chauffage > 24h : les DJU du jour sont déduits des DJU réels
- DJU du jour de mise en service **inclus** ; DJU du jour d'arrêt **exclus**

### NC — Consommation nette chauffage
```
NC = QT – (m × qECS)
```
- Si compteur énergie ECS présent : `NC = somme des compteurs énergie "chauffage"`
- Pour sites à production mixte : compteur en sortie de chaufferie

### Intéressement (NC < N'B : DALKIA performe mieux que prévu)
```
I = ½ × (N'B – NC) × Pu
```
→ DALKIA adresse une **facture** à la collectivité

**Plafond** : si NC < 85% de N'B (économie > 15%) :
```
Imax = ½ × N'B × 15%
```
→ Le partage est plafonné, le gain au-delà de 15% revient entièrement à la collectivité

### Pénalité (NC > N'B : dépassement de la cible)
```
P = -(NC – N'B) × Pu
```
→ DALKIA adresse un **avoir** à la collectivité
→ **100% à la charge de DALKIA** (pas de partage, pas de plafond)

---

## Première période d'application

Le marché prend effet le 13/10/2025, mais la **première période d'intéressement** court du **01/01/2026 au 31/12/2026**.

Les factures/avoirs d'intéressement doivent être transmis **avant le 31 janvier** de l'année suivante.

---

## Clause de garantie de l'efficacité énergétique (P2.4)

DALKIA s'engage sur un pourcentage de réduction des consommations défini dans l'Acte d'Engagement.

| Situation | Conséquence |
|-----------|------------|
| Objectifs atteints | P2.4 facturé à **100%** |
| Objectifs non atteints | P2.4 facturé à **50%** sur l'exercice |

Le rapport IPMVP (avant 31/01 chaque année) documente :
- Les engagements de DALKIA
- Le niveau d'efficacité obtenu
- La méthode de calcul retenue
- L'impact financier pour les deux parties

---

## Révision du NB

Le NB (cible de référence) peut être révisé dans les cas suivants :

| Seuil de déclenchement | Condition |
|------------------------|-----------|
| > 8% d'écart NC/N'B | Deux saisons successives |
| > 12% d'écart NC/N'B | Une seule saison |

**Qui peut demander la révision ?** Les deux parties.

**Refus de révision possible** : si le dépassement est imputable à DALKIA et NC > N'B de plus de 8% (2 saisons) ou 12% (1 saison), la collectivité peut refuser le réajustement.

**Cas de révision automatique :**
- Travaux de réhabilitation énergétique réalisés par la collectivité → cible neutralisée pendant travaux, nouveau NB après une saison complète
- Nouvelles installations → NB fixé après 1ère saison de chauffe
- Résiliation possible de plein droit sans indemnité si pas d'accord entre parties

---

## Vérification électricité (IPMVP option B)

Les engagements sur l'électricité sont vérifiés via le protocole **IPMVP option B** :
- Mesure de l'impact des actions d'amélioration (APE) sur la consommation électrique
- DALKIA transmet son rapport avant le 31/01 chaque année
- Pas de calcul d'intéressement direct sur l'électricité (contrairement au gaz)
- Mais impact sur P2.4 si les objectifs globaux (gaz + électricité) ne sont pas atteints

---

## Implications pour Po2

```python
# Pseudo-code calcul intéressement annuel par site
def calcul_interessement(site_id, annee):
    NB = get_cible_gaz(site_id)               # depuis Annexe 5.1 AE
    DJU_reels = get_dju(annee, "montpellier") # depuis API météo / COSTIC
    DJU_ref = 1426
    
    N_prime_B = NB * (DJU_reels / DJU_ref)   # correction climatique
    
    m = get_volume_ecs(site_id, annee)         # depuis compteurs GRDF/GTC
    qECS = get_qecs(site_id)                  # depuis bordereau de prix
    QT = get_conso_gaz_totale(site_id, annee) # depuis API GRDF ADICT
    
    NC = QT - (m * qECS)
    
    Pu = get_prix_unitaire_gaz(annee)          # depuis contrat P1 actif
    
    ecart = N_prime_B - NC
    if ecart > 0:  # économies
        I = 0.5 * min(ecart, N_prime_B * 0.15) * Pu
        return {"type": "facture", "montant": I}
    else:  # dépassement
        P = abs(ecart) * Pu
        return {"type": "avoir", "montant": P}
```

---

## Liens
- [[04-Cibles-par-site]] — valeurs NB et qECS par site
- [[02-Énergie-fourniture]] — source des données QT (GRDF) et DJU
- [[05-Pénalités-et-sanctions]] — autres pénalités hors intéressement
- [[08-Gouvernance]] — calendrier des rapports IPMVP
