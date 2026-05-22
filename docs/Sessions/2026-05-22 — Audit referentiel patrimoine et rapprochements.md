# Session - Audit referentiel patrimoine et rapprochements

## Demande

Verifier ce qui existe pour faire de la liste patrimoine le referentiel des sites, batiments et locaux auquel rattacher PRM ENEDIS, compteurs gaz, CPE DALKIA et futurs contrats de maintenance. Proposer l'ordre des prochaines actions et documenter Obsidian.

## Constats code

- Le schema patrimoine conserve deja `Site -> Building -> Local`.
- La liste et les fiches UI restent surtout orientees `Building`.
- Les PRM ENEDIS ont deja un nom et une adresse contractuels dans le module Energie, mais aucun lien au patrimoine.
- `BuildingMeterLink` donne un premier lien manuel compteur -> batiment, sans console de rapprochement et sans choix direct Site/Local.
- `CpeSite` DALKIA garde ses noms contractuels et ses PCE dans le module CPE, sans lien patrimoine.
- Le module maintenance est encore documente seulement.

## Decision documentee

Ajout de [[Decisions/008-referentiel-patrimoine-et-rapprochements]] :

- le patrimoine est le referentiel maitre ;
- les objets externes passent par une boite de rapprochement ;
- les introuvables restent visibles avec un statut a traiter ou a creer.

## Prochain ordre conseille

1. Tester et stabiliser la liste hierarchique Site/Batiment/Local.
2. Construire la boite de rapprochement et le backlog des introuvables.
3. Rapprocher d'abord les PRM ENEDIS depuis leurs noms/adresses.
4. Brancher les sites CPE DALKIA et leurs PCE sur ce flux.
5. Faire arriver maintenance ensuite sur les memes referents.
6. Revoir la navigation UI apres les retours de test des modules deja livres.
