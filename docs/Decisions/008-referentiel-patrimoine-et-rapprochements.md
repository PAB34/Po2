# ADR 008 - Referentiel patrimoine et rapprochements

## Statut

Accepte le 2026-05-22.

## Contexte

Po2 dispose maintenant d'une liste patrimoniale hierarchique `Site -> Building -> Local`.

En parallele :

- ENEDIS fournit des PRM avec noms et adresses contractuels ;
- le gaz devra porter des PCE GRDF ;
- le CPE DALKIA possede deja ses propres `CpeSite` et certains PCE ;
- les contrats de maintenance devront couvrir plusieurs lieux du patrimoine.

Des objets externes peuvent ne pas trouver immediatement leur batiment, site ou local de reference. Les creer automatiquement ou les perdre dans un import rendrait le patrimoine moins fiable.

## Decision

La liste patrimoniale est le referentiel maitre des lieux de Po2.

- Un objet energie, CPE ou contrat se rattache a un referent patrimoine existant parmi `Site`, `Building` ou `Local`.
- Une source externe non rattachee est conservee dans une boite de rapprochement avec son identifiant, son libelle source, son statut, son score et sa decision.
- Un objet non identifiable doit pouvoir rester `a_traiter`, `ambigu` ou `a_creer`; il ne doit pas etre supprime silencieusement ni devenir automatiquement un faux batiment.
- Les modules metier gardent leurs specificites : PRM ENEDIS, PCE GRDF, `CpeSite` DALKIA et contrats de maintenance ne deviennent pas eux-memes le referentiel patrimoine.

## Consequences

### Positives

- Une seule liste de lieux fait foi.
- Les lacunes du patrimoine deviennent visibles.
- Le rapprochement peut commencer avec ENEDIS et etre reutilise pour GRDF, DALKIA et maintenance.
- L'interface pourra s'organiser autour des fiches patrimoine plutot qu'autour de listes paralleles.

### Cout

- Le lien compteur V1 `BuildingMeterLink` ne suffit pas seul pour couvrir Site/Batiment/Local et les introuvables.
- Il faut une console de rapprochement avant de brancher trop de modules sur des champs texte de noms.
- Certains imports resteront volontairement en attente de validation utilisateur.

## Alternatives ecartees

### Creer automatiquement un batiment a chaque PRM/PCE introuvable

Ecarte : cela polluerait le referentiel avec des libelles contractuels ou des usages techniques mal qualifies.

### Laisser chaque module garder sa propre liste de sites

Ecarte : ENEDIS, DALKIA et maintenance divergeraient rapidement et les analyses par patrimoine deviendraient fragiles.

## Voir aussi

- [[Modules/Patrimoine]]
- [[Modules/Energie-Gaz]]
- [[Modules/Maintenance-Contrats]]
- [[Backlog]]
