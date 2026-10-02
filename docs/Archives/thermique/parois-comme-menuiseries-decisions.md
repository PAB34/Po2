# Parois : fusion, copie de composition, retracé d'un mur (D238 à D241)

Date : 2026-10-01. Retour du thermicien sur le R+1 : les parois sortent du relevé IA en morceaux, parfois
superposés et bizarres près des angles (capture : pan de façade en biais, plusieurs formes qui se chevauchent).
Il veut le même confort que pour les menuiseries.

## Existant vérifié

- Relevé (`releve_brut.elements`) : un élément = un morceau de **tronçon** du contour, avec type, composant,
  couches, nus (épaisseurs). Les angles et abouts de refend sont des éléments à part : ce sont eux, les **ponts
  thermiques**, et ils marquent déjà la discontinuité à chaque changement de direction (fin de tronçon).
- Catalogue des composants (P1, P2…) : composition (couches) et règle, commun aux niveaux.
- Corriger le composant « partout » existe (`element_corriger`, portée `partout`).
- Menuiseries : réunion des morceaux à 6 cm dans le relevé (D223) ; modèle posé en cliquant (D220).

## Décisions proposées

- **D238 — Fusion des parois à 6 cm.** Comme les menuiseries : sur un même tronçon, deux parois de même
  composant, séparées de 6 cm au plus, sans rien entre elles qu'un « indéterminé », deviennent une seule paroi.
- **D239 — Copier la composition d'une paroi (pinceau).** On choisit la paroi la plus fiable (bonne
  composition, bonnes épaisseurs), « Copier sa composition », puis on clique les autres parois : chacune prend
  son composant, ses couches et ses nus. Raccourci : « Appliquer à toutes les parois de ce composant ».
- **D240 — Retracer un mur.** Avec une composition copiée : un clic au début, un clic à la fin, le long de la
  façade (sur un ou plusieurs tronçons). Tout ce qui est entre les deux — parois, morceaux bizarres,
  indéterminés qui se chevauchent — est remplacé par **une paroi propre par tronçon**, de cette composition.
  Les angles et abouts (ponts thermiques) restent en place : la discontinuité à chaque angle est gardée. Les
  menuiseries de la portion sont conservées (le mur s'arrête au tableau).
- **D241 — Les morceaux bizarres** (capture) se traitent par D240 : on retrace le pan de mur, les morceaux
  remplacés sont écartés avec le motif « remplacé par le mur retracé » (visibles, réactivables).

## Ordre proposé

D238 (rapide, aucun geste) → D239 (pinceau) → D240 (retracer, qui règle aussi D241).

## Résultat (2026-10-01, en prod)

- D238 : `reunir_menuiseries` réunit aussi les parois (`TYPES_REUNIS`).
- D239 : `couches` devient corrigeable (au moins une couche, épaisseurs 0–200 cm) ; fiche d'une paroi :
  composition lisible + « Copier sa composition (pinceau) » à l'étape Parois ; bandeau : clic sur une paroi,
  « Appliquer aux N parois Px », « Retracer un mur », « Terminé ».
- D240 : opération `paroi_retracer` (début, fin le long de la façade, composition) ; les clics sont projetés
  sur la façade par l'écran avec la règle du serveur (`projeterSurTroncon`).
- Tests : 3 serveur (fusion des parois, couches copiées, mur retracé), 3 écran (`parois.test.ts`).
