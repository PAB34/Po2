# 2026-05-22 — Rapport fournisseur : agrégat par famille et recalcul BPU chiffré

tags: #énergie #factures #rapport-fournisseur #BPU #UX

> Commit : `ce53a0b`
> Page concernée : `/energie/factures` → bouton **« Éditer rapport »**

---

## Constat utilisateur sur le rapport précédent

Sur le rapport ENGIE du 22 mai (cf. `saas/energie/ENGIE/Audit facture.pdf`), trois écueils ont été remontés :

1. **Section « Points soumis à clarification » trompeuse** — le `message` affiché en titre d'agrégat mentionnait UN compteur précis (ex. *« Trou de facturation détecté sur 24309117128642 »*) alors que la ligne couvrait 30+ PRM. Le « Périmètre détecté » sous le message listait bien plus de scopes que ce que le titre laissait penser, avec un `...` qui tronquait.
2. **Section « Factures concernées » trop pauvre** — aucune indication du PRM précisément concerné par les anomalies pour chaque facture, ni du type technique.
3. **Pas de chiffrage des écarts de prix** — pour la famille « Prix contractuels » (`BPU_PRICE_MISMATCH`), aucune estimation du montant que représentait l'écart constaté vs le BPU contractuel.

---

## Décisions retenues

| Question | Choix |
|---|---|
| Affichage liste PRM impactés | Liste complète, mise en page grille responsive (pas de troncature) |
| Colonnes facture | Ajout **PRM impactés** (extraits des scopes des issues) |
| Recalcul BPU | Refetch des détails facture côté frontend + calcul JS (livraison rapide, pas de migration DB) |

---

## Refonte implémentée

### 1. « Points soumis à clarification » — agrégation par famille

- Suppression de l'agrégation par `code` (ex. `PERIOD_GAP`, `BPU_PRICE_MISMATCH`) : un seul **bloc par famille** (`Périodes`, `Prix contractuels`, etc.).
- Plus de `message` du premier issue rencontré (trompeur) : remplacé par le **détail générique** de la famille.
- Affichage en cartes avec compteurs : `nb factures · nb compteurs distincts · nb signalements`.
- Liste exhaustive des **codes de contrôle** distincts (ex. `BPU_PRICE_MISMATCH, BPU_TARIFF_POSTE_INCONSISTENCY`).
- **Périmètre détaillé** dans un `<details>` ouvert par défaut, en grille `auto-fill minmax(280px, 1fr)` — tous les scopes sont visibles, plus de `...`.

### 2. « Factures concernées » — colonne PRM ajoutée

- Nouvelle colonne **« PRM impactés »** : extraction du PRM (1ʳᵉ partie du scope si 10-18 chiffres) depuis les issues retenues par les filtres pour cette facture. Liste verticale dans la cellule.
- La colonne `Catégories` remplace `Points à clarifier` pour rester homogène avec la nouvelle nomenclature.

### 3. Nouvelle section « Estimation impact des écarts BPU »

Section **conditionnelle** : n'apparaît que si au moins un `BPU_PRICE_MISMATCH` est retenu.

Pipeline de calcul :

1. **Fetch** des `EnergyInvoiceImportDetail` des factures concernées via `fetchEnergyInvoiceImport(token, id)` (Promise.all, parallèle).
2. **Parse** du message de chaque issue `BPU_PRICE_MISMATCH` via une regex qui capture `(prix_facture_€/MWh, prix_BPU_€/MWh, poste)` — gère le format courant (`pour LU/base`) et le format historique (`(ENGIE 2025 lot 7, C2/hph)`).
3. **Matching ligne facture** : on retrouve le site dans `analysis_result.sites[]` par scope (PRM ou FIC), puis on cherche la ligne énergie dont `unit_price_ht × 1000 ≈ prix_facture` (tolérance 0,5 €/MWh).
4. **Conversion quantité** : `quantity_unit` → MWh (kWh ÷ 1000 sinon).
5. **Delta total** = `(prix_facturé − prix_BPU) × quantité_MWh`.

Affichage : tableau avec **Prix facture / Prix BPU / Delta €/MWh / Quantité MWh / Écart estimé HT**, code couleur rouge si défavorable à la collectivité, footer avec **total HT estimé** et mention du nombre de lignes sans quantité rattachée (exclues du total).

### 4. Plumbing token

- `InvoiceSupplierReport` prend désormais une prop `token: string | null` (lu via `useAuth()` dans `EnergieInvoicesPage`).
- Le `useEffect` de fetch est annulable via flag `cancelled` pour éviter les setState après démontage.

