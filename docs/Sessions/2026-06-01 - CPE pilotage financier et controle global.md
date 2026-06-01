# 2026-06-01 - CPE pilotage financier et controle global

## Objectif

Transformer `/cpe` en outil de travail quotidien pour le suivi financier du marche DALKIA :

- dissocier les archives de facture et l'audit des controles ;
- rendre visible l'exercice annuel ;
- lancer un controle portefeuille sans recalcul manuel facture par facture.

## Livrable

- vue `Factures` : suivi annuel du 01/01 au 31/12, filtres, KPI et graphiques ;
- contrats hors perimetre exclus par defaut ;
- graphique par types `AC`, `AJ`, `DE`, `EC`, `RE` ;
- vue `Controle factures` : recalcul global, KPI qualite, graphiques anomalies, file priorisee ;
- endpoints `GET /api/cpe/finances/controls/report` et
  `POST /api/cpe/finances/controls/recalculate`.

## Suite

Parser les enveloppes DPGF des annexes DALKIA Lot 1 et Lot 2 afin de comparer le realise facture
au prevu contractuel par famille, poste et site.
