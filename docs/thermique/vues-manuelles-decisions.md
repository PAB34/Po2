# Coupes et façades : le thermicien d'abord, l'IA ensuite (D206 à D210)

Date : 2026-10-01. Suite de `cadres-des-vues-decisions.md` (D205), après le test du projet 1 (PC10, PC11).

## Constats du test (2026-10-01)

1. Une coupe dont le cadre est corrigé **disparaît du plan** : ses pièces sont vidées (D205), le trait
   déduit des pièces (D190) ne se retrouve plus, la vue passe en « non située ».
2. Une vue **ne se renomme pas** : coupes C et D inversées par l'agent, impossible à remettre.
3. **Mesures fausses** : menuiserie « 0,02 m × 1,83 m », hauteur d'étage 0,9 m. Cause : le *haut* d'une vue
   est un vecteur de la **page PDF** ; l'écran montre la planche tournée (`rotation_deg`), et la liste
   « Haut de la vue » (D205) parle de la page, pas de ce que voit le thermicien. Un haut de travers projette
   la largeur sur la hauteur.
4. **Mode sombre** : textes gris clair et boutons « fantômes » illisibles.

## Existant vérifié

- `thermique_lecture_coupes.py` : `corriger_vue` (cadre, haut), `hauteurs_du_plan` (trait relevé par nom,
  sinon déduit), `confirmer_hauteur` (deux clics le long du haut).
- `FenetreCoupe.tsx` : raster de la planche à sa rotation d'affichage ; `mesureDeDeuxCoins` (baies.ts).
- `CadresDesVues.tsx` : cadres, liste des vues, haut en termes de page.
- Le raster accepte n'importe quelle rotation (`getRaster(token, id, rotation)`, pdfium : 90 = horaire).

## Décisions

- **D206 — Une vue se corrige entièrement à la main.** `PATCH /vues/{id}` accepte aussi `nom` (unique sur
  la planche) et `nature` (coupe/façade). Renommer n'efface pas la lecture ; changer de nature, si.
- **D207 — Le haut se dit comme on le voit.** La liste « Haut de la vue » parle de l'écran ; la conversion
  écran → page passe par la transformation du raster affiché. Le serveur garde un vecteur de page.
- **D208 — La fenêtre de coupe/façade s'ouvre à l'endroit.** Elle charge le raster à la rotation qui met le
  haut de la vue en haut de l'écran. Un bouton « La vue est de travers : pivoter » tourne le haut d'un quart
  de tour (et relance la lecture d'une coupe, comme D205).
- **D209 — Le trait d'une coupe se trace à la main sur le plan.** Deux clics (extrémités), un troisième du
  côté regardé. Il est rangé comme trait relevé, avec l'identifiant de la vue (`vue_id`, `manuel`), et passe
  avant tout trait trouvé par le nom ou déduit. Une vue « à relire » reste ainsi cliquable sur le plan.
- **D210 — Mode sombre.** Les couleurs de texte secondaire et des boutons fantômes de l'outil passent par
  des jetons redéfinis en sombre.

- **D211 — Mesures visibles et posées à la main** (lot 2). Pendant la mesure, le rectangle de la menuiserie
  et la hauteur se dessinent avec leurs cotes, le long des axes de la vue. Une hauteur n'est plus envoyée au
  second clic : elle s'affiche d'abord. Hors de 1,50–15 m elle est refusée (« Refaire la mesure ») ; hors de
  2–6 m elle est signalée. Elle se pose ensuite **sur les locaux cliqués du plan** (hauteur saisie, sans IA)
  ou corrige les pièces lues de la coupe (D191), si la coupe en a. Une menuiserie de moins de 20 cm dans un
  sens est signalée comme suspecte.

## À venir (lots suivants)

- Lot 4 : « Faire lire par l'IA » par vue, à l'initiative du thermicien.

## Questions

1. (ouverte) Le repérage automatique des cadres doit-il rester proposé à l'import, ou le thermicien
   cadre-t-il toujours d'abord ? — proposé : il reste, comme proposition à valider.
