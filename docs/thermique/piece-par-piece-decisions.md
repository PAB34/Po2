---
read_policy: lire avant de coder la page « Pièce par pièce » de l'application thermique
---

# Page « Pièce par pièce » — décisions

Date : 2026-09-22. Demande de l'utilisateur (D28, [locaux-decisions.md](locaux-decisions.md)) : dans l'application,
le thermicien modifie un local, clique **« Remodéliser »**, revérifie, **enregistre** et passe au local suivant.
Rien n'est codé tant que les questions du § 4 ne sont pas tranchées.

## 1. Existant vérifié (après la refondation, `main` = `119df335`)

| Élément | État |
|---|---|
| `SheetPage` + `components/TileSheetViewer` (298 l.) | affichage d'une planche en tuiles, rotation, échelle : **base de la vue plan** |
| `ProjectPage` | liste des planches ; onglets « Plans et planches » et « Bibliothèque » |
| Bibliothèque du projet (`ThermiqueComponent`, `ComponentLibrary`, `WallEditor`) | parois et menuiseries avec U calculé : **cible des composants de l'étude** |
| Modèles en base | projet, document, planche, composant. **Aucune table pour une étude de niveau** |
| Routes | socle seulement (projets, documents, planches, tuiles, bibliothèque) |
| Chaîne d'étude (`run_etude_niveau.py`) | tourne **sur le poste, dans Claude Code** (mode session, pas d'API) ; produit `passe-globale.json` (locaux, objets), `enveloppe.json`, `enveloppe.raw.json` (éléments d'enveloppe rattachés aux locaux), `enveloppe/enveloppe-manifeste.json` (tronçons, échelle), `catalogue.json`, `controle.json` |
| Calcul des fiches (`thermique_fiches_locaux.fiches`) | à partir de l'analyse, du manifeste et des éléments : côtés (adjacence, épaisseur, orientation, déperditif), enveloppe rattachée. **N'a pas besoin de l'image** : rapide, exécutable sur le serveur |
| Rattachement des éléments aux locaux (`thermique_enveloppe_pieces.decouper_par_piece`) | pas d'image non plus : rejouable après une modification de contour |
| Recalage des contours (`thermique_locaux.recaler_pieces`) | a besoin de l'image de la page (rendu 300 dpi) : plus lourd |
| Dépendances serveur | `scipy`, `numpy`, `Pillow` présents ; **`shapely` absent de `requirements.txt`** : le moteur ne tournerait pas en production, et les tests qui l'importent échouent en intégration continue |

Constat : la page n'a pas besoin de l'agent. Tout ce que « Remodéliser » recalcule (rattachement des éléments,
côtés, adjacences, parois déperditives, métrés) est du calcul classique, déjà écrit et testé.

## 2. Principe

1. **Sur le poste (Claude Code)** : `run_etude_niveau.py` fait l'étude d'un niveau (agents + algorithmes) et écrit
   un **fichier d'étude unique** `etude-<niveau>.json`.
2. **Dans l'application** : le thermicien importe ce fichier sur la planche du niveau, puis valide local par local.
3. Ce que le thermicien signale comme hors de portée du calcul (zonage d'un grand local, doute de lecture) part dans
   une **liste de demandes** reprise à la session Claude Code suivante.

## 3. Décisions proposées

- **D34 — Stockage.** Nouvelle table `thermique_etudes` (une étude par planche) : analyse (locaux, objets),
  manifeste, éléments d'enveloppe, catalogue, fiches calculées, état de chaque local (`a_verifier` / `valide`),
  demandes, dates. Colonnes JSON, comme `calibration_json` et `composition_json` aujourd'hui.
- **D35 — Import.** Bouton « Importer une étude » sur la planche : dépôt du fichier `etude-<niveau>.json` produit par
  la commande. Pas d'envoi automatique depuis le poste (il faudrait des identifiants dans la commande).
- **D36 — Écran.** À gauche, le plan (visionneuse en tuiles existante) avec les locaux en surimpression ; le local
  courant est mis en avant, ses côtés sont colorés par adjacence (extérieur, local non chauffé, local chauffé, vide)
  et ses éléments d'enveloppe sont affichés. À droite, la fiche du local : nom, nature, surface, côtés (adjacence,
  épaisseur, orientation, déperditif), éléments d'enveloppe (paroi, menuiserie, poteau : composant, longueur,
  inclus ou exclu), liaisons (angles, refends). En bas : liste des locaux avec leur état.
- **D37 — Modifications possibles (première version).** Contour (déplacer, ajouter ou supprimer un sommet), nom,
  nature, adjacence forcée d'un côté, rattachement d'un élément à un autre local, exclusion d'un élément,
  changement de composant (lien vers la bibliothèque du projet).
- **D38 — « Remodéliser ».** Le serveur rejoue le rattachement des éléments et le calcul des fiches **pour tout le
  niveau** (quelques secondes au plus), puis l'écran montre ce qui a changé : dans le local courant, et chez les
  **voisins touchés**. Votre remarque : modifier un contour peut ajouter ou retirer des éléments déperditifs chez un
  voisin. Rien n'est enregistré à ce stade.
- **D39 — « Enregistrer et suivant ».** Enregistre l'état remodélisé, passe le local en `valide`, garde une trace
  (qui, quand, quoi) et ouvre le local suivant non validé. Un local validé dont un voisin change repasse en
  `a_verifier`, avec le motif.
- **D40 — Hors de portée de la première version.** Le recalage automatique des contours sur l'image, le découpage
  d'un grand local en zones (le Pôle multimédia : on émet une demande), les valeurs de ψ et les hauteurs (après les
  coupes).
- **D41 — Préalable.** Ajouter `shapely` aux dépendances du serveur (voir § 1), avant tout le reste.

## 4. Questions

- **Q1** — Import par dépôt d'un fichier d'étude (D35) : cela vous convient ?
- **Q2** — Modifications de la première version (D37) : suffisantes, ou faut-il aussi pouvoir **dessiner** un local
  manquant, en **fusionner** deux ou en **couper** un ?
- **Q3** — Historique : suffit-il de garder le dernier état et la trace « qui, quand, quoi » ? Ou faut-il pouvoir
  revenir à une version antérieure d'un local ?
- **Q4** — Ponts thermiques : en première version, afficher leur type et leur longueur seulement (les ψ viendront
  avec la bibliothèque) ?
- **Q5** — Hauteurs : sans les coupes, mettre une hauteur sous plafond par défaut (par exemple 2,50 m), modifiable
  par local, pour avoir des surfaces de parois ? Ou n'afficher que les longueurs ?
- **Q6** — Ordre du « suivant » : ordre de lecture du plan, locaux chauffés d'abord, ou locaux en alerte d'abord ?
