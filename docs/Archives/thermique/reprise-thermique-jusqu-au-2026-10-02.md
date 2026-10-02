# Ancienne section « REPRENDRE ICI » (outil thermique), jusqu'au 2026-10-02

> Archivée au rangement du 2026-10-02. Historique seulement : la reprise se fait depuis `docs/thermique/README.md`.
> Les chemins cités ont été mis à jour vers `docs/thermique/reference/`, `en-service/` ou `docs/Archives/thermique/`.

## Contenu archivé

**🧭 GUIDE DE RÉFÉRENCE (2026-10-02, À GARDER PRÉCIEUSEMENT) : `docs/thermique/reference/guide-etude-thermique-14-etapes.md`**
— voulu par le thermicien comme guide pour **reprendre toute la plateforme** : objectif **assistant IA à la
réalisation d'études thermiques, en local avec Claude** (14 étapes, une étape + un plan par mission, conventions
écrites, « hypothèses et doutes », validation à chaque étape). Correspondance avec l'existant et ordre de reprise :
`docs/thermique/reference/refondation-assistant-ia-local-decisions.md` (D275–D280, 5 questions). Méthode d'analyse :
`docs/thermique/reference/analyse-par-missions-decisions.md` (D271–D274).

Ancienne boussole, remplacée par le guide : `docs/Archives/thermique/bilan-et-plan-2026-10-02.md` — bilan forces/faiblesses et plan
d'objectifs dans l'ordre : (1) R+1 parfait [lot B murs : 3 questions ouvertes dans
`mur-ligne-de-metre-decisions.md` ; coupes et élévations ; recette souris], (2) interface allégée étape par
étape + nettoyage des fonctions retirées, (3) bibliothèques fiables, (4) autres niveaux par report sans IA,
(5) livrable déperditions. Tout lot doit servir un de ces objectifs.

**AUDIT DU WORKFLOW (2026-10-02, fin)** : `docs/thermique/en-service/audit-workflow-2026-10-02.md` — 3 failles (relais et
mode automatique sur Opus 4.7 par l'alias `opus` ; coordonnées de l'IA ; pas de livrable), faiblesses par étape,
10 priorités. Murs en prod le même jour : suppression instantanée, indéterminés, poignées, créer un mur, ajouter un
point (D247, D249, D250, D252, D254). Essai R+2 en session cloud en cours (branche publique `essai/r2-cloud`).

