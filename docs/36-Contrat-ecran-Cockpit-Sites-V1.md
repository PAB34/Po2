# 36 — Contrat d’écran Cockpit Direction et Sites 360° V1

> Date : 2026-06-25  
> Statut : cadrage UX + prototype sans backend  
> Prototype : `docs/prototype-refonte-v1/index.html`

## Intention

Le cockpit ne doit pas être une page de beaux indicateurs isolés. Il doit être le point d’entrée quotidien qui transforme les signaux en décisions : facture à payer ou contester, abonnement à recalibrer, budget à réarbitrer, équipement CVC à financer, site à fiabiliser.

La fiche Site 360° joue le rôle inverse : elle part d’un site et rassemble le contexte nécessaire avant de décider.

## Règle d’expérience

Chaque signal affiché doit répondre à quatre questions :

1. quelle est la source du signal ?
2. quelle preuve permet de le croire ?
3. qui doit décider ou instruire ?
4. quelle est l’action suivante ?

Si une alerte ne peut pas répondre à ces quatre questions, elle reste une donnée, pas une décision.

## Cockpit Direction

### C01 — Lecture consolidée

Le cockpit conserve les KPI de haut niveau : budget opérationnel, atterrissage, consommations fluides, travaux prioritaires. Ces chiffres servent à orienter la lecture, pas à remplacer les écrans métier.

### C02 — File de décisions

La file de décisions doit mélanger les domaines lorsque c’est utile : factures, budget, technique, fluides, maintenance. Le tri se fait par impact, échéance, confiance et responsabilité.

### C03 — Chaîne de décision V1

Ajout dans le prototype : une carte visuelle relie les domaines prioritaires à leur preuve et à leur action suivante.

| Domaine | Preuve attendue | Décision cible |
|---|---|---|
| Factures | Contrôle facture + matrice comptable | Payer, réclamer ou transmettre aux finances |
| Fluides | Courbes ENEDIS/GRDF, DJU, contrat fournisseur | Expliquer une dérive ou recalibrer un abonnement |
| Technique | Criticité CVC, devis, couverture maintenance | Arbitrer P3, PPT ou ordre de service |
| Budget | Engagé, facturé, atterrissage par opération | Réallouer, alerter ou préparer N+1 |
| Sites 360° | Patrimoine, contrats, compteurs, équipements | Vérifier le contexte avant décision |

## Sites 360°

### S01 — Portefeuille puis détail

Le portefeuille liste les sites selon qualité, budget, dérive fluides et criticité. L’utilisateur ouvre ensuite une fiche site seulement lorsqu’un arbitrage ou une vérification est nécessaire.

### S02 — Onglets métier

La fiche conserve les onglets Synthèse, Fluides, Contrats, Technique, Budget/PPT et Documents. Chaque onglet doit rester connecté au même référentiel site.

### S03 — Décisions reliées au site

Ajout dans le prototype : la synthèse du site affiche les décisions reliées au site : facture à décider, abonnement à vérifier, maintenance, budget. Chaque entrée indique la preuve et renvoie vers l’écran métier.

## Points à garder pour le raccordement React

- ne pas créer un cockpit séparé par profil ; conserver un cockpit adaptable ;
- ne pas dupliquer les données du site dans chaque module ; le site est le pivot ;
- toute facture validée doit conserver les versions de contrat, matrice comptable et référentiels appliquées ;
- toute décision doit produire une trace : auteur, date, justification, preuves consultées ;
- les priorités du cockpit doivent être calculables depuis les statuts réels, pas saisies à la main.

## Limites du prototype

Les chiffres, alertes, sites et décisions sont simulés. Le prototype valide la forme de l’expérience, pas encore la justesse des calculs ni le raccordement aux API.
