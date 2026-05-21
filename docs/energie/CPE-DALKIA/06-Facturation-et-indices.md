# Facturation et formules de révision des prix

tags: #facturation #révision #indices #P1 #P2 #P3 #ICHT-IME #BT40 #PEG

---

## Indices de référence

| Indice | Description | Valeur base (01/01/2025) |
|--------|-------------|--------------------------|
| **ICHT-IME** | Salaires industrie mécanique et électrique | 141,4 |
| **FSD2** | Frais et services divers | 169,8 |
| **BT40** | Travaux de chauffage du bâtiment | 128,4 |
| **PEG** | Price Exchange Gas (prix marché gaz) | Valeur au 13/10/2025 |
| **TVD** | Terme variable distribution gaz | Selon facture fournisseur |
| **CEE** | Certificats d'Économies d'Énergie | Selon facture fournisseur |
| **TICGN** | Taxe Intérieure sur la Consommation de Gaz Naturel | Légal |

---

## P1 — Révision prix gaz

### Formule Pugaz
```
Pugaz = Pugaz0 × (a + b×PEG/PEG0 + c×TVD/TVD0 + d×CEE/CEE0 + e×TICGN/TICGN0)
```
- Coefficients a, b, c, d, e calculés en fonction de la quote-part réelle de chaque composante
- Une formule **par tarif** (T1, T2, T3, T4 selon les sites)
- Achat indexé PEG du 13/10/2025 au 31/12/2027 (avec option SWAP en prix fixe)
- TVD, TICGN, CEE : refacturés à l'euro/l'euro

### Calendrier facturation P1
| Échéance | Montant |
|----------|---------|
| 31 mars | Acompte = ¼ P10 |
| 30 juin | Acompte = ¼ P10 |
| 30 septembre | Acompte = ¼ P10 |
| **15 février N+1** | Décompte définitif (arrêté au 31/12/N) |

---

## P2 — Révision prix entretien/conduite

### Formule de révision annuelle
```
P2 = P20 × (0,15 + 0,70 × ICHT-IME/ICHT-IME0 + 0,15 × FSD2/FSD20)
```
- Révision au **1er janvier** de chaque année civile
- 15% fixe + 70% main d'œuvre (ICHT-IME) + 15% frais de service (FSD2)

### Calendrier facturation P2
| Échéance | Montant |
|----------|---------|
| 31 mars | ¼ P20 révisé |
| 30 juin | ¼ P20 révisé |
| 30 septembre | ¼ P20 révisé |
| 31 décembre | ¼ P20 révisé (à transmettre avant le 31 janvier) |

> Pas de facture de régularisation en fin d'exercice.

### Cas particulier P2.4
- Facturé **annuellement** après validation de l'atteinte des objectifs énergétiques
- Réduit à **50%** si objectifs non atteints (voir [[03-Cibles-et-intéressement]])

### Cas particulier P2 "Sensibilisation énergétique"
- Facturé **trimestriellement** selon les mêmes conditions que les autres postes P2  
  *(précision issue de la mise au point OUV11)*

---

## P3 — Révision prix garantie totale

### Formule P3.1 à P3.3
```
P3 = P30 × (0,15 + 0,30 × ICHT-IME/ICHT-IME0 + 0,55 × BT40/BT400)
```

### Formule P3.4 (travaux programmés)
*(Formule modifiée lors de la mise au point OUV11 — formule finale à récupérer dans l'OS de mise au point)*
```
P3.4 = P30 × (0,70 × ICHT-IME/ICHT-IME0 + 0,10 × [indice] + 0,20 × [indice])
```
> ⚠️ La formule P3.4 du CCAP a été remplacée lors de la mise au point (OUV11, article CCAP 7.4.2). Se référer au document OUV11 signé pour la formule définitive.

### Calendrier facturation P3
| Échéance | Montant |
|----------|---------|
| 31 mars | ¼ P30 révisé |
| 30 juin | ¼ P30 révisé |
| 30 septembre | ¼ P30 révisé |
| **31 octobre** | ¼ P30 révisé (à transmettre avant le 31 octobre) |

> Révision au **1er octobre** de chaque saison.

---

## BPU — Taux horaires et coefficients

- Taux horaires révisés annuellement selon la formule du P2
- Coefficients sur fourniture et sous-traitance : **fixes** sur toute la durée
- Transparence : les prix fournitures sont publiés, coefficient multiplié (pas de marge cachée)
- Délai devis : 2 semaines maximum (48h si urgence post-dépannage)
- Facturation dans le mois suivant la réception des travaux

---

## Délais de paiement

- Délai global de paiement : **30 jours** à compter de réception de la demande
- Intérêts moratoires : taux BCE + 8 points + indemnité forfaitaire 40€
- Facturation électronique : plateforme **CHORUS Pro** exclusivement
- SIRET Ville de Sète : **21340301700014**

---

## Avance

- Déclenchement : si marché > 50 000 € HT et durée > 2 mois
- Taux standard : **5%** du montant initial TTC (prorata si durée > 12 mois)
- Taux PME : **30%** (si DALKIA justifie ce statut)
- Remboursement : commence quand 65% du montant est exécuté, termine à 80%
- Garantie : caution personnelle et solidaire à 100% de l'avance

---

## Liens
- [[01-Structure-du-marché]] — structure globale P1/P2/P3
- [[09-Mise-au-point]] — modifications de la formule P3.4
