# Session — Contrat et prototype Fluides V1

> Date : 2026-06-24

## Objectif

Traiter les six réponses Fluides, définir le contrat d'écran raccordable et produire une maquette détaillée cohérente avec la charte PO².

## Réalisé

- consolidation des réponses QF01 à QF06 ;
- audit des routes ENEDIS, GRDF, DJU, consommation journalière et courbe de charge ;
- création du document 34 ;
- page Fluides détaillée dans le prototype ;
- onglets Tous, Électricité, Gaz et Eau à construire ;
- trajectoire réel/référence/prévision et fourchette ;
- hiver chauffage et été froid ;
- dérives de courbe de charge et qualité des données ;
- drill-down vers Site 360°.

## Validation

- syntaxe JavaScript valide ;
- rendu contrôlé dans le navigateur ;
- filtres Électricité et Gaz avec atterrissages cohérents ;
- état Eau sans données fictives ;
- passage vers le site Fonquerne ;
- aucune erreur console.

## Handoff suivant

1. Relecture utilisateur du prototype Fluides.
2. Contrat d'écran Facturation.
3. Cartographie détaillée des données vers les composants React.
4. Endpoint portefeuille multi-fluides et moteur d'atterrissage lors du raccordement.
