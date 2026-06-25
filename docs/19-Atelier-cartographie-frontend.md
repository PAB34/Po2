# 19 - Atelier cartographie frontend

> Date : 2026-06-16.
> Objectif : disposer d'une interface graphique locale pour decider quoi raccorder dans la nouvelle navigation avant de continuer le code React.

## Fichier

Atelier HTML autonome :

```text
docs/atelier-cartographie-frontend.html
```

Il fonctionne sans serveur, sans `npm` et sans base de donnees.

## Usage

1. Ouvrir `docs/atelier-cartographie-frontend.html` dans un navigateur.
2. Onglet `1. Raccorder l'existant` :
   - choisir la section cible ;
   - choisir la sous-section ;
   - choisir l'action : `Brancher`, `Refondre`, `Garder expert`, `Cacher`, `A cadrer`, `Hors produit` ;
   - ajouter un commentaire si besoin.
3. Onglet `2. Dessiner le front cible` :
   - decrire ce que l'on veut voir dans chaque section/sous-section ;
   - decrire la decision utilisateur aidee ;
   - noter les commentaires UX.
4. Onglet `3. Exporter la decision` :
   - copier le Markdown ;
   - ou telecharger le JSON.

## Sauvegarde

Les choix sont sauvegardes dans le navigateur via `localStorage`.

Pour transmettre les decisions a Codex :

- utiliser le bouton `Telecharger JSON`, puis partager le fichier ;
- ou copier le Markdown exporte et le coller dans la conversation.

## Place dans le chantier

Cet atelier doit etre utilise avant de poursuivre la refonte React.

Ordre recommande :

1. Valider la cartographie existant -> section/sous-section.
2. Valider la cible front par section/sous-section.
3. Reprendre `ProductDomainPage.tsx` et la navigation React avec ces decisions.

## Travail execute le 2026-06-16

PR GitHub : <https://github.com/PAB34/Po2/pull/13>

Commits principaux :

- `db8b2f0` - `feat(frontend): add product navigation shell`
- `b24c4e4` - `feat(frontend): add mapping workshop`
- `eaaf001` - `feat(frontend): rename energy domain to fluids`

### 1. Socle de refonte frontend

Une premiere couche de navigation produit a ete ajoutee sans supprimer les anciennes routes.

Routes conteneurs ajoutees :

- `/patrimoine`
- `/marches`
- `/technique`
- `/administration`

Routes anciennes conservees comme parcours fonctionnels ou alias :

- `/buildings/*`
- `/energie/*`
- `/factures/*`
- `/cpe/*`

Fichiers React principaux :

- `saas/frontend/src/App.tsx`
- `saas/frontend/src/pages/HomePage.tsx`
- `saas/frontend/src/pages/ProductDomainPage.tsx`
- `saas/frontend/src/styles.css`

### 2. Atelier de cartographie

L'atelier HTML local a ete ajoute pour permettre de commenter et arbitrer la future interface avant de coder trop loin.

Fonctions livrees :

- onglet `Raccorder l'existant` : chaque fonctionnalite developpee est rattachee a une section/sous-section cible ;
- onglet `Dessiner le front cible` : chaque ecran cible peut recevoir une proposition, une decision utilisateur aidee et des notes UX ;
- onglet `Exporter la decision` : export Markdown et JSON ;
- sauvegarde dans le navigateur ;
- bouton de sauvegarde clarifie avec affichage de l'heure de sauvegarde.

### 3. Arbitrages produit actees

Arbitrages retenus dans l'atelier et dans la navigation :

- le domaine `Energie` devient `Fluides & consommations` ;
- le domaine Fluides couvre `Electricite`, `Gaz`, `Eau`, `Prix contractuels`, `Preconisations`, `Donnees distributeurs` ;
- les factures fournisseurs sortent de Fluides et deviennent `Marches & contrats > Factures marche` ;
- `Technique > Fluides et conformite` devient `Technique > F-Gaz / ESP` pour eviter la confusion avec le domaine Fluides ;
- les routes techniques `/energie/*` restent conservees pour ne pas casser l'existant, mais les libelles visibles changent progressivement.

### 4. Documentation associee

Documents ajoutes ou mis a jour :

- `docs/17-Refonte-frontend-capacites-metier.md` : cadrage produit, domaines, parcours et ordre de chantier ;
- `docs/18-Registre-raccordement-frontend.md` : registre de raccordement ecrans cibles -> fonctionnalites existantes -> code actuel ;
- `docs/19-Atelier-cartographie-frontend.md` : mode d'emploi et bilan de l'atelier ;
- `docs/00-Index.md` : index mis a jour avec les documents 17, 18 et 19.

### 5. Validation

Validations faites :

- atelier ouvert et verifie dans le navigateur integre sur `http://127.0.0.1:8765/atelier-cartographie-frontend.html` ;
- verification que `Fluides & consommations > Vue d'ensemble`, `Fluides & consommations > Eau` et `Technique > F-Gaz / ESP` apparaissent ;
- verification que l'ancien libelle cible `Energie > Vue d'ensemble` n'apparait plus dans l'atelier ;
- `git diff --check` OK ;
- PR #13 verte dans GitHub Actions.

Validation non faite localement :

- build frontend local non execute, car le poste Codex local ne dispose pas de `npm`/`node_modules` dans ce contexte. La validation build est donc portee par GitHub Actions.

## Prochaine action recommandee

La prochaine action produit est de transformer les decisions de l'atelier en premiere vraie maquette front raccordee, en commencant par :

```text
Marches & contrats > Factures marche
```

Objectif : construire le parcours cible `importer -> controler -> comprendre -> decider -> exporter`, en reutilisant les fonctionnalites deja developpees autour des factures ENGIE/EDF, du controle BPU/TURPE/ENEDIS et de l'export finance.

## Complement de methode - 2026-06-22

L'atelier existant constitue une premiere cartographie, mais il doit etre enrichi avant de devenir la source de verite : utilisateur, situation, decision, donnees, regles, qualite, preuve, statut de validation et KPI UX. Voir [[21-Cartographie-fonctionnelle-vers-experience-utilisateur]]. Le shell est livre ; le design system reste a construire.