**2026-10-02 (suite) — EN ATTENTE DE RÉPONSES** : `docs/Archives/thermique/murs-traces-decisions.md` (D248–D253 : mur =
ligne libre tracée, poignées, clic droit « Créer un mur », gestes enregistrés aussitôt, « Repartir de zéro » du
R+1 avec sauvegarde ; 5 questions ; remplace le lot B). Bilan de la détection :
`docs/thermique/en-service/detection-composants-bilan-2026-10-02.md` (l'IA reconnaît, ne mesure pas).

**CAP DÉCIDÉ LE 2026-10-01 : consolider le R+1 jusqu'à ce qu'il soit parfait, AVANT tout autre niveau.**
- La passe globale automatique (`run_etude_niveau.py --mode cli`) est **insuffisante** : essai A/B sur le R+2,
  23 / 25 / 36 objets contre 130 au R+1 (le R+1 avait été fait en session interactive, mode « attente »). La
  façon de passer les consignes à l'agent n'est pas en cause. **Ne relancer aucun niveau avec elle.**
- Ensuite : **reporter le relevé du R+1 sur les autres niveaux** par le calage, sans IA
  (`docs/thermique/en-service/report-entre-niveaux-decisions.md`, D233–D237, principe validé, 4 questions à confirmer
  au moment de coder) ; puis détection « par l'exemple » des menuiseries répétées ; l'IA seulement pour des
  lectures ciblées.
- Étude R+2 automatique produite (`Etudes-thermique/projet1/R2/etude-R2.json`, 21 incohérences) : à ne pas
  prendre pour base ; elle servira au mieux pour son contour de façade (99 tronçons, 154,6 m).

**Chiffres de référence du R+1** (`banc.db` du bloc-notes, instantané antérieur à la prod) : 227 éléments,
**229 côtés** (et non plus 222 : les côtés contre les 2 terrasses sont distingués depuis F), **170,12 m
déperditifs**, 289 formes, 77 liaisons. Tout lot qui ne touche pas au calcul doit les laisser intacts.

**2026-10-01 (nuit, suite) — coupes et élévations sans IA ✅ EN PROD** (D230–D232,
`docs/thermique/en-service/vues-sans-ia-decisions.md`). « Analyser » ne met plus en file que les niveaux ; les vues se
créent à la main (« Ajouter une vue ») ; les menuiseries mesurées sont dessinées sur leur vue. Catalogue repris
d'un autre niveau : vignettes non dessinées (arrêt du R+2 corrigé). **R+2 du projet 1 en cours d'analyse sur le
poste** (`Etudes-thermique/projet1/R2`), à importer par l'utilisateur.

**2026-10-01 (nuit) — étapes Parois et Menuiseries séparées ✅ EN PROD** (D227–D229,
`docs/thermique/en-service/etapes-parois-menuiseries-decisions.md`). Six étapes ; chaque étape n'épaissit et ne laisse
attraper que sa famille ; étape Menuiseries : compteur « sans modèle », cotes, bibliothèque, fenêtre prête à
mesurer ; fiche d'une menuiserie allégée (relevé replié), « Affecter aussi à » retiré de l'écran.

**2026-10-01 (soir) — menuiseries réunies et exposition ✅ EN PROD** (D223–D225,
`docs/thermique/en-service/menuiseries-reunies-exposition-decisions.md`). Morceaux d'une menuiserie réunis **dans le
relevé** à chaque recalcul (même tronçon, même composant et modèle, ≤ 6 cm, indéterminé absorbé) ; une étude
plus ancienne est recalculée une fois à sa lecture (`menuiseries_reunies`). Jonction de tronçons : une baie à
l'écran (une cote, un clic). Exposition (8 secteurs + azimut) écrite à chaque recalcul, donc à chaque pose du nord.

**2026-10-01 (fin) — modèles de menuiserie ✅ EN PROD** (D218–D222, `docs/thermique/en-service/modeles-menuiseries-decisions.md`).
Mesure en coupe/élévation → modèle nommé + capture PNG → posé en cliquant les menuiseries du plan (ou « même
largeur ± 2 cm ») ; la baie hérite largeur, hauteur et surface du modèle ; cote affichée sur le plan à l'étape 4 ;
bibliothèque des modèles du projet. Hauteur : « Appliquer à tous les locaux du niveau ». Reporté : couper une baie
réunie à tort ; relevé cadre/vitrage par un agent sur les captures.

**2026-10-01 (suite) — parcours à 5 étapes et fenêtre « Coupes et élévations » ✅ EN PROD** (D213–D217,
`docs/thermique/en-service/coupes-elevations-fenetre-decisions.md`). Étape 3 « Locaux et hauteur » (hauteur obligatoire
pour valider) ; plus de traits de coupe sur le plan ; la fenêtre choisit la vue et mesure hauteur ou
menuiserie ; hauteur posée sur le local ouvert, les locaux cliqués ou tous ceux sans hauteur ; menuiserie
« Affecter aussi à » d'autres pièces (parts égales). **À éprouver par le thermicien sur le R+1.**

**2026-10-01 — coupes et façades : le thermicien d'abord, l'IA ensuite ✅ EN PROD** (D206–D212,
`docs/thermique/en-service/vues-manuelles-decisions.md`). Vue renommable et reclassable ; haut choisi tel que vu à
l'écran ; fenêtre de vue ouverte à l'endroit ; « Placer les coupes » trace un trait à la main sur le plan ;
mesures dessinées en direct, hauteur vérifiée puis posée sur les locaux cliqués ; mode sombre lisible ;
« Faire lire par l'IA » vue par vue (plus de relecture automatique). **À éprouver par le thermicien sur
PC10/PC11 et le R+1.** Niveaux SS1, RDC, R2, R3, toiture du projet 1 : analyse toujours à relancer (sur accord).

**2026-09-30 — calage des niveaux refait « comme Aligner d'AutoCAD » ✅ EN PROD (`a601cfe0`), validé par
l'utilisateur** (`thermique/en-service/calage-autocad-decisions.md`, D201–D202) : point de base → rotation (aimant 1°,
« La rotation est déjà bonne ») → longueur avec ses propres points ; écart à l'échelle déclarée affiché. Les
cases de superposition nomment le voisin. Découverte : l'échelle d'une planche est **arrondie à l'échelle
usuelle si l'écart < 1 %** (`standard_scale_near`) → le calage le révèle, et les métrés en héritent (question
ouverte). **Règle utilisateur depuis ce jour : pousser sur `main` dès chaque modification testée.**

