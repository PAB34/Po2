# Reporter le relevé d'un niveau sur un autre (D233 à D237)

Date : 2026-10-01. Décision du thermicien : « point 1 » (partir du niveau déjà travaillé).

> **Statut : principe validé le 2026-10-01, EN ATTENTE.** Le thermicien veut d'abord **consolider le R+1
> jusqu'à ce qu'il soit parfait** ; le report vers les autres niveaux se codera ensuite, à partir de ce R+1.
> Les quatre questions ci-dessous restent à confirmer au moment de coder (les propositions n'ont pas été
> contredites). Aucun niveau n'est relancé avec la passe globale automatique d'ici là.

## Pourquoi

Essai du 2026-10-01 sur le R+2 (projet 1) : la passe globale de l'agent, lancée seule sur le plan entier,
rend 23, 25 ou 36 objets selon l'essai (R+1 : 130), quelle que soit la façon de lui passer ses consignes
(essai A/B). Le bon R+1 avait été produit en session interactive (mode « attente »). L'inventaire automatique
d'un plan entier est le maillon faible : irrégulier, coûteux, et toute la chaîne en hérite.

Les étages d'un même bâtiment partagent l'essentiel de leur façade, de leurs murs et de leurs menuiseries.
Le R+1 a été relu et corrigé par le thermicien ; le calage entre niveaux existe (D201–D203).

## Existant vérifié

- **Calage** (`thermique_calage.py`) : chaque planche porte une similitude de ses points PDF vers la planche de
  référence (`calage_json`). R+1 → R+2 = (R+2 → réf)⁻¹ ∘ (R+1 → réf), sans IA.
- **Étude d'un niveau** (`ThermiqueEtude.content_json`) : locaux et objets en coordonnées 0–1000 de la page
  rendue, convertis en points PDF par la transformation du raster (`convertir_contours`) ; relevé de
  l'enveloppe (`releve_brut.elements`) en abscisses le long des **tronçons** du contour du niveau
  (`enveloppe.manifeste.troncons` : origine, direction, normale extérieure en pixels de la page, `px_par_m`).
- Chaque élément porte : type, composant, couches, nus, `modele` (D220), confirmé/corrigé/écarté, exposition.
- Le catalogue des composants (compositions) est commun d'un niveau à l'autre (déjà repris par la chaîne).
- Étude R+2 produite le 2026-10-01 : contour de 99 tronçons (154,6 m), tiré du remplissage de l'image (fiable) ;
  locaux et relevé pauvres.

## Décisions proposées

- **D233 — Le contour du niveau cible reste le sien.** Le R+2 n'a pas la même emprise que le R+1 (terrasse,
  retraits) : on garde ses tronçons, et c'est le relevé du R+1 qui vient s'y poser.
- **D234 — Report du relevé, sans IA.** Chaque élément du R+1 (mur, menuiserie, poteau, garde-corps, angle,
  about) est ramené en points PDF du R+2 par le calage, puis posé sur le tronçon du R+2 qui passe à moins de
  **30 cm** de lui, dans le même sens. Il garde composant, couches, nus, modèle de menuiserie. Il est noté
  « repris du R+1 ». Un élément du R+1 sans tronçon en regard est écarté du report et listé.
- **D235 — Les différences sont dites.** Les longueurs de tronçon du R+2 sans élément repris sont listées
  « à relever » (avec leur longueur), et dessinées comme telles sur le plan : c'est là, et seulement là, que le
  thermicien (ou une lecture IA ciblée, sur demande) intervient.
- **D236 — Un geste sur la planche cible.** À l'étape « Analyse du plan » du R+2 : « Reprendre le relevé de… »
  (liste des niveaux calés qui ont une étude). Un aperçu dit ce qui sera repris, écarté et à relever, avant
  d'enregistrer ; l'enregistrement crée une nouvelle version de l'étude (rien n'est perdu).
- **D237 — Les locaux du niveau cible restent les siens**, à corriger à l'étape « Locaux et hauteur » (le
  plateau du R+2 n'est pas découpé comme celui du R+1).

## Questions

1. **État des éléments repris** : (a) ils gardent l'état du R+1 (confirmé reste confirmé) ; (b) ils repartent
   tous « à vérifier ». — proposé : (a), avec la mention « repris du R+1 », la vérification se faisant par les
   différences (D235).
2. **Tolérance de report** : 30 cm vous convient-il (épaisseur de mur près du nu extérieur) ?
3. **Locaux** : d'accord pour garder ceux du R+2 (D237), ou voulez-vous aussi reprendre les locaux du R+1 comme
   point de départ ?
4. **Sur les longueurs « à relever »** : (a) vous les relevez à la main ; (b) une lecture IA ciblée sur ces seuls
   morceaux, à votre demande. — proposé : (a) d'abord, (b) plus tard si utile.
