# 26 - Audit de couverture de l'atelier BPMN

> Date : 2026-06-22
> Objet : verifier que les fonctionnalites reelles de PatrimoineOp sont representees dans l'atelier produit/UX.

## Sources controlees

- registre canonique : [[24-Cockpit-canonique-reconstruction-produit-frontend]] ;
- navigation et routes React dans `saas/frontend/src/App.tsx` ;
- 29 pages et 11 composants frontend ;
- 19 groupes de routes backend et 299 endpoints ;
- 55 services metier ;
- 64 migrations Alembic, jusqu'a `0063_add_control_detail_and_tva.py` ;
- backlog et etat actuel du developpement.

## Resultat

Le premier atelier couvrait 27 des 50 capacites du registre. La passe differentielle a identifie 23 capacites absentes. Apres enrichissement, les 50 capacites canoniques sont rattachees a au moins un cadre : couverture fonctionnelle `50/50`.

Cette couverture signifie que chaque capacite est visible dans l'atlas. Elle ne signifie pas que chaque experience est validee : les statuts `partiel`, `a construire` et `futur` restent a travailler avec les utilisateurs.

## Atlas obtenu

1. L0 - Carte generale PatrimoineAuCarre.
2. L1 - Factures de fourniture multi-fournisseurs.
3. L2 - Controle detaille ENGIE.
4. L2 - Controle gaz TotalEnergies.
5. L1 - Patrimoine et rattachements.
6. L1 - ENEDIS, GRDF, DJU et atterrissages.
7. L1 - CPE DALKIA complet.
8. L1 - CVC, reglementaire et PPT.
9. L1 - Couverture maintenance DALKIA / SPIE.
10. L1 - Budget, realise et atterrissage.
11. L1 - Administration, qualite et audit.

## Capacites ajoutees lors de la passe

- patrimoine : `CORE-01`, `PAT-02`, `PAT-03`, `OCC-01`, `LEASE-01`, `FIELD-01` ;
- fluides : `ELEC-03`, `FORECAST-01`, `FORECAST-02`, `WATER-01`, `OPERAT-01` ;
- DALKIA : `CPE-01` a `CPE-05` ;
- technique : `CVC-02`, `REG-01`, `REG-02`, `BACS-01` ;
- maintenance : `SPIE-01` ;
- exploitation : `OPS-01` ;
- hors perimetre : `OUT-01`, visible comme annotation et explicitement exclu de PatrimoineOp.

## Points de vigilance confirmes

- le socle DALKIA est tres riche mais son experience reste fragmentee ;
- ENEDIS, GRDF et DJU existent, mais l'atterrissage annuel kWh puis euros reste a concevoir ;
- le CVC et le suivi F-Gaz/ESP existent, mais le PPT chiffre manque ;
- la couverture DALKIA/SPIE par site n'est pas encore construite ;
- la matrice comptable existe, mais budget initial, engagements, mandats et atterrissage transversal manquent ;
- les files de travail, responsables, echeances et l'audit transversal restent incomplets ;
- les referentiels gaz pedagogiques et la synthese globale avec drill-down restent en TO-BE.

## Regle de synchronisation

Une nouvelle fonctionnalite doit etre ajoutee au registre canonique puis rattachee a un diagramme, un profil, une decision, une preuve et un ecran cible. La fusion versionnee de l'atelier ajoute les nouveaux elements sans ecraser les deplacements, liens et commentaires utilisateur.
## Extension du registre apres les passes V1

Le premier audit avait identifie 50 capacites. La passe sur les reimports et decisions de factures a explicite cinq capacites deja presentes ou partiellement presentes dans l etat actuel : deduplication, historique, audit des imports, reclamation et contacts de marche. Le modele actuel couvre donc 55 capacites.

La projection V1 ajoute onze fondations ou fonctions cibles : design system, cockpits, Site 360, RBAC, recherche, notifications, rapports, accessibilite, mesure UX, generation de message et envoi direct futur. Le registre cible et l atelier couvrent desormais 66 capacites sur 66.
