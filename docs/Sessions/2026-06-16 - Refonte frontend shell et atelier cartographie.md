# 2026-06-16 - Refonte frontend shell et atelier cartographie

> IA : Codex
> Duree approximative : session longue de cadrage, implementation, validation et push
> PR : <https://github.com/PAB34/Po2/pull/13>

## Objectif de la session

Reprendre le chantier de refonte totale du frontend sans casser l'existant.

Le besoin utilisateur a ete clarifie ainsi :

- ne pas refaire seulement une page existante ;
- organiser les fonctionnalites backend/front deja developpees dans une nouvelle interface produit ;
- disposer d'un support graphique pour commenter les sections, sous-sections et raccordements ;
- garder une possibilite de retour arriere via branche/PR avant merge.

## Ce qui a ete fait

### Chantier 1 - Socle navigation produit

Une premiere structure de navigation metier a ete ajoutee au front React.

Commits :

- `db8b2f0` - `feat(frontend): add product navigation shell`
- `eaaf001` - `feat(frontend): rename energy domain to fluids`

Fichiers principaux :

- `saas/frontend/src/App.tsx`
- `saas/frontend/src/pages/HomePage.tsx`
- `saas/frontend/src/pages/ProductDomainPage.tsx`
- `saas/frontend/src/styles.css`

Routes conteneurs ajoutees :

- `/patrimoine`
- `/marches`
- `/technique`
- `/administration`

Routes conservees :

- `/buildings/*`
- `/energie/*`
- `/factures/*`
- `/cpe/*`

Decision importante : les routes techniques `/energie/*` restent en place pour compatibilite, mais le libelle produit visible devient `Fluides & consommations`.

### Chantier 2 - Atelier graphique de cartographie frontend

Commit :

- `b24c4e4` - `feat(frontend): add mapping workshop`

Fichier principal :

- `docs/atelier-cartographie-frontend.html`

L'atelier local permet :

- de raccorder chaque fonctionnalite existante a une section/sous-section cible ;
- de decrire ce que l'utilisateur doit voir dans chaque ecran cible ;
- d'ecrire la decision utilisateur aidee ;
- d'ajouter des notes UX ;
- d'exporter les decisions en Markdown ou JSON ;
- de sauvegarder dans le navigateur.

L'atelier a ete servi localement sur :

```text
http://127.0.0.1:8765/atelier-cartographie-frontend.html
```

Le bouton de sauvegarde a ete clarifie : il affiche maintenant une heure de sauvegarde, par exemple `Sauvegarde a 16:37:08`.

### Chantier 3 - Arbitrages produit actees

Arbitrages retenus avec l'utilisateur :

- `Energie` devient `Fluides & consommations` ;
- Fluides couvre `Electricite`, `Gaz`, `Eau`, `Prix contractuels`, `Preconisations`, `Donnees distributeurs` ;
- les factures fournisseurs sortent de Fluides ;
- le parcours facture cible devient `Marches & contrats > Factures marche` ;
- `Technique > Fluides et conformite` devient `Technique > F-Gaz / ESP`.

Raison : les factures sont un parcours marche/finance transversal, tandis que Fluides doit rester centre sur les consommations, donnees distributeurs, prix contractuels et preconisations.

### Chantier 4 - Documentation de cadrage

Documents ajoutes ou mis a jour :

- `docs/17-Refonte-frontend-capacites-metier.md`
- `docs/18-Registre-raccordement-frontend.md`
- `docs/19-Atelier-cartographie-frontend.md`
- `docs/00-Index.md`

## Validation

Validations locales :

- atelier ouvert dans le navigateur integre ;
- presence verifiee de `Fluides & consommations > Vue d'ensemble` ;
- presence verifiee de `Fluides & consommations > Eau` ;
- presence verifiee de `Technique > F-Gaz / ESP` ;
- ancien libelle cible `Energie > Vue d'ensemble` absent de l'atelier ;
- `git diff --check` OK.

Validation CI :

- PR #13 verte dans GitHub Actions apres push du commit `eaaf001`.

Limite locale :

- build frontend non execute localement : `npm` et `node_modules` indisponibles dans l'environnement local Codex.

## Ce qui reste a faire / handoff

### Priorite 1 - Premier vrai parcours refondu

Commencer par :

```text
Marches & contrats > Factures marche
```

Objectif UX :

```text
importer -> controler -> comprendre -> decider -> exporter
```

Fonctionnalites a reutiliser :

- imports ENGIE/EDF ;
- lots et historique imports ;
- controles BPU/TURPE/ENEDIS ;
- decisions facture ;
- liaison/export finance XLSX ;
- matrice comptable multi-lots a preparer pour ENGIE, EDF, TotalEnergies, DALKIA, SPIE.

### Priorite 2 - Ne pas confondre les domaines

Regle de vocabulaire a conserver :

- `Fluides & consommations` = electricite, gaz, eau, donnees distributeurs, prix, preconisations ;
- `Marches & contrats > Factures marche` = import, controle, decision, export finance des factures ;
- `Technique > F-Gaz / ESP` = obligations et risques techniques lies aux fluides frigorigenes / equipements sous pression.

### Priorite 3 - Merge PR #13

La PR #13 est verte et mergeable.

Avant merge :

- relire le diff GitHub ;
- confirmer que le libelle `Fluides & consommations` convient ;
- confirmer que le parcours `Factures marche` est bien la prochaine priorite.

## Notes & decisions

- La refonte doit rester progressive : ne pas supprimer les routes existantes tant que les nouveaux parcours ne remplacent pas reellement les anciens.
- Les docs et l'atelier servent de contrat de refonte entre l'utilisateur et l'implementation React.
- Les changements non lies presents dans le working tree n'ont pas ete stages ni pousses.

## Pour la prochaine IA - entree en matiere

```text
J'ai lu :
- docs/00-Index.md
- docs/04-Etat-actuel-du-dev.md
- docs/17-Refonte-frontend-capacites-metier.md
- docs/18-Registre-raccordement-frontend.md
- docs/19-Atelier-cartographie-frontend.md
- docs/Sessions/2026-06-16 - Refonte frontend shell et atelier cartographie.md

Je sais que la PR #13 contient la premiere brique de refonte frontend et que la CI est verte.
Je sais que la prochaine priorite est Marches & contrats > Factures marche.
Je ne dois pas demander d'installation locale au poste utilisateur.
Je propose de commencer par maquetter et raccorder le parcours importer -> controler -> comprendre -> decider -> exporter.
```
