# Session — Factures et matrices comptables V1

> Date : 2026-06-24

## Objectif

Intégrer la matrice comptable au parcours Factures & décisions, par contrat et version, avec édition comptable et aller-retour XLSX.

## Réalisé

- chaîne import, dédoublonnage, parsing, contrat, imputation, décision et export ;
- cartes de matrices par contrat ENGIE, EDF, TotalEnergies et DALKIA ;
- éditeur de règles service/fonction/nature/opération/antenne/ventilation ;
- statuts Validée, Proposée, À compléter et À arbitrer ;
- principe d’instantané comptable par facture ;
- export/import XLSX simulé avec aperçu des différences ;
- contrat d’écran 35 et documentation projet mis à jour.

## Garde-fous

La plateforme reste source de vérité. Le classeur XLSX ne remplace pas la base, ne supprime aucune règle implicitement et crée une nouvelle version brouillon après validation du différentiel.
