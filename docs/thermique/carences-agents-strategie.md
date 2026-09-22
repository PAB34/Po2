---
read_policy: lire avant de faire évoluer un agent ou la chaîne ; complète chaine-analyse-plan-raster.md
---

# Carences restantes des agents et stratégie pour les couvrir

Date : 2026-09-22. Base : l'étude complète du R+1 (médiathèque de Frontignan) et des mesures faites sur ses
résultats (relevé de 208 intervalles, 72 tronçons, 171 m de périmètre ; passe globale de 130 objets).

## 1. Ce qui marche déjà (à préserver)

- Reconnaissance des composants : P1 reconnu 29 fois sous le même nom, catalogue stable (14 → 23), éléments
  extérieurs écartés (claustra, brise-soleil, escalier, potelets).
- Contrôle par l'image : P1 confirmé à 96 %, baies M1 et M4 à 100 %, 87 % de l'isolant visible compté.
- Nus : **écart médian de 2,5 cm** avec les traits du plan (199 mesures).
- Angles : le type donné par l'agent (sortant, rentrant) est d'accord avec la géométrie dans 11 cas sur 12.

## 2. Carences mesurées

| # | Carence | Mesure sur le R+1 | Effet sur l'étude | Cause principale |
|---|---|---|---|---|
| C1 | Pas de vérité terrain : aucun score ne dit si un changement améliore ou dégrade | — | on ne peut ni prouver un progrès, ni éviter une régression | aucune référence validée par le thermicien |
| C2 | Nus parfois très faux | 10 % des lectures à plus de **11 cm** (nu extérieur) et **21 cm** (nu intérieur) | longueurs intérieures, rattachement aux pièces, raccords d'angles refusés | l'agent estime à l'œil sur la règle ; rien ne recale sa lecture sur le trait réel |
| C3 | Position du cadre des baies incohérente pour un même composant | M3 : de −14 à +90 cm du nu intérieur ; M5 : de −28 à +4 cm | position de la menuiserie dans le mur (ψ d'appui, tableau), largeur des baies de retour | baies presque perpendiculaires à la bande ; lecture en abscisse au lieu de la profondeur |
| C4 | Guide de l'enveloppe fautif par endroits | claustra suivi (T39–T45, T56–T57), dents de scie coupées (T34, T67, T68), boucle T70–T71 | le mur réel sort de la bande lue : l'agent ne peut pas le relever (P4 confirmé à 74 % seulement) | guide calculé sur l'image, sans contrôle de ce qu'il longe |
| C5 | Pièces de la passe globale qui n'atteignent pas la façade | rattachements « à la pièce la plus proche » sur ~30 m, jusqu'à 1,8 m de distance | pièce d'un vitrage parfois fausse | contours de pièces approximatifs, dessinés par l'agent |
| C6 | Circulations et espaces ouverts non identifiés comme locaux | circulations absentes ; Pôle multimédia d'un seul tenant (65 m de façade) | règle D23 (tout local en façade est déperditif) non appliquée ; zonage grossier | consigne de la passe globale qui ne demande pas les circulations ni les sous-espaces |
| C7 | Trop de points « à vérifier », confiances non étalonnées | **68 intervalles sur 208 (33 %)** à vérifier ; confiance moyenne 0,66 quel que soit le type | charge de relecture élevée ; les vrais doutes sont noyés | la confiance est une impression de l'agent, jamais comparée au résultat réel |
| C8 | Ponts thermiques particuliers non caractérisés | 5 angles refusés ; liaisons plancher jamais relevées (invisibles en plan) | ψ à chercher à la main | pas d'outil de fiche ; hors du champ d'un plan |
| C9 | Pas de hauteurs | aucune | pas de surfaces, pas de ψ plancher localisé | les plans ne les portent pas : il faut les coupes |
| C10 | Refends et cloisons de la passe globale peu nombreux | 4 refends, 24 cloisons pour 22 pièces | découpage par pièce dépendant des abouts relevés par l'autre agent | passe globale à 150 dpi, tuiles larges |
| C11 | Transcription des réponses en mode session | ~30 à 60 Ko de JSON recopiés par lot | risque d'erreur de recopie, temps | l'agent ne peut que lire : il ne peut pas écrire sa réponse dans un fichier |

## 3. Principe directeur

**L'agent reconnaît, l'algorithme mesure, un relecteur regarde les écarts, la vérité terrain arbitre.**

- L'agent est fort pour reconnaître et nommer (motifs, composants, contexte) ; il est approximatif pour mesurer
  au centimètre. Les mesures doivent être recalées par l'algorithme sur les traits réels du plan.
- Un second regard ne doit porter que sur ce que les contrôles signalent (écarts image/relevé, raccords refusés,
  faible confiance) : c'est ciblé, donc rapide.
- Toute évolution d'un agent ou d'un algorithme est rejouée sur un banc d'essai et notée : on ne garde que ce qui
  améliore le score.

## 4. Stratégie, par ordre de priorité

### S1 — Vérité terrain et banc d'essai (couvre C1, prépare C7) — priorité 1

- Le thermicien corrige une fois le R+1 dans `/analyse` (objets de l'enveloppe par couche, pièces, baies) et
  valide le catalogue : c'est la référence.
- Un script de notation compare un résultat à la référence : part du linéaire bien classée par composant, écart
  des nus, largeurs de baies, pièces (recouvrement), ponts thermiques trouvés.
- Chaque changement de consigne ou d'algorithme est rejoué sur le R+1 (les réponses des agents sont conservées)
  et noté. Deuxième plan de référence dès que possible (autre projet, autre graphisme).

### S2 — L'algorithme mesure, l'agent choisit (couvre C2, C3) — priorité 2

- Recalage des nus : autour de la valeur lue, chercher sur la bande le trait réel le plus proche (bord de la masse
  grise ou noire) et retenir sa position ; garder la lecture de l'agent si aucun trait n'est net.
- Baies : mesurer largeur et position du cadre dans la direction réelle de la baie (y compris les baies de retour
  perpendiculaires), à partir des doubles traits du vitrage ; l'agent ne donne que le type et le composant.
- Effet attendu : le 90e centile des écarts des nus sous 5 cm ; cadres cohérents par composant ; moins de raccords
  refusés.

### S3 — Un guide qui longe vraiment le mur (couvre C4) — priorité 2

- Le guide suit la masse grise continue (voile) plutôt que le premier trait rencontré ; un élément exclu du
  catalogue (claustra, potelets) n'est plus longé.
- Bande adaptative : quand le contrôle voit la paroi sortir de la bande, le tronçon est rendu plus large et relu.
- Suppression des boucles parasites (côtés qui reviennent sur eux-mêmes).

### S4 — Un relecteur ciblé (couvre C2, C3, C7 résiduels) — priorité 3

- Nouvel agent `thermicien-relecteur` : il reçoit seulement les tronçons signalés (écart avec l'image, raccord
  refusé, confiance basse), rendus plus grands (600 dpi), avec une question précise (« le mur est-il isolé entre
  12,40 et 13,10 m ? où est le cadre de cette baie ? »), et rend une correction.
- Effet attendu : les points « à vérifier » transmis au thermicien passent de 33 % à quelques cas réellement
  douteux.

### S5 — Passe globale v2 : tous les locaux (couvre C5, C6, C10) — priorité 3

- Consigne complétée : circulations, halls, dégagements comme pièces ; sous-espaces d'un espace ouvert proposés
  (avec « à confirmer ») à partir des libellés et du mobilier.
- Contours de pièces recalés par l'algorithme sur le nu intérieur des murs (plus de repli « pièce la plus
  proche »).
- Tuiles plus fines (ou 300 dpi) pour les refends et cloisons.

### S6 — Étalonnage des confiances (couvre C7) — après S1

- Comparer, sur le banc d'essai, la confiance annoncée et le résultat réel, par type d'élément ; en déduire un
  seuil de relecture par type. Les consignes des agents sont ajustées en conséquence.

### S7 — Ponts thermiques particuliers (couvre C8) — lot A5

- Chaque changement de direction mesuré ; part géométrique ψi − ψe ≈ U·2·e·tan(θ/2) ; jonctions regroupées
  quand elles sont à moins de dmin = max(1 m ; 3 × épaisseur) (ISO 10211).
- Fiche par pont thermique particulier (image, compositions, angle, arrêt de l'isolant) prête pour ubakus ; le ψ
  calculé par le thermicien est enregistré dans le catalogue et réutilisé.

### S8 — Nouveaux agents pour ce que le plan ne dit pas (couvre C9) — prochain chantier

- `thermicien-coupe` : hauteurs sous plafond, planchers, toitures, liaisons plancher réelles, à partir des coupes.
- Plus tard : façades (hauteurs de baies, allèges), notice ou carnet de menuiseries s'ils sont fournis.

### S9 — Confort d'usage (couvre C11)

- Autoriser l'agent à écrire **uniquement** son fichier de réponse dans le dossier de l'étude (au lieu de lire
  seulement), pour supprimer la recopie ; ou lui faire rendre des lots plus petits.

## 5. Ordre proposé

1. S1 (banc d'essai) — sans lui, les étapes suivantes ne sont pas mesurables.
2. S2 et S3 (mesure et guide) — les gains les plus nets, purement algorithmiques, sans nouvel appel d'agent.
3. S5 et S4 (passe globale v2, relecteur) — évolutions des agents, notées sur le banc d'essai.
4. S7 (ponts thermiques particuliers), S6 (étalonnage), S9.
5. S8 (coupes) — nouveau chantier.

## 5 bis. Proposition de l'utilisateur (2026-09-22) : travailler pièce par pièce

Idée : pour chaque pièce, analyser tous ses composants de parois, ses ponts thermiques, ses métrés et les autres
informations utiles, plutôt que de tout déduire du tour de l'enveloppe.

Recommandation : **approche hybride, la pièce devient l'unité de travail finale** (c'est celle du calcul des
déperditions et des logiciels de thermique), en s'appuyant sur ce qui marche déjà.

- Le tour de l'enveloppe reste la couche de **reconnaissance** : la continuité et la répétition le long de la
  façade sont ce qui fait apprendre le catalogue (P1 reconnu 29 fois) et permet le contrôle par l'image.
- Nouvelle passe **pièce par pièce** (agent `thermicien-local`) : pour chaque pièce, une image recadrée sur la
  pièce et ses murs, avec sa **fiche local pré-remplie** (parois de façade déjà relevées, baies, ponts thermiques,
  catalogue). L'agent fait le tour de la pièce, **tous côtés compris** (façade, mur sur circulation, sur local non
  chauffé, sur autre pièce), donne pour chaque côté l'adjacence (extérieur, local non chauffé, local chauffé,
  circulation), confirme ou complète composition et baies, et liste les ponts thermiques de la pièce.
- Gains : unité de raisonnement du thermicien ; parois intérieures sur local non chauffé couvertes (C6, D23) ;
  petite image par appel, donc plus de précision ; validation par pièce plus naturelle que par tronçon.
- Conditions : des contours de pièces justes et toutes les circulations d'abord (S5) ; une même cloison vue de
  deux pièces doit rester cohérente (identifiants du catalogue, contrôle entre voisines) ; plus d'appels (petites
  pièces regroupées par zone).
- Ordre : S5 (tous les locaux, contours recalés) → fiche local générée depuis le relevé actuel → agent
  `thermicien-local` → validation par pièce. La référence par tronçon (S1) reste la vérité terrain des
  compositions et des baies, utile aux deux passes.

## 6. Questions à l'utilisateur

- Q1 — Êtes-vous d'accord pour corriger une fois le R+1 dans `/analyse` afin qu'il serve de référence (S1) ? Si
  oui, faut-il une page de validation plus simple que l'éditeur actuel (valider / corriger par tronçon) ?
- Q2 — Disposez-vous d'un deuxième jeu de plans (autre architecte) pour éviter d'ajuster l'outil à un seul
  graphisme ?
- Q3 — Les coupes du projet sont-elles disponibles (S8) ?
