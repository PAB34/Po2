---
read_policy: lire avec guide-etude-thermique-14-etapes.md avant de proposer un lot ; remplace bilan-et-plan-2026-10-02.md comme boussole
---

# Refondation : un assistant IA d'étude thermique, en local avec Claude (D275 à D280, proposées)

Date : 2026-10-02. Décision du thermicien : le guide `guide-etude-thermique-14-etapes.md` est **la référence pour
reprendre toute la plateforme**. Objectif : **assistant IA à la réalisation d'études thermiques, dans un
environnement local avec Claude.** Déclencheur : les missions courtes faites dans le navigateur (contour au nu
intérieur à 2,1 cm de médiane, 97 % d'accord opaque/vitré ; `analyse-par-missions-decisions.md`).

## Les principes du guide, devenus règles de la plateforme

1. **Une étape + un plan principal à la fois**, les autres plans joints pour recouper.
2. **Chaque mission rappelle** le plan visé (nom stable), l'étape, les conventions validées.
3. **Chaque mission se termine par « hypothèses et doutes »**, que le thermicien corrige ou valide.
4. **Un livrable par étape, validé avant la suivante.** Une erreur corrigée dès qu'elle apparaît.
5. **Un seul document de conventions** par projet (règles de tracé, nomenclatures, hauteurs retenues), mis en tête
   de chaque mission.
6. **Une conversation neuve par grande étape** ; on lui redonne les plans utiles, le dernier fichier de
   coordonnées et les conventions.
7. **Noms de fichiers stables** : `PLAN-N1`, `COUPE-AA`, `FACADE-SUD`, `TOITURE`, `MASSE`.
8. **L'IA reconnaît et tranche, le code mesure** : l'agent exécute l'analyse d'image et choisit ses zooms (leçon du
   2026-10-02). Jamais les vecteurs du PDF (règle du thermicien), sauf décision contraire.

## Les 14 étapes et la plateforme aujourd'hui

| Étape du guide | Ce qui existe déjà | Ce qui manque |
|---|---|---|
| 1. Cadrage et inventaire | dépôt des PDF, tri en planches par nom, niveau | pièces écrites (CCTP, carnet de menuiseries), fiche des informations écrites, liste des manques |
| 2. Calage géométrique | échelle contrôlée par une cote, rotation, **nord**, **calage des niveaux** (validé) | correspondance des files et altimétries entre plans, coupes, façades |
| 3. Coupes et hauteurs | fenêtre « Coupes et élévations », hauteur mesurée en 2 clics, posée sur les locaux | lecture par mission (l'ancien agent faisait 0/13) ; épaisseurs de planchers, isolant aux liaisons |
| 4. Zonage et enveloppe | contours des locaux, natures (chauffé, circulation, non chauffé), retouches | **contour au nu intérieur typé par mission** (M1), à importer comme façade de référence |
| 5. Parois opaques verticales | **option C** : parois des locaux, compositions validées, coupures, adjacence | type mur mitoyen, mur enterré ; nomenclature des types |
| 6. Planchers et toitures | — | tout |
| 7. Menuiseries et cadres | modèles mesurés en élévation, posés au clic, posés sur les parois, surfaces | carnet de menuiseries, Uw/Sw/TLw, allège, position dans l'épaisseur |
| 8. Protections et masques | — | tout |
| 9. Structure | poteaux et refends dans le relevé | tableau des éléments en contact avec l'enveloppe, mode d'isolation |
| 10. Ponts thermiques | liaisons verticales du relevé, catalogue NF EN ISO 14683, jugement un par un | **liaisons par mission** (M2), liaisons horizontales (coupes), longueurs |
| 11. Métrés | surfaces brute / baies / opaque par paroi (écran) | tableur par type, orientation, niveau ; surface et volume chauffés |
| 12. Systèmes | — | fiche de saisie par zone |
| 13. Contrôle croisé | contrôle de cohérence d'un niveau | recoupements plans / coupes / façades |
| 14. Livrable final | — | dossier complet, note d'hypothèses, format du logiciel |

## Décisions proposées

- **D275 — Le guide fait foi.** Chaque lot de la plateforme sert une étape du guide ; le parcours de l'écran suit
  ses 14 étapes (aujourd'hui 6 étapes, qui en couvrent 2, 3, 4, 5, 7 et 10).
- **D276 — Le dossier d'étude local.** Chaque projet a un dossier sur le poste (`Etudes-thermique/<projet>/`) :
  plans renommés, `conventions.md`, et pour chaque étape ses livrables (fichier de coordonnées JSON, tableaux,
  plans annotés) et sa note « hypothèses et doutes ».
- **D277 — Une mission = une compétence Claude Code.** Pour chaque étape, une compétence (`/etape-04` …) qui prépare
  la mission : plan visé, conventions, livrable précédent, consigne du guide, boîte à outils d'analyse d'image ;
  et un nouvel agent autorisé à exécuter ce code (les agents existants ne sont pas modifiés). Le modèle est annoncé
  et vérifié.
- **D278 — Le site devient la table de validation** : il affiche chaque livrable sur le plan, permet de corriger
  au geste (ce qui existe déjà : calage, contours, parois, coupures, hauteurs, modèles) et enregistre la validation.
  Les livrables s'importent dans le format d'échange de D272.
- **D279 — Pilote : le R+1 du projet 1**, étape par étape, en commençant par écrire `conventions.md` à partir des
  décisions déjà prises (nu intérieur, doublage BA13 présumé, découpage par local, NF EN ISO 14683, angles…).
- **D280 — Ordre de reprise** : 1 et 2 (formaliser l'existant) → 4 (import M1) → 3 (coupes par mission) → 5 →
  7 → 10 (import M2) → 11 (métrés) → 14 (premier livrable) ; puis 6, 8, 9, 12, 13.

## Questions

1. **Rôle du site** : (a) il reste la table de validation et d'affichage, les analyses se font avec Claude sur le
   poste (recommandé : tout ce qui est construit sert) ; (b) tout se fait en local (Claude Code + fichiers), le site
   devient secondaire.
2. **Où tournent les missions** : Claude Code sur le poste (ici), ou claude.ai dans le navigateur comme pour M1 et
   M2 ? Sur le poste, la boîte à outils sera écrite avec numpy, scipy et Pillow (OpenCV n'est pas installé ; pas
   d'installation locale).
3. **Valeurs ψ (étape 10)** : le guide cite les règles Th-Bât comme source possible ; votre règle était les normes du
   dossier NORMES seulement (NF EN ISO 14683…). On garde cette règle ?
4. **Ordre de reprise D280** : d'accord, ou une autre priorité (par exemple le livrable dès que possible) ?
5. **`conventions.md` du projet 1** : je le rédige à partir des décisions déjà validées, et vous le relisez ?
