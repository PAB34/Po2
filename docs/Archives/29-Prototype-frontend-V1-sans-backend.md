# 29 - Prototype frontend V1 sans backend

> Date : 2026-06-24  
> Livrable : `docs/prototype-refonte-v1/index.html`  
> Statut : premier jet interactif à évaluer ; aucune API ni base de données raccordée.

## Niveau de préparation estimé

La plateforme est estimée à **80 % prête pour prototyper sa nouvelle expérience**, mais à **55–60 % prête pour construire immédiatement le frontend définitif raccordé au réel**.

Cette différence est normale : la cartographie et les besoins sont suffisamment solides pour dessiner les parcours, alors que les contrats de données, neuf arbitrages et plusieurs fonctionnalités métier doivent encore être finalisés avant le raccordement complet.

| Dimension | Estimation | Lecture |
|---|---:|---|
| Inventaire des fonctionnalités | 90 % | 66 capacités recensées et représentées dans la V1. |
| Vision produit et workflows | 82 % | Les chaînes prioritaires et le global-vers-détail sont établis. |
| Profils et décisions utilisateur | 72 % | 17 décisions validées, 9 à compléter. |
| Données et contrats d'écran | 60 % | CIRIL, matrice comptable et certains référentiels restent à stabiliser. |
| Design system réellement implémenté | 30 % | Ce prototype pose le langage ; le SaaS actuel n'est pas encore refondu. |
| Prêt pour une livraison production globale | 55–60 % | Le raccordement, les droits, les états d'erreur et les tests réels restent nécessaires. |

Ces pourcentages mesurent la **préparation de la refonte**, pas l'avancement total de toutes les fonctionnalités futures.

## Ce que montre le prototype

### Cockpit par profil

Le sélecteur `Voir comme` adapte l'accueil aux profils Direction, Fluides, Technicien CVC, Comptable et Patrimoine. Chaque profil reçoit ses indicateurs et sa file de décisions, sans créer cinq produits séparés.

Le cockpit affiche maintenant une **Chaîne de décision V1** : Factures, Fluides, Technique, Budget et Sites 360°. Chaque entrée relie le signal à une preuve attendue, une décision cible et l'écran métier correspondant.

### Factures et décisions

La vue unifie ENGIE, EDF, TotalEnergies et DALKIA. Elle montre les nouvelles factures, conformités, anomalies et transmissions aux finances. Le parcours visualise import, dédoublonnage, parsing, association au contrat, imputation comptable, décision et export. Les matrices sont versionnées par contrat ; leur éditeur et l’aller-retour XLSX sont simulés avec aperçu préalable des différences. Une facture ouvre un panneau latéral avec montant, échéance, verdict, trace de contrôle et actions de décision/réclamation.

### Site 360°

Le site devient la porte d'entrée vers les informations patrimoniales, les fluides, les contrats, la technique, le budget/PPT et les documents. Le prototype permet de changer de site et d'onglet sans perdre le contexte. La synthèse du site affiche désormais les décisions reliées au site avec leur preuve : facture, abonnement, maintenance et budget.

### Fluides et calibrage des abonnements

La vue Fluides distingue la **mesure distributeur** du **contrat fournisseur**. Pour l’électricité, les courbes de charge ENEDIS au pas de 30 minutes alimentent la recommandation de puissance souscrite sur les contrats EDF ou ENGIE. Le diagnostic sépare les abonnements surdimensionnés, les risques de dépassement et les cas correctement calibrés.

Le gaz suit une méthode adaptée : profils GRDF, CAR, capacité et paramètres du contrat TotalEnergies. L’eau est prévue à partir de la télérelève ou des index disponibles, du débit de pointe, du diamètre du compteur et de la structure tarifaire ; le prototype n’invente pas une courbe fine lorsque la source n’existe pas.

Chaque abonnement présenté peut maintenant ouvrir une fiche de calcul : diagnostic, paramètre actuel, mesure de référence, cible, courbe ou profil utilisé, étapes de calcul, contrat, risque, confiance et actions d’instruction. Le cas Eau montre volontairement l’impossibilité de calculer plutôt qu’une recommandation artificielle.

### Thème d’affichage

Le mode `Automatique` suit `prefers-color-scheme` et donc le thème exposé par Windows au navigateur. Le bouton de thème de la barre supérieure permet de basculer entre `Automatique`, `Sombre` et `Clair`. Le choix manuel est conservé localement pour les ouvertures suivantes.

### Interactions transversales

- navigation métier persistante ;
- recherche globale par site, facture, compteur ou contrat ;
- changement de profil instantané ;
- filtres et recherche de factures ;
- drill-down en panneau latéral ;
- simulation d'une décision ;
- comportement responsive pour écran réduit;
- thème automatique, sombre ou clair avec préférence persistante.

## Langage visuel proposé

- fond clair légèrement chaud pour réduire la fatigue ;
- navigation sombre stable pour donner du contexte ;
- vert menthe comme couleur d'action et de confiance ;
- ambre et corail réservés aux décisions et risques ;
- grands chiffres peu nombreux, accompagnés de leur source ou interprétation ;
- tableaux denses seulement lorsque la comparaison le justifie ;
- drill-down plutôt que multiplication des pages ;
- qualité de la donnée visible au même niveau que l'indicateur.

## Données simulées

Tous les noms de factures, montants, indicateurs, niveaux de couverture et contrôles affichés sont des exemples de conception. Les boutons ne transmettent aucun fichier, message ou décision. Aucun appel réseau applicatif n'est effectué.

## Ouvrir le prototype

Double-cliquer sur :

```text
docs/prototype-refonte-v1/ouvrir-prototype.cmd
```

Ou ouvrir directement `docs/prototype-refonte-v1/index.html`.

## Ce que l'utilisateur doit évaluer

1. Comprend-on immédiatement où regarder et quoi décider ?
2. La densité est-elle agréable ou trop faible/trop forte ?
3. La navigation correspond-elle au vocabulaire réel de la collectivité ?
4. Le panneau facture montre-t-il les preuves dans le bon ordre ?
5. Le Site 360° constitue-t-il une bonne porte d'entrée ?
6. Les couleurs et la personnalité générale correspondent-elles à l'image souhaitée ?

## Suite recommandée

Après retour utilisateur, transformer ce premier jet en socle React du SaaS : tokens, shell, navigation, composants, données simulées typées et tests. La première tranche raccordée doit rester le dossier facture commun, puis le cockpit et le Site 360°.
## Alignement avec la charte PO²

La structure du prototype est conservee, mais ses couleurs et sa typographie sont encore provisoires. L alignement de marque est documente dans [[31-Analyse-charte-graphique-et-alignement-prototype]] : bleu nuit `#1D3150`, vert accent `#74B44A`, gris techniques et titres Montserrat. Les vrais fichiers SVG transparents du logo restent necessaires avant integration definitive.