# Coupes et élévations : une fenêtre, pas de traits (D213 à D217)

Date : 2026-10-01. Suite de `vues-manuelles-decisions.md` (D206–D212), après le test du thermicien.

## Constat

Placer les traits de coupe et d'élévation sur le plan (D209) fonctionne, mais c'est une corvée : le
thermicien sait d'un coup d'œil quelle coupe ou quelle élévation regarder. Ce qui compte, c'est d'ouvrir
la bonne vue depuis le plan pour **mesurer une hauteur d'étage** ou **une menuiserie**.

## Existant vérifié

- `parcours.ts` : 6 étapes sur un plan (planche, analyse, locaux, parois et menuiseries, ponts, hauteurs
  « à venir »). La validation d'un local (`ValidationLocal`) n'exige pas de hauteur.
- `FenetreCoupe.tsx` : une vue à la fois, ouverte par un trait du plan ou par la fiche (« Voir la coupe »).
- Menuiseries (`thermique_menuiseries.py`) : le plan donne position, type et largeur de chaque baie ;
  **jamais la hauteur**, qui ne vient que d'une mesure en coupe ou en élévation (par type, D200, ou par baie).
  `confirmer` accepte une mesure sur n'importe quelle vue, coupe comprise.
- Rattachement d'une menuiserie à une pièce : géométrique (`decouper_par_piece`), une pièce par morceau.

## Décisions

- **D213 — Cinq étapes.** Planche, Analyse, **Locaux et hauteur**, Parois et menuiseries, Ponts. L'étape
  « Hauteurs (coupes) » disparaît. Un local (hors espace extérieur) ne se valide **qu'avec une hauteur**
  (lue, mesurée ou saisie) ; l'étape compte les locaux validés et les hauteurs manquantes.
- **D214 — Une fenêtre « Coupes et élévations ».** Un bouton du plan l'ouvre ; une liste choisit la vue
  parmi toutes celles du projet (coupes, élévations). Les deux mesures y sont toujours possibles ; l'étape
  met en avant la sienne (hauteur à l'étape 3, menuiserie à l'étape 4). La fenêtre garde sa place et sa
  vue d'une ouverture à l'autre. La fiche d'un local propose « Mesurer la hauteur » (fenêtre prête à
  mesurer) ; la fiche d'une baie, « Mesurer sa hauteur ».
- **D215 — Hauteur posée vite.** Mesurée depuis la fiche d'un local, la hauteur va d'abord à ce local ;
  puis on clique d'autres locaux, ou « Appliquer aux N locaux sans hauteur » en un seul enregistrement.
- **D216 — Plus de traits sur le plan.** La case « Voir les coupes et façades » et « Placer les coupes »
  sont retirées de l'écran. Le serveur garde traits relevés, tracés et déduits (rien n'est perdu).
- **D217 — « Affecter aussi à ».** Une menuiserie peut être partagée avec d'autres pièces cochées
  (champ corrigeable `pieces_en_plus`). Sa longueur est **répartie à parts égales** entre sa pièce et les
  pièces cochées : la baie n'est jamais comptée deux fois. Parts égales plutôt qu'au prorata du mur : simple
  à vérifier, et une répartition fine se fait en corrigeant les bornes. Les pièces sont désignées par leur
  nom : renommer une pièce demande de refaire l'affectation.

## Questions

Aucune ouverte (réponses du 2026-10-01 : hauteur obligatoire ; « appliquer aux autres » oui ; bouton sur le
plan et dans la fiche).