**Fichiers de décisions en cours (lire celui du lot repris) :**
- `thermique/en-service/superposition-niveaux-decisions.md` — 🔥 chantier prioritaire. D168–D173. **S2 calage et S3
  calque fantôme FAITS et en prod** (cases « Voir niveau inférieur / supérieur », calage 4 clics).
  Reste **S4** (règle des quatre quarts, `metre-plans-decisions.md` §3 : liaisons plancher / mur déduites,
  créées d'office, jugées dans la passe) et **S5** (D170, D171 : un agent repère sur le plan les traits
  de coupe et repères de façade, cliquables pour ouvrir la vue ; pièces de la coupe rattachées aux locaux
  du plan ; **hauteur sous plafond lue par local** ; hauteur des menuiseries lue en élévation).
  ⚠️ S4 ne se vérifie qu'avec **deux niveaux étudiés et calés** : seul le R+1 l'est.
  **✅ EN PRODUCTION `a82c3af0` (2026-09-29, migration 0088, bundle `thermique-DSkqJM3Q.js`, route `/vues` 401)** :
  tout S5 ci-dessous. Jamais recetté à la souris : la recette par l'utilisateur est la prochaine étape.
  **S5 (2026-09-29)** : `thermique/en-service/coupes-elevations-S5-decisions.md`
  (Q34–Q41 répondues → D178–D185 ; règles de rattachement D186–D189). Vérité terrain des deux projets :
  `thermique/en-service/verite-terrain-coupes.md` + `.json`. Le R+1 étudié est celui du **projet 1** (Frontignan, PC04,
  1/100). **Fait** : rattachement coupe → locaux (`thermique_coupes.py`, coupe A réelle 8/8), rangement des
  lectures + route `GET /sheets/{id}/hauteurs` + hauteur saisie par `modifier` (`thermique_lecture_coupes.py`,
  **migration 0088**), hauteur dans la fiche du local (écran), agent `thermicien-coupe` + script
  `run_lecture_coupes.py` (images quadrillées en points PDF, `--reponses` pour rejouer) + relais par type de
  travail (un ancien relais ne reçoit que des niveaux). **Essai réel de l'agent : 0/13** (positions fines et
  plafond fini ratés ; vues et numéros de pièces bien lus) → Q42 tranchée en conversation : **D190** le trait se
  déduit de la coupe (balayage du plan, numéros de pièces ; coupe A 8/8, C 3/3 sur vérité terrain), **D191**
  la hauteur se confirme par deux clics dans la coupe (corrige tout l'étage). Faits : déduction + cache du
  trait (préparé en tâche de fond à la lecture des coupes), routes `POST/DELETE /vues/{id}/hauteur`,
  `GET /projects/{id}/vues`, fenêtre flottante de la coupe (`FenetreCoupe.tsx`, bouton « Voir la coupe » dans
  la fiche). **Tout est en commits locaux, rien poussé, jamais éprouvé à la souris.** Reste : traits
  cliquables sur le plan (S5a/S5b), traits à décrochés ou en biais, élévations (S5e).
  **Suite (même jour)** : D171 traits cliquables (case « Voir les coupes ») et D192 repli par les noms faits ;
  **S5e fait** (`thermique/en-service/elevations-S5e-decisions.md`, D193–D200) : baies (58 → 49 au R+1, 8 morceaux à
  vérifier), hauteur par composant mesurée par deux coins sur la façade, « Voir la façade » depuis la fiche
  d'une menuiserie. Reste : trait de façade sur le plan (attend le nord, D198), surfaces (murs, baies) dans le
  calcul.
- `Archives/thermique/retours-menuiseries-2026-09-28-decisions.md` — M1, M2 (morceaux → élément entier), M3 **faits**.
  Réponses Q30–Q33 → **D174** fusion d'office de 2 menuiseries contiguës de même composant ; **D175**
  menuiserie dessinée = composant le plus employé ; **D176** identiques = même composant, largeur ± 1 cm ;
  **D177** hauteur lue en élévation (S5). **À faire : M4** (clic droit menuiserie : « Supprimer » = écarter ;
  « Dessiner une menuiserie ici » = 2 clics projetés sur le tronçon, mur coupé de part et d'autre) et
  **M5** (repère composant · largeur, hauteur à lire en élévation).
- `thermique/en-service/retours-ponts-2026-09-28-decisions.md` — P5 (ajout de pont instantané, D164) **fait**.
  Réponses Q19–Q23 enregistrées. **À faire** : **P2** (à l'étape des ponts, clic dans un local → seuls
  ses ponts, partagés marqués ½ ; la passe reste sur tout le niveau, Q21 b), **P3** (D163 : 50/50 des
  angles à la jonction de deux pièces + « partagé avec… » manuel, Q22 a), **P6/D165** (liaisons linéiques
  dessinées le long du côté et jugées dans la passe = F seconde partie), **P4** (clic droit : les 5 ponts
  types les plus employés du niveau puis « Autre… », Q23 a), **P1** (croquis de la norme découpés dans le
  PDF, Q19 a, + vignette zoomée du plan, Q20 a).
- `Archives/thermique/retours-usage-2026-09-28-decisions.md` — A, B, C, D, E, F (1re partie), G1 faits (D155–D162).
  Reste **G2** (dessiner l'emprise des angles), **G3** (déplacer les bornes d'un élément, voisin qui suit,
  Q17 a), **G4** (agent de liaison, sur demande pour le niveau, Q18 b).

**Ordre convenu par l'utilisateur (D172, Q29 a)** : superposition d'abord (S2, S3 faits) ; les autres
lots ensuite. Proposé à l'utilisateur en fin de session, sans réponse : (1) petits lots décidés (M2 fusion
d'office, M4, P2+P3, P4, P1), (2) S4, (3) S5. **Lui demander par quoi reprendre.**

**Normes** : `C:\Users\pa.borja\Documents\Po2\Thermique\NORMES` (9 PDF, texte extractible par
`pdfplumber` ; tableaux en image → rendre les pages par `pypdfium2` et les lire). Catalogue ISO 14683
C.2 transcrit : `saas/backend/app/data/thermique_ponts_iso14683.json`. ⚠️ PDF sous **licence CSTB
nominative** : à vérifier avant ouverture de l'outil à d'autres bureaux d'études. Demander à l'utilisateur
l'annexe nationale française de la NF EN 12831-1 s'il l'a.

**Pièges de cette session** : un `python -c` lancé depuis la racine du dépôt avec `banc.db` en chemin
relatif **crée un `banc.db` vide dans le dépôt** — toujours passer par un script du bloc-notes ;
`[IO.File]` en PowerShell résout les chemins relatifs depuis le dossier du processus, pas `cd` ;
`Set-Content -Encoding utf8` ajoute un BOM (utiliser `UTF8Encoding $false`). Vérifier un déploiement sur le
bundle **servi** (`/assets/thermique-*.js`) et une route par son code HTTP sans session (401 = existe,
404 = inconnue, 502 = serveur en redémarrage).

**Règles permanentes** : rien sur GitHub sans « pousse » explicite ; français ; « ce que j'ai fait, en
clair » ; fichier de décisions avant de coder ; ne jamais saisir d'identifiant (donc pas de recette à la
souris) ; ne pas modifier `.claude/agents/thermicien-plan.md` ; tests ciblés seulement ; `git commit --
<chemins>` explicites.

