# Session 2026-06-22 - Reorientation direction et cap frontend

## Objectif

Confronter les attentes direction aux travaux prevus et recentrer le produit sur le controle des factures, le pilotage budgetaire, le patrimoine CVC et la couverture des marches, tout en cadrant un front moderne.

## Ce qui a ete fait

- lecture de l'index, du backlog, de l'etat actuel, de la roadmap et des documents UX/maintenance/CVC ;
- verification rapide du frontend et de ses principaux monolithes ;
- creation de [[20-Cap-direction-2026-factures-budget-CVC-maintenance]] ;
- ajout des chantiers dossier facture, budget/atterrissage, PPT CVC, couverture, SPIE et front au backlog ;
- passage en P0 des chantiers structurants concernes ;
- mise a jour de l'index, de l'etat actuel et de la roadmap.

## Handoff suivant

1. Demarrer le Lot 0 du document 20 : pieces DALKIA/SPIE, budget initial et matrice comptable reelle.
2. Choisir des factures reelles par marche et formaliser les controles bloquants.
3. Commencer le front par les fondations partagees puis reconstruire Factures verticalement, pas par un restylage global.
4. Ne pas supprimer les anciennes routes ou les doublons CVC/BPU avant arbitrage.

## Notes et decisions

- Les attentes direction sont compatibles avec l'existant ; l'enjeu est la convergence et la preuve de bout en bout.
- SPIE est un marche P2 propre et ne doit pas heriter du moteur CPE DALKIA.
- La matrice comptable devient l'axe de consolidation budgetaire.
- Aucun ADR technique : schemas et design system restent a concevoir.

## Message pour la prochaine IA

Lire [[20-Cap-direction-2026-factures-budget-CVC-maintenance]], puis prendre le premier livrable P0 du [[Backlog]]. Preserver les changements utilisateur deja presents dans le worktree.

## Complement consommations et cartographie UX

- ajout du cinquieme axe P0 : series ENEDIS/GRDF, DJU transversal et atterrissage kWh puis euros ;
- creation de [[21-Cartographie-fonctionnelle-vers-experience-utilisateur]] ;
- constat design : shell/navigation livres, design system strict encore a construire ;
- registre frontend enrichi avec Performance & DJU et Atterrissage consommations.

## Complement strategie de developpement et profils

- decision proposee : deux pistes synchronisees, capacites metier et experience produit ;
- ajout de huit profils cibles, dont sept internes et un prestataire futur ;
- distinction profil d'usage / permission / perimetre ;
- creation de [[22-Developpement-deux-pistes-et-profils-utilisateurs]].

## Correction perimetre fournisseurs

La liste des tranches verticales omettait EDF et TotalEnergies. Correction : socle commun de facture de fourniture, puis tranches ENGIE electricite, EDF electricite, TotalEnergies gaz et liaison ENEDIS/GRDF/DJU. Les regles fournisseur restent specifiques ; seul le dossier, la decision, la ventilation et l'export sont partages.

## Seconde passe de controle

- comparaison de 19 fichiers de routes, environ 295 endpoints, 52 services, 21 modeles, 60 migrations, 29 pages et 11 composants ;
- confirmation des cinq axes ;
- ajout des quatre fondations transversales ;
- angles morts identifies : execution maintenance, engagements/mandats, workflow/audit, occupation, eau, conformites futures et mesure des gains ;
- creation de [[23-Seconde-passe-audit-fonctionnel-et-angles-morts]].

## Cockpit canonique de reconstruction frontend

- creation de [[24-Cockpit-canonique-reconstruction-produit-frontend]] avec un premier registre de plus de 40 capacites ;
- separation claire entre etat du moteur, etat de l'experience et decision de reconstruction ;
- creation de [[Templates/Fiche-capacite-produit]] et [[Templates/Contrat-ecran-UX]] ;
- le document 24 devient la source de verite quotidienne, les audits 13/14/18/21/23 deviennent ses sources.

## Atelier BPMN Produit & UX

- creation de `docs/atelier-bpmn-produit/index.html` ;
- cartes prechargees L0 general, L1 factures multi-fournisseurs et L2 ENGIE ;
- couloirs, cadres deplacables, relations typees, boites de commentaire, filtres AS-IS/TO-BE ;
- vues Registre et Couverture UX ;
- sauvegarde locale et import/export JSON ;
- validation navigateur complete sans erreur console ;
- documentation : [[25-Atelier-BPMN-produit-UX]].

## Légende intégrée à l'atelier BPMN

Ajout d'une entrée visible `Légende & fonctionnement` détaillant niveaux L0/L1/L2, couloirs, types de cadres, couleurs de statut, relations, AS-IS/TO-BE, manipulations et méthode de travail. Validation navigateur OK, aucune erreur console.

## Gel fonctionnel et synchronisation TotalEnergies

- decision utilisateur : arret temporaire du developpement de nouvelles fonctionnalites apres la PR #25, au profit de la conception UX ;
- ajout du L2 `Controle gaz TotalEnergies` dans l'atelier ;
- fiche de verification par facture et trace detaillee cartographiees en AS-IS developpe ;
- referentiels gaz pedagogiques et synthese globale avec drill-down places en TO-BE, sans lancement du developpement ;
- ajout d'un lanceur local et d'une fusion versionnee non destructive des nouveaux elements ;
- synchronisation du code vers l'atelier volontairement assistee : elle doit etre demandee apres une livraison.
## Audit complet de couverture de l atelier

- comparaison du registre canonique avec 29 pages, 11 composants, 299 endpoints, 55 services et 64 migrations ;
- couverture initiale : 27 capacites sur 50 ;
- ajout de sept parcours L1 : patrimoine, fluides/DJU/atterrissages, DALKIA, CVC/reglementaire/PPT, maintenance DALKIA-SPIE, budget et operations ;
- couverture finale : 50 capacites sur 50 dans 11 diagrammes ;
- module pronostics rendu visible comme hors perimetre PatrimoineOp ;
- validation navigateur des 11 diagrammes et de la vue Couverture UX ;
- rapport : [[26-Audit-couverture-atelier-BPMN-2026-06-22]].
## Fiches specialisees par type de cadre

- ajout de schemas distincts pour evenement, tache humaine, tache systeme, decision, ecran UX, donnee/preuve, capacite et annotation ;
- ajout de details de relation : condition, information transportee, cadence et responsabilite ;
- preremplissage expert non destructif des 151 cadres et 164 relations ;
- ajout d indices de code selon les familles de capacites ;
- recherche et import/export etendus aux nouveaux details ;
- corrections utilisateur prioritaires : seuls les champs absents sont completes lors des synchronisations ;
- controle automatise : 11 diagrammes, 151 cadres et 164 relations, aucun champ specialise manquant.
## Modele V1 independant

- ajout du selecteur `Etat actuel - AS-IS` / `V1 - Plateforme operationnelle cible` ;
- migration non destructive de l atelier existant vers deux modeles independants ;
- V1 composee des 11 parcours projetes et de trois nouveaux parcours : cockpits par profil, Site 360 degres, design system et fondations produit ;
- V1 : 14 diagrammes, 193 cadres, 215 relations, dont 130 cadres `Specifie V1` ;
- ajout de neuf capacites au registre cible : design system, cockpits, Site 360, RBAC, recherche, notifications, rapports, accessibilite et mesure UX ;
- export/import JSON compatible avec les deux versions ;
- test automatise : etat actuel conserve a 11 diagrammes et 151 cadres, isolation des modifications V1 confirmee, aucun detail specialise manquant ;
- reference : [[27-Modele-V1-plateforme-operationnelle]].