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
