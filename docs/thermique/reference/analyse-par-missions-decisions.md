# Analyse des plans par missions courtes et outillées (D271 à D274, proposées)

Date : 2026-10-02. Déclencheur : deux demandes faites par le thermicien à Claude (Opus 5.5, effort moyen) dans
son navigateur, sur le plan du R+1 traité comme une image : (1) « les parois extérieures au nu intérieur »,
(2) « les éléments pouvant générer une liaison thermique verticale, par catégorie, le niveau du dessous étant
chauffé ». Résultat jugé « bluffant » par le thermicien, obtenu en peu de temps. Fichier rendu (coordonnées +
code) gardé hors du dépôt public : `Etudes-thermique/projet1/R1/claude-navigateur/`.

## Sa méthode (résumée)

Rendu raster à 200 dpi (pixels seuls) ; **code d'analyse d'image exécuté par Claude** (seuillage, ouverture
morphologique, contours des blocs de murs, profils de pixels pour les vitrages) ; **lecture visuelle** d'une
trentaine de zooms choisis par lui pour trancher intérieur/extérieur et le côté du nu intérieur ; enchaînement
de ~100 sommets typés mur / vitré / liaison ; liaisons verticales en 7 catégories (A–D calculées sur le contour,
E–G placées par lecture). Limites qu'il annonce : arbitrages d'interprétation, enchaînement non reproductible
tel quel, contrôle visuel partiel.

## Pourquoi c'est mieux que notre chaîne

| | Notre chaîne (R+1, R+2) | Missions dans le navigateur |
|---|---|---|
| Outils de l'agent | lecture d'images seulement : positions estimées à l'œil | **il exécute du code** : positions calculées |
| Où regarder | ordre fixe : guide calculé d'avance, 72 bandes de 5 m | **il choisit** ses zooms |
| Question | tout en une passe, JSON énorme | **une mission courte** à la fois |
| Modèle | Opus 5 (R+1), Opus 4.7 par erreur (R+2) | Opus 5.5 |

## Mesure sur le R+1 (2026-10-02, copie de l'étude du 22/09)

Repère : leurs pixels (200 dpi, page non tournée) → notre raster (300 dpi, tourné de 90°) : (x, y) → (1,5·y,
W − 1,5·x). Image de superposition : `comparaison-R1-contours.png` (même dossier).

- Leur contour : **141,79 m** (mur 61,69 m, vitré 79,41 m, liaison 0,69 m). Nos parois extérieures : 126,72 m
  (plus 39,51 m sur local non chauffé ou vide, qu'on ne leur avait pas demandés).
- Écart de nos parois extérieures à leur contour : **médiane 2,1 cm** ; 58 % de la longueur à moins de 3 cm,
  64 % à moins de 10 cm, 81 % à moins de 30 cm.
- Opaque / vitré : **97 % d'accord** sur la longueur comparée (99,53 m ; désaccords 1,19 m et 1,94 m).
- Écarts, à trancher sur l'image :
  - **façade sud en mur-rideau** (6.1.3 à 6.1.5, 4.4…) : 30 cm d'écart. Ils suivent la ligne du vitrage, nos
    locaux s'arrêtent à la face intérieure des poteaux. C'est une question de convention (question 1) ;
  - **6.1.3 équipement, mur est** : nos parois sont à 59 cm à l'intérieur du mur. **Erreur de notre contour** ;
  - **traits verts parasites** en diagonale dans 4.3 et 4.2 : côtés de nos contours classés extérieurs à tort.
    **Erreur de notre côté** ;
  - 29,9 m de leur contour n'ont aucune paroi de notre côté à moins de 30 cm (terrasses, abords de la terrasse du
    personnel, 6.1.1) : zones où nos contours n'atteignent pas la façade.

**Conclusion** : pour l'enveloppe extérieure, leur contour est au moins aussi juste que le nôtre là où les deux
existent, et plus complet ailleurs. Le nôtre reste seul à couvrir les locaux non chauffés et les vides.

## Décisions proposées

- **D271 — Missions courtes et outillées.** L'analyse d'un niveau se fait par missions, une question à la fois :
  (M1) contour au nu intérieur typé mur / vitré / liaison ; (M2) liaisons verticales par catégorie ; puis plus
  tard (M3) locaux non chauffés, gaines et vides ; (M4) menuiseries par type. L'agent dispose d'une **boîte à
  outils d'analyse d'image écrite une fois** (rendu, blocs de murs, profils, zooms gradués, export dans le format
  ci-dessous), reprise du code fourni, sans OpenCV si le poste ne l'a pas (numpy, scipy, Pillow suffisent). Il
  lit les zooms pour trancher. Jamais les vecteurs du PDF.
- **D272 — Un format d'échange unique** : repère (dpi, rotation, taille de page), segments typés, points
  catégorisés. Exactement celui du fichier rendu.
- **D273 — Import comme propositions**, jamais en silence :
  - M1 → la **façade de référence** du niveau. Chaque paroi d'un local est comparée à elle : vitrée ou opaque selon
    la façade (remplace la règle D263 tirée du relevé), et une paroi à plus de 15 cm de la façade est signalée
    (« contour à recaler » : cas 6.1.3). Les côtés extérieurs sans façade proche sont signalés comme suspects
    (traits parasites).
  - M2 → **ponts** de l'étape Ponts, avec leur catégorie et leur type NF EN ISO 14683 proposé (question 4).
- **D274 — Où ça tourne.** En session (navigateur claude.ai, session cloud ou session sur le poste), avec un fichier
  de consigne par mission et la boîte à outils du dépôt. Un **nouvel agent** autorisé à exécuter le code d'analyse
  d'image. Les agents existants ne sont pas modifiés. Modèle annoncé et vérifié (règle du thermicien).

## Questions

1. **Mur-rideau (façade sud)** : le nu intérieur est-il la ligne du vitrage (leur choix) ou la face intérieure des
   poteaux (nos locaux) ?
2. **Nouvel agent qui exécute du code d'analyse d'image** : d'accord ?
3. **Où lancer les missions** : dans votre navigateur comme aujourd'hui (simple, vous voyez tout), en session cloud,
   ou ici ?
4. **Catégories de liaisons → NF EN ISO 14683** : A et B angles (C), C jonction mur/menuiserie (W), D angle
   menuiserie/menuiserie (à modéliser), E refend/noyau (IW), F cloison/façade (IW ou négligée si cloison
   légère ?), G poteau (P). Ça vous va ?