---

## Fiabilisation du matching (2e itération, même date)

Suite au retour utilisateur sur l'imprécision potentielle de l'heuristique de matching ligne/BPU
côté frontend, le calcul a été déplacé **dans le moteur d'analyse backend** qui connaît déjà
exactement la ligne facture qui a généré le mismatch et le BPU retenu.

### Backend — `_check_bpu` enrichi

- Nouveau helper `_record_bpu_mismatch()` dans `saas/backend/app/services/invoice_analysis.py`.
- À chaque détection d'un `BPU_PRICE_MISMATCH` (cas BPU historique ET cas BPU configuré),
  on persiste un dict structuré dans `bpu_summary["mismatches_detail"]` qui est ensuite
  sérialisé dans `control_report_json` :

  ```python
  {
    "scope": "24309117128642 / FIC 630000534222 / 2026-03-05 - 2026-04-04",
    "site_prm_id": "24309117128642",
    "site_fic_number": "630000534222",
    "line_index": 4,                          # position exacte dans site.invoice_lines[]
    "line_label": "Energie facturee HCH",
    "line_normalized_component": "energie_hch",
    "line_poste": "HCH",
    "invoice_price_eur_mwh": 121.74,
    "bpu_price_eur_mwh": 75.29,
    "delta_eur_mwh": 46.45,
    "quantity": 5000.0,
    "quantity_unit": "kWh",
    "quantity_mwh": 5.0,
    "delta_total_eur_ht": 232.25,
    "bpu_reference": "C2/hph",                # ou "ENGIE 2025 lot 7 C2/hph" si historique
    "source": "configured"                    # "historical" | "configured"
  }
  ```

### Frontend — lecture directe sans parsing

- Suppression de la regex `BPU_PRICE_REGEX`, de `findMatchingInvoiceLine`, de `siteMatchesScope`
  et de `computeBpuDeltas`. Plus de matching par tolérance de prix.
- Le composant lit `detail.control_report.bpu.mismatches_detail` via `extractMismatchesDetail()`
  et affiche les valeurs exactes calculées par le backend.
- Une **colonne « Ligne facturée »** a été ajoutée au tableau (label + poste + composante
  normalisée) pour traçabilité totale facture ↔ écart.
- Une **colonne « Référence BPU »** indique précisément à quel lot/segment/poste le moteur a
  rattaché le prix (avec source historique vs configuré en sous-libellé).

### Compatibilité analyses antérieures

Les factures déjà analysées avant ce changement n'ont pas `mismatches_detail` dans leur
`control_report`. Le frontend détecte ce cas et affiche une **invite à relancer l'analyse**
dans la zone éditeur (note jaune) et dans la section BPU elle-même. La relance se fait depuis
la page détail facture via le bouton « Re-analyser » existant.

## 3e itération (même date) — chiffrage incohérences tarif/poste + timeline visuelle

Retour utilisateur après nouvel audit ENGIE : « j'ai un doute sur Estimation impact des écarts
BPU sur le nombre de PRM traités et le montant ». Doute légitime — 8 signalements remontent
dans la catégorie « Prix contractuels » mais une seule ligne chiffrée à 0,23 € sur 5 kWh.

### Diagnostic

- **Pas de bug parser** : 5 kWh × 0,12174 €/kWh = 0,61 €, arithmétique correcte. La facture
  ENGIE annote bien `quantity_unit = "kWh"`. La ligne « Base » est juste résiduelle (5 kWh)
  sur un compteur où la consommation principale est ventilée sur HCH/HPH/HCB/HPB.
- **Cause réelle** : les 7 autres signalements sont des `BPU_TARIFF_POSTE_INCONSISTENCY` qui
  ne remontaient pas dans le total. C'est là que se cache l'écart financier réel.

### Backend — chiffrage des incohérences tarif/poste

Nouveau helper `_record_bpu_tariff_poste_inconsistency()` qui calcule par groupe :

```
delta = Σ(montant_HT_facturé)  −  Σ(quantité_MWh) × prix_BPU_attendu
```

Chaque entrée stockée dans `mismatches_detail` porte désormais un champ `type` :
- `"price_mismatch"` — écart de prix unitaire par ligne (déjà existant)
- `"tariff_poste_inconsistency"` — incohérence tarif/poste agrégée par groupe (nouveau)

L'entrée `tariff_poste_inconsistency` porte aussi le détail de chaque ligne facture impliquée
(`lines: []`) pour traçabilité totale.

