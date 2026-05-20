# Template d'analyse — BPU PDF par PDF

> Copier ce fichier en `docs/Templates/_analyses-completes/<nom-pdf>.md` (à créer) pour chaque PDF analysé.
> But : capturer **toutes** les informations d'un BPU dans un format structuré, prêt à reporter dans le CSV canonique.

---

## Identification du document

| Champ | Valeur | Notes |
|---|---|---|
| `pdf_filename` | `<exemple_de_nom.pdf>` | Nom exact du fichier dans `saas/energie/HERAULT ENERGIE/HISTORIQUE BPU/` |
| `supplier` | EDF / ENGIE / autre | Lu dans le contenu du PDF (pas seulement le nom du fichier) |
| `valid_year` | 2021 / 2022 / ... | Année principale de validité |
| `valid_from` | AAAA-MM-JJ | Date de début (souvent 01/01 de l'année) |
| `valid_to` | AAAA-MM-JJ | Date de fin (souvent 31/12 de l'année) |
| `market_subsequent` | 1 / 2 / 3 | Numéro du marché subséquent (MS1, MS2, MS3) |
| `lot_number` | 1 / 2 / 3 / ... | Numéro du lot |
| `amendment_number` | 5 / 6 / ... ou vide | Numéro d'avenant si applicable |
| `amendment_label` | "V2" / "achat clic" / "prix ferme" / "signé" / vide | Libellé libre |
| `signature_date` | AAAA-MM-JJ | Date de signature en bas du document |
| `signatory_name` | "Alexandre DOUTRE" / ... | Nom du signataire |
| `signatory_role` | DG / DAF / ... | Rôle si mentionné |
| `docusign_envelope_id` | si présent | Identifiant en bas si signature électronique |

---

## Segments tarifaires identifiés dans ce PDF

> Recopier chaque segment trouvé (un PDF peut en avoir plusieurs : C1, C2, C3, C4, C5, EP, BATIMENT, etc.).

### Segment 1
| Champ | Valeur |
|---|---|
| `segment_type` | tension / site / usage |
| `segment_code` | C1 / C2 / C3 / C4 / C5 / BT / HTA / EP / BATIMENT / ECLAIRAGE_PUBLIC / BORNES / autre |
| `segment_label` | Libellé complet tel qu'écrit dans le PDF |
| `tension_category` | BT / HTA |
| `turpe_tariff` | C1 / C2 / C3 / C4 / C5 ou vide |
| `usage_label` | "Éclairage public" / "Bâtiment" / vide |

(Dupliquer cette section pour chaque segment du PDF.)

---

## Postes horosaisonniers utilisés dans ce PDF

> Pour chaque segment, lister les postes vus.

| Segment | Postes |
|---|---|
| C1 | BASE / POINTE / HPH / HPE / HCH / HCE / HP / HC |
| C4 | HPH / HPE / HCH / HCE |
| ... | ... |

**Codes normalisés** :
- `BASE` (toute heure)
- `POINTE` (heures de pointe réseau)
- `HPH` (heures pleines hiver)
- `HCH` (heures creuses hiver)
- `HPE` (heures pleines été)
- `HCE` (heures creuses été)
- `HP` (heures pleines, double tarif générique)
- `HC` (heures creuses, double tarif générique)

Si tu vois un autre poste non listé → l'écrire tel quel et le signaler en section "Nouvelles découvertes".

---

## Composantes de prix (cœur de l'extraction)

| segment_code | period_code | component_type | component_label (libellé PDF) | price_value | price_unit | is_negative | notes |
|---|---|---|---|---|---|---|---|
| C1 | HPH | fourniture | "Electricité" | 5.481 | c€/kWh HTT | false | |
| C1 | HPH | capacite | "Mécanisme de capacité" | -0.033 | c€/kWh HTT | true | |
| C1 | HPH | cee | "CEE (Obligations d'économies d'énergie)" | 0.628 | c€/kWh HTT | false | Valeur unique pour le segment, copier sur tous les postes ? À vérifier |
| C1 | HPH | go | "Option Energie renouvelable" | 0.231 | c€/kWh HTT | false | |
| ... | ... | ... | ... | ... | ... | ... | ... |

**Codes composantes normalisés** :
- `fourniture` (prix énergie pure)
- `capacite` (mécanisme de capacité)
- `cee` (Certificats d'Économies d'Énergie)
- `go` (Garanties d'Origine / Option renouvelable)
- `renouvelable` (alias de `go` chez EDF, garder si distinction explicite)
- `autre` (réserve pour découvertes)

**Unités fréquentes** :
- `c€/kWh HTT` (centimes d'euro par kWh hors toutes taxes)
- `€/MWh` (euros par MWh)
- `€HTT/MWh` (idem)

---

## Frais fixes

| charge_type | charge_label (libellé PDF) | charge_value | charge_unit | applicable_from | applicable_to | segment_code (si lié) | notes |
|---|---|---|---|---|---|---|---|
| abonnement | "Abonnement mensuel C4" | 30.00 | €HT/mois | | | C4 | |
| branchement_provisoire | "Surcoût Branchement Provisoire" | 120.00 | €HT/BP/Mois | 2023-01-01 | 2025-12-31 | | |
| contrat_temporaire | "Surcoût Contrat Temporaire" | 7.40 | €HT/CT/Mois | 2023-01-01 | 2025-12-31 | | |

**Codes charge_type normalisés** :
- `abonnement`
- `branchement_provisoire`
- `contrat_temporaire`
- `autre`

---

## Clauses spéciales / conditions particulières

Liste libre des clauses non standard. Exemples typiques :
- Formule d'indexation des prix (référence indice, dates de révision, etc.)
- Conditions de résiliation
- Modalités de calcul TURPE (renvoi à un référentiel externe)
- Plafond/plancher sur certaines composantes
- Conditions particulières par segment

---

## Nouvelles découvertes (= éléments non couverts par le modèle actuel)

> ⚠️ Section **critique** : si tu trouves une information dans le PDF qui ne rentre dans aucune des catégories ci-dessus, **la décrire ici**. Ça déclenchera une extension du schéma.

Exemples possibles :
- Nouvelle composante de prix jamais vue (ex: "Prime mécanisme d'effacement")
- Nouveau type de poste (ex: "Heures super-creuses")
- Nouvelle structure de remise volumique
- Champ administratif manquant (n° accord-cadre, agent commercial, etc.)

Format suggéré :
```
- Élément : <nom>
- Description : <contexte dans le PDF>
- Valeur(s) vue(s) : <exemples>
- Proposition d'intégration au schéma : (nouveau code dans COMPONENT_TYPES ? nouvelle colonne dans BpuDocument ? nouvelle table ?)
```

---

## Métriques d'analyse

À la fin de l'analyse, remplir pour le suivi :

| Métrique | Valeur |
|---|---|
| Nombre de segments | |
| Nombre de postes total (toutes combinaisons) | |
| Nombre de prix unitaires extraits | |
| Nombre de frais fixes | |
| Confiance subjective (1-10) | |
| Temps passé (min) | |
| Difficultés rencontrées | |
