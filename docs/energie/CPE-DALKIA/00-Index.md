# CPE DALKIA — Base de connaissance

> **Contrat de Performance Énergétique** — Ville de Sète & CCAS  
> Titulaire : **DALKIA S.A.** (Agence Languedoc-Roussillon, Montpellier)  
> N° marché : **24 BT 039** — Lot 1 Bâtiments communaux  
> Prise d'effet : **13 octobre 2025** — Durée minimale : **8 ans** (≈ 12 octobre 2033)

---

## Navigation

| Note | Contenu |
|------|---------|
| [[01-Structure-du-marché]] | Architecture P1/P2/P3, prestations, périmètre |
| [[02-Énergie-fourniture]] | Gaz vs électricité, rôles PA/DALKIA, APIs |
| [[03-Cibles-et-intéressement]] | Formules NB/N'B/NC, DJU, calcul intéressement/pénalités |
| [[04-Cibles-par-site]] | Tableau NB (gaz) et cibles électricité par site |
| [[05-Pénalités-et-sanctions]] | Tableau complet des pénalités contractuelles |
| [[06-Facturation-et-indices]] | Formules de révision P1/P2/P3, délais facturation |
| [[07-GTC-et-données]] | API GTB, GMAO, espace client, formats de données |
| [[08-Gouvernance]] | Réunions, reporting, mémoire annuel, protocole IPMVP |
| [[09-Mise-au-point]] | Modifications OUV11 signées (écarts CCAP/CCTPM) |
| [[10-Roadmap-Po2]] | Fonctionnalités à développer dans Po2 — phases, priorités, données externes |
| [[11-Implémentation-Po2]] | Détail technique Phase 1 — modèles DB, calculs, API, frontend, mise en service |

---

## Contexte Po2 (développement)

Le module **Énergie** de Po2 doit permettre :
1. **Suivi des consommations** — import CSV ENEDIS (électricité) + API GRDF ADICT (gaz)
2. **Calcul automatique de l'intéressement** DALKIA — comparaison NC vs N'B corrigé DJU
3. **Suivi des cibles** par site (gaz + électricité) avec alertes de dépassement
4. **Tableau de bord CPE** — performance annuelle, état P2.4, solde P3

> **Attention** : l'électricité n'est PAS fournie par DALKIA. La Ville reste sur ses propres contrats (EDF/ENGIE via contrat cadre Hérault Énergie). DALKIA suit l'électricité par IPMVP option B mais ne facture pas l'électricité.