### Frontend — deux sous-tableaux + total cumulé

Type union `BpuMismatchDetail = BpuPriceMismatch | BpuTariffPosteInconsistency` côté TS.
La section « Estimation impact des écarts BPU » présente désormais :
- Sous-tableau 1 : **Écarts de prix unitaire** (par ligne, comme avant)
- Sous-tableau 2 : **Incohérences tarif / poste** (par groupe agrégé)
  - Colonnes : BPU attendu, postes facturés, quantité totale, total facture HT,
    total si BPU attendu, écart estimé HT
- **Total écart estimé HT cumulé** en pied de section.

## 4e itération (même date) — frise visuelle des périodes facturées

Demande utilisateur : « sur le chevauchement ou le vide de période de facturation ce serait
intéressant d'avoir un visuel genre un graphique en barre sur l'année glissante en cours,
un pour chaque regroupement de facture ».

### Composant `InvoicePeriodTimeline` (SVG natif, zéro dépendance)

Path : `saas/frontend/src/components/InvoicePeriodTimeline.tsx`.

- Axe X : année glissante (12 mois en arrière depuis aujourd'hui) — graduations mensuelles.
- Groupage : `regroupement` (fallback `contract_holder`, puis `"Non regroupe"`).
- 1 ligne par `rowKey` (PRM dans le rapport, n° facture dans la page liste).
- Multiples périodes sur la même ligne → détection automatique des **chevauchements** (barre
  rouge) et des **trous internes** (hachuré rouge sur fond rose).
- Légende intégrée (Période facturée bleu / Période signalée orange / Chevauchement rouge /
  Trou de facturation hachuré).
- SVG responsive, imprimable, tooltips `<title>` natifs.

### Intégrations

**Dans le rapport fournisseur** (`InvoiceSupplierReport.tsx`) :
- Sous la liste des scopes de la famille `periods`.
- Parse les scopes au format `"PRM / FIC nnnn / YYYY-MM-DD - YYYY-MM-DD"` via
  `parseScopeWithPeriod()` pour extraire PRM/FIC/start/end.
- Groupé par regroupement de la facture portant l'issue.
- Affiche uniquement les périodes signalées (vue ciblée pour le fournisseur).

**Dans `/energie/factures`** (page liste) :
- Panneau collapsible « Frise des périodes facturées » au-dessus du tableau.
- 1 barre par facture filtrée (la période globale facture, pas par PRM — accessible sans
  fetch supplémentaire).
- Les factures portant une anomalie `periods` sont surlignées orange.
- Donne une vue d'ensemble du parc et permet de repérer visuellement les regroupements
  problématiques.

## Limitations restantes

- La frise dans le rapport ne montre que les périodes **signalées** (issues de
  `PERIOD_GAP` / `PERIOD_OVERLAP`). Pour montrer aussi les périodes saines en référence
  visuelle, il faudrait fetcher les `analysis_result.sites[]` de toutes les factures du
  parc. Reporté tant que le visuel actuel reste lisible.
- La frise de la page liste affiche **1 barre par facture** (période globale), pas par PRM.
  Pour la vue par PRM dans la page liste il faudrait soit un endpoint backend qui agrège
  les périodes par PRM, soit un Promise.all sur les détails — non bloquant pour l'usage actuel.
- Pas de prise en compte du **lot BPU applicable à la période** dans le recalcul BPU : on
  se base sur le BPU que le moteur backend a retenu lors de l'analyse de la facture. C'est
  cohérent par construction (le delta a été calculé avec ce BPU).

---

## Tests à faire en production

1. Ouvrir `/energie/factures`, filtrer par catégorie `Prix contractuels` + `Périodes`.
2. Cliquer « Éditer rapport ».
3. Vérifier :
   - Section « Points soumis à clarification » : 2 cartes (Périodes, Prix contractuels), liste complète des scopes en grille.
   - Section « Estimation impact BPU » : présente, tableau rempli, total HT non nul.
   - Section « Factures concernées » : colonne PRM impactés peuplée.
4. Imprimer/PDF et vérifier la mise en page sur 2-3 pages.

---

## Voir aussi

- [[Modules/Energie-Facturation]] — module facturation (section UI mise à jour)
- [[Sessions/2026-05-21 — Rapport fournisseur factures filtrees]] — version initiale du rapport
- [[Sessions/2026-05-22 - References BPU historiques factures]] — moteur de matching BPU historique
