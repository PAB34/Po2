---
type: state
status: actif
read_policy: toujours
source_of_truth: true
related:
  - 00-Index.md
  - 49-Spec-execution-refonte-Factures-Decisions-V1.md
  - Backlog.md
do_not_auto_read:
  - Archives/Journal-etat-dev-2026.md
---

# État actuel du développement

> Snapshot du **présent** : ce qui tourne en prod, les chantiers ouverts, et où reprendre.
> Détail chronologique des mises à jour passées → `Archives/Journal-etat-dev-2026.md` (ne pas lire par défaut).
> Détail par session → `Sessions/` (ne pas lire par défaut).

## 🔜 Reprise prochaine session

> Mise à jour : **2026-09-24** (F0 et F4 livrés en production ; il ne reste que F2).

- **▶️ REPRENDRE ICI — lot F2, le parcours en cinq étapes par niveau.** C'est le dernier lot de la série F.
  Décisions déjà écrites : `thermique/parcours-par-niveau-E3bis-decisions.md`. Son **étape 5 est F4**, qui
  existe désormais : il s'agit de l'héberger dans la structure en étapes, pas de la réécrire. Deux gestes
  restent volontairement reportés (D104) : **ajouter** un élément ou un pont absent, et déplacer les bornes
  d'un élément sur son tronçon. **Rappel permanent : rien n'est poussé sans accord explicite.**
- **✅ F4 EN PRODUCTION — les éléments d'enveloppe se corrigent** (`e8e4d764`, `44e5932d`, `283995f8`, sans
  migration). Sur le R+1, **92 des 227 éléments** arrivent marqués « à vérifier » : on peut maintenant les
  confirmer d'un clic, corriger leur type, leur composant et leurs nus, ou les écarter avec un motif. Une
  correction s'écrit dans le **relevé brut**, jamais dans le dessin (**D99**) : les 289 formes sont
  régénérées à chaque recalcul. Écarter ne supprime pas (**D100**), la lecture d'origine de l'agent est
  conservée à côté de la correction (**Q7**), et corriger un composant partagé annonce le nombre d'éléments
  touchés avant de proposer la portée (**D103**, `L1` en porte 34). Un **pont thermique est un élément du
  relevé** : les 77 liaisons correspondent aux 77 angles et abouts, leur pastille ouvre le même panneau.
  Décisions : `thermique/elements-F4-decisions.md`.
- **✅ F0 EN PRODUCTION — « Analyser avec Claude Code »** (`ca7abb47`, `b4762ffb`, `29d8f77f`, migration
  **0086**). File `thermique_travaux` côté serveur, relais `scripts/relais_thermique.py` côté poste, et une
  règle qui **refuse d'écraser un niveau déjà travaillé**, en disant pourquoi. Les niveaux partent du plus
  bas au plus haut pour que le catalogue monte (**D95**). Une session Claude expirée remet le niveau à faire
  au lieu de l'échouer (**D98**). ⚠️ **Le relais n'a jamais tourné de bout en bout** : ses fonctions sont
  testées, l'enchaînement complet reste à éprouver sur un vrai plan.
  Décisions : `thermique/relais-local-F0-decisions.md`.
- **⚠️ CORRECTIF D'USAGE — le local ouvert montre toutes ses cotes** (`283995f8`). D83 le disait déjà, mais
  la case « Côtés intérieurs » filtrait aussi le local sélectionné : un local décollé de la façade
  n'affichait plus une seule cote, sans rien dire. La fiche annonce désormais le linéaire déperditif et
  alerte quand il est nul. Mesuré sur le R+1 : la déperditivité tient jusqu'à **0,84 m** de recul.
- **📌 À FAIRE PAR LE THERMICIEN, hors code** : l'étude du R+1 porte un recouvrement de **10,85 m²**
  (*escalier atrium* / *4.2 Pôle multimédia*) et **42,36 m²** d'intérieur sans local.
- **✅ RECETTE RÉELLE DU MENU CONTEXTUEL — 2026-09-24.** Les trois gestes du clic droit ont enfin été
  exercés à la souris sur le R+1 (local 6.1.6, contour de 14 sommets) : ajout au pixel visé, suppression
  d'une poignée, redressement d'un côté (« 2 points de moins »), menu hors édition, fermeture au clic
  extérieur, déplacement du plan intact. **Un défaut trouvé et corrigé (D91)** : Échap ne fermait pas le
  menu, l'écouteur clavier posé en bouillonnement ne voyait jamais la touche ; il est passé en capture.
  Détail du banc : `thermique/nord-et-edition-plan-decisions.md` §5.

> Mise à jour précédente : **2026-09-23** (reprise Codex — métrés, nord et gestes de correction terminés localement).
- **✅ MÉTRÉS, PONTS ET ÉLÉMENTS SUR LE PLAN — F3** (`50005292`) : un clic sur un local dessine ses cotes,
  sa surface, ses ponts thermiques et ses éléments d'enveloppe ; les quatre réglages permettent d'étendre
  l'affichage au niveau entier. Le vrai R+1 recoupe 222 côtés, 289 éléments et 77 liaisons.
- **✅ NORD ET CORRECTION DU CONTOUR** (`a19dba04`) : flèche sans ambiguïté, de la base vers la pointe `N`,
  stockée en points PDF par planche et propageable entre formats ; les orientations sont recalculées dès la
  validation. Le contour se simplifie au lasso libre (`Alt + glisser`) et le clic droit propose ajouter,
  supprimer ou redresser un côté. Sur le vrai R+1, les **222 côtés** passent de « nord à caler » à une
  orientation calculée, sans perdre les 24 locaux. Vérifications : 73 tests backend, 32 frontend et build.
  Décisions : `thermique/nord-et-edition-plan-decisions.md`.
- **✅ LOT F1 TERMINÉ LOCALEMENT — contours calés et chaîne qui se relit elle-même.** Le fichier d'étude passe
  en `format_version: 3` : contours calés sur le nu intérieur mesuré à l'assemblage (D66), liaisons localisées
  (D74), tracé reprojeté des éléments (D75), et **contrôle de cohérence en six points (D77)** écrit dans
  `A-FAIRE.md` et dans l'étude, affiché à l'import. Un calage qui doute ne s'applique pas et rend la main
  au thermicien (**D78**, correction d'une régression livrée le 2026-09-23) ; le format **v2 reste
  importable**, pour pouvoir revenir en arrière. Sur le R+1 : couverture 86,2 → 91,1 %, surface sans local
  112,6 → 42,4 m², quatre locaux reculés de 2,08 m² en tout, et un recouvrement de 10,85 m² enfin signalé.

> Mise à jour précédente : **2026-09-23** (session Codex — benchmark agents thermiciens OpenAI).

- **✅ BENCHMARK LOCAL OPENAI / CLAUDE CODE SUR LE R+1** (commit `3eb0c5e4`, non poussé) : deux agents
  OpenAI de projet en lecture seule (`thermicien_plan_openai`, `thermicien_enveloppe_openai`), sans API ni
  vecteurs PDF ; comparateur strict des JSON, appariement géométrique, couverture IoU et projections avec
  légende. Quatre runs OpenAI aveugles exécutés : le meilleur run de base couvre 85,0 % des pièces face à
  Claude, mais les trois répétitions ne s'accordent qu'à 73,3 % en moyenne. Le run mal recalé reste pourtant
  très confiant ; un prompt renforcé corrige les débordements mais omet le plateau ouvert 4.2/4.3/4.4.
  **Décision : ne pas importer automatiquement**. Prochain lot : séparer couverture physique complète et
  frontières fonctionnelles proposées, puis ajouter les contrôles raster de couverture/débordement avant de
  tester l'agent enveloppe. Détail : `thermique/comparatif-agents-claude-openai.md`.

- **✅ LOT E2 TERMINÉ LOCALEMENT — Import d'une étude de niveau dans l'espace thermicien**
  (branche `feat/thermique-socle-raster`, migration **0083**, pas encore poussé) : fichier unique
  `etude-<niveau>.json` produit sans relancer les agents ; import strict lié au SHA-256 et à la page du PDF ;
  étude courante et historique versionné ; plan de référence stocké côté serveur ; 24 locaux du R+1 superposés
  au plan, liste chauffés/circulations/non chauffés et fiche détaillée en lecture seule. Vérification réelle :
  17 + 5 + 2 locaux, 230 éléments rattachés, 32 composants, erreur de reprojection maximale 0,0003/1000.
  Tests : 123 backend thermiques, 11 frontend thermiques, typecheck et build Vite. Décisions et preuves :
  `thermique/etude-niveau-E2-decisions.md`. **Prochain lot : E3**, édition/recalage des contours et rattachements,
  validation pièce par pièce et versions d'enregistrement.

- **✅ EN PROD — Outil de métré thermique, étape 1 (socle)** (PR #178, migration **0076**
  appliquée, vérifiée par SSH le 2026-09-11) : sous-domaine **`thermique.patrimoineaucarre.com`** (bloc Caddy), **mêmes comptes Po2**,
  comptes **bureaux d'études** (rôle `THERMIQUE_EXTERNE`, refusés partout ailleurs dans Po2),
  projets, import PDF → planches (type et niveau suggérés), **visionneuse en tuiles pdfium**
  (coupe lourde affichée en 0,49 s au lieu de 47 s avec pdf.js), échelle + contrôle par une cote.
  Docs : `thermique/metre-thermique-decisions.md`, `thermique/00-audit-existant-faisabilite.md`,
  ADR [[Decisions/013-outil-thermique-comptes-externes-et-tuiles]].
- **✅ DNS fait, certificat obtenu** : `https://thermique.patrimoineaucarre.com` en ligne.
  **Une seule connexion** (Q6) : fenêtre d'identification du navigateur retirée sur ce
  sous-domaine (branche `feat/thermique-connexion-unique`).
- **Cadrage précisé par l'utilisateur** : projet **à part** (sans lien avec Po2), pour les
  **thermiciens privés en bureau d'études** ; priorité à une **géométrie irréprochable** (murs,
  cloisons, menuiseries, planchers), entités thermiques Th-Bât ensuite ; export vers **Pléiades**
  et **Perrenoud** ; MVP en ligne, « logiciel » à terme (conséquences : décisions §3, Q20).
- **Retour d'usage 2026-09-11** (10 planches contrôlées par cote, 1/100 confirmé à 0,1 %) :
  échelle « non définie » rendue visible, mesure sans échelle signalée, échelle déduite d'une
  cote ramenée à l'échelle usuelle si l'écart < 1 % (branche `feat/thermique-echelle-ux`).
- **Bibliothèque de composants** (décision utilisateur du 2026-09-11, avant la détection de
  géométrie) : une seule bibliothèque pour l'étude thermique **et** le calcul des déperditions
  CVC, sourcée depuis les PDF Th-Bât. Cadrage et décisions : `thermique/bibliotheque-composants-decisions.md`.
  - **Lot B1 menuiseries fait** (branche `feat/thermique-bibliotheque-b1`) : moteur autonome
    `saas/backend/thermique_moteur/` (aucune dépendance à Po2, test à l'appui), édition JSON
    datée par le suivi officiel (2021-12-16), 168 lignes fenêtres + correctifs + portes +
    fermetures + Ujour-nuit/Uws, 0 erreur, 1 alerte (coquille du document, corrigée et signalée),
    page « Bibliothèque ». Reconstruire : `python -m thermique_moteur.bibliotheque.build "<REGLES TH BAT>"`.
  - **Lot B2a fait** (branche `feat/thermique-bibliotheque-b2`) : 294 matériaux (λ, ρ, Cp, μ)
    lus d'après la géométrie des tableaux du fascicule matériaux, 0 erreur, 3 alertes (notes du
    document) ; calcul d'une paroi en couches (`thermique_moteur/parois.py`) et épaisseur
    d'isolant pour un U cible ; constantes recoupées avec le fascicule méthodes ; onglets
    « Matériaux » et « Composer une paroi ». Reconstruire : `python -m thermique_moteur.bibliotheque.build "<REGLES TH BAT>"`.
  - **Lot B2b-1 fait** (branche `feat/thermique-bibliotheque-b2b`) : 40 tableaux de résistances R
    (briques, blocs, béton cellulaire, entrevous, dalles alvéolées, isolants en vrac, cloisons),
    1 074 valeurs, 7 tableaux imprimés en image transcrits (Q32), 0 erreur, 5 alertes (anomalies du
    document) ; onglet « Éléments tabulés » et couche « élément » dans « Composer une paroi ».
    Reconstruire : `python -m thermique_moteur.bibliotheque.build "<REGLES TH BAT>" --lot elements`.
  - **Recadrage utilisateur (2026-09-11)** : la bibliothèque doit être celle **du projet** (composants
    par catégorie, réutilisables comme modèles), pas seulement un référentiel consultable. Cadrage :
    `thermique/bibliotheque-projet-decisions.md` (Q33-Q38 répondues).
  - **Lots L1 + L2 faits** (branche `docs/thermique-bibliotheque-projet`, migration **0077**) :
    table `thermique_components` (composant de projet ou modèle du compte), moteur
    `thermique_moteur/composants.py`, API (créer, modifier, dupliquer, importer un modèle, enregistrer
    comme modèle), onglet « Bibliothèque » de chaque projet et « Mes modèles » : cartes repliables par
    catégorie, éditeur de paroi intégré avec recherche unique, épaisseur d'isolant appliquée en un clic.
  - **▶️ Prochain : L3** (menuiseries composées depuis le référentiel B1, ponts thermiques), **L4**
    (bibliothèque par défaut, export des préconisations), puis référentiel B2b-2, B2b-3, B2c.
    Fascicules « méthodes » dans `Thermique/REGLES TH BAT/methodes_th-bat/` (non versionné).
- **Métré sur les plans : pas commencé** (seul le prototype de lecture des traits existe). Méthode
  cadrée le 2026-09-14 dans `thermique/metre-plans-decisions.md` : contour de référence au nu
  intérieur par niveau, superposition N−1 / N / N+1, règle des « quatre quarts » pour les liaisons,
  détection = proposition, composants colorés sur le plan ; lots M1 à M5 ; Q39-Q42 répondues (contour d'abord, hauteurs saisies, 60/40, couleur par
  composant). **Lot M1 fait** (branche `feat/thermique-metre-m1`, migration **0078**) : onglet
  « Métré » (niveaux depuis les planches, calage A-B, nord, contour / local non chauffé / patio avec
  aimantation sur les traits épais, côtés qualifiés, calques des niveaux voisins, synthèse) ;
  moteur `thermique_moteur/traits.py` et `metre.py`. **Lot M3 (détection) fait** (branche
  `feat/thermique-detection-m3`, migration **0079**, `scipy`) : contour au nu intérieur détecté
  automatiquement, hauteurs lues sur les coupes, hauteur sous plafond. **Retour utilisateur** : il veut
  une **couche IA** de vérification étape par étape, planche par planche → cadrage
  `thermique/agent-verification-decisions.md` (réponses : vérification par **Claude Code**, pas d'API ;
  l'IA propose, le thermicien valide). **Lot M4a (types de murs) fait** (branche
  `feat/thermique-parois-menuiseries`) : épaisseur et isolant lus côté par côté, types proposés et
  rattachés à la bibliothèque, recalage du contour sur la face intérieure des murs ; cadrage
  `thermique/parois-menuiseries-pt-decisions.md` (Q51 : hauteurs des menuiseries lues sur les façades).
  **▶️ Prochain : M4b menuiseries + façades**, puis M4c ponts thermiques, puis M2.
  **Contours de pièces repris le 2026-09-18** (branche `fix/thermique-clic-piece`, commit `af9dc199`) :
  recalage manuel des sommets vérifié ; simplification adaptative des quadrilatères et des grands espaces
  multi-côtés, avec conservation du contour brut et garde-fous de surface/croisement. Validation réelle
  du R+1 faite : 20 → 4 et 59 → 19 sommets ; les limites absentes restent impossibles à inventer par
  lissage. Commit `edef539e` : alerte des contours complexes et retracé complet en quelques clics.
  **Parcours « pièce d'abord » ajouté le 2026-09-21** : création par points sans aucun calque ni
  menuiserie désignée, repli direct après un échec de détection, puis inventaire local de toutes les
  familles graphiques bordantes. La prise des sommets est maintenant constante en pixels et fonctionne
  à tous les zooms. **Nouveau MVP isolé démarré le 2026-09-21** : route `analyse`, bouton unique
  « Analyser le plan ». **Recadrage utilisateur du 2026-09-21** : cette route analyse maintenant le rendu
  raster par IA multimodale, sans lire les vecteurs PDF. Elle propose murs extérieurs, refends, cloisons,
  isolation, menuiseries, terrasses, balcons, poteaux et garde-corps, avec confiance, légende et édition de
  chaque point ; ajout/suppression manuels en dernier recours. Socle codé sur la branche
  `feat/thermique-inventaire-objets-r1`. **Mode d'exécution recadré** : agent de projet Claude Code lancé
  localement avec le compte du thermicien, vue globale + six tuiles et JSON strict ; l'adaptateur API serveur
  reste un repli. Le paquet R+1 est prêt et l'écran importe le JSON de l'agent avec contrôle de rotation puis
  rend ses points éditables. La session Claude Code locale doit encore être authentifiée avant la recette
  réelle (`thermique/analyse-ia-visuelle-r1-decisions.md`).
  Remplace le découpage de `thermique/etape2-geometrie-decisions.md`. Questions générales : Q15-Q18, Q20.
- Côté Po2, le **réexport ASTECH** (incrément 3) reste le prochain chantier, sans lien avec
  l'outil thermique.

> Reprise précédente : **2026-08-19** (session Claude — référentiel ASTECH : écran, carte, correctifs).

- **✅ EN PROD — Écran ASTECH complet** (`/patrimoine/astech`, migrations **0070 → 0074**,
  PR #98 à #117). Import idempotent avec gabarit conservé, moteur de reconnaissance,
  carte (points violets / verts appariés, marqueurs déplaçables ASTECH **et** Po2,
  éventail sur points superposés, géocodage inverse), héritage nom + adresse + cadastre,
  cible **bâtiment ou local**, statut `propose` distinct de `lie`.
- **État prod 2026-08-19** : 184 bâtiments · 160 sites · 626 locaux · 444 biens ASTECH.
- **▶️ PROCHAIN CHANTIER — incrément 3 : le réexport ASTECH** (rien commencé). Feuille
  réduite, en-têtes recopiés à l'octet près, normalisation d'adresse (bis/ter dans
  `BISTER`, type de voie en toutes lettres dans `LIBELVOIE`), `REFCAD`, coordonnées à
  virgule, feuille de traçabilité. Détail → `Sessions/2026-08-19 - Referentiel patrimoine historique ASTECH.md`.
- **⚠️ Action utilisateur** : cliquer « 2. Reconnaître les noms » — la purge du patrimoine
  a effacé les rattachements en cascade, le bouton les répare et les repropose.
- **En attente référente ASTECH** : périmètre importé (Q2), import par clé accepté ou non
  (Q12), largeur de `REFCAD`.

> Reprise précédente : **2026-08-18** (session Claude — référentiel patrimoine historique ASTECH).

- **✅ EN PROD — Référentiel patrimoine historique (ASTECH)** (PR #98, migration **0070**) :
  nouvelle page **`/patrimoine/astech`** (menu Patrimoine) pour l'aller-retour avec le fichier
  patrimoine de la collectivité.
  - **Import** d'un export ASTECH : détection automatique de la feuille exploitable (`Feuil1`
    porte la clé `CODE_BIEN` renseignée, `BAT` l'a vidée), **en-têtes conservés à l'octet près**
    (contrainte de réinjection : ASTECH n'accepte le fichier modifié que si en-têtes et code bien
    sont inchangés), payload des 317 colonnes conservé pour le futur réexport. Import idempotent.
  - **Rapprochement** : réutilise `_site_similarity` (cvc.py, déjà en prod). L'adresse ne sert
    qu'à départager. Deux garde-fous : ambiguïté entre candidats proches (sauf nom identique) et
    plusieurs biens visant le même bâtiment.
  - **Écran unique** : file des biens à gauche, carte à droite avec **marqueur violet déplaçable**
    (seul le point sélectionné), et bouton **« Attribuer IGN »** qui réutilise tel quel
    `POST /buildings/{id}/ign-attachment`. Aucun moteur dupliqué, `/buildings/list` inchangé.
  - **Mesuré sur données réelles** : 866 lignes lues → 399 biens importés, 26 hors périmètre,
    **78 rattachés automatiquement**, 295 à traiter.
  - **Reste à faire — incrément 3** : le **réexport** ASTECH (feuille réduite, normalisation
    d'adresse, `REFCAD`, coordonnées à virgule décimale, feuille de traçabilité).
  - **En attente de la référente ASTECH** : périmètre exact importé (Q2), confirmation qu'ASTECH
    accepte un import de mise à jour par clé, largeur du champ `REFCAD`. Chacun est un
    **paramètre**, pas une hypothèse enfouie.
  - **Doc** : `refonte-v1/patrimoine-fichier-historique-rapprochement-decisions.md` (audit,
    décisions Q1-Q13, mapping des colonnes, hypothèses de travail).

> Reprise précédente : **2026-07-07** (session Claude — atterrissage électrique : révision BPU + budget sans N-1).

- **✅ EN PROD — Référentiels** : vue **BPU curée** (`BpuReferentielV1`, PR #43 mergée) dans le hub
  `/refonte-v1/referentiels` ; **DPGF DALKIA = pas de cure** (Q7 close, PR #44 : page déjà refondue, seul
  gain cosmétique pour un risque réel → sans suite). Chantier « moteur métier / référentiels » **terminé**.
- **✅ EN PROD — Atterrissage électrique** (`/refonte-v1/marches`, onglets ENGIE/EDF, service
  `app/services/engie_elec_budget_revise.py`) :
  - **Révision BPU par typologie** (PR #46) : le prix de référence est résolu par **typologie du marché
    Hérault Énergie** (tous fournisseurs), plus par fournisseur facturant → le ratio Y/N-1 marche quand
    l'attributaire change (ENGIE 2026 vs EDF 2025). Passé de 0 % à **100 % des PRM** révisés.
  - **Budget de référence sans historique N-1** (PR #47) : marché neuf (ENGIE démarré 2026) → bascule
    « année en vigueur » (prix Y + fourniture BPU × conso ENEDIS N-1). ENGIE 2026 réf. **136 € → ~1,14 M€**.
  - **Import granulaire typologies 2026** (PR #48, + **re-import BPU prod** `import_xlsx` fichier élec
    `force=True`) : `BATIMENT` collapse → **BATIMENT_HTA/BT/BT36** ; résolveur partagé par **jeu de codes
    candidats** (additif). Effet : **contrôle factures gagne C2/C4 bâtiments** (0→4/5, C5 5/5, zéro régression).
- **🟢 Finding B (EDF réalisé 2026 vide) = CLOS sans action** : décalage de facturation EDF (factures émises
  2026 = conso 2025, déjà en base). La conso 2026 n'est pas encore facturée ; l'atterrissage projette. RAS.
- **▶️ Prochaines étapes possibles** (rien de bloquant en attente) : (a) charger le **BPU gaz TE** en prod
  (absent ; fichier `_herault`, impact module gaz — tâche séparée) ; (b) **Suivi des indices/variables**
  (`/refonte-v1/marches`, transversal) ; (c) solder la **PR #32 factures** (validée staging, non mergée).
- **📄 Docs du chantier** : `atterrissage-bpu-elec-decisions.md` (§8-11 typologie), `atterrissage-elec-budget-sans-n1-decisions.md`,
  `bpu-import-granulaire-2026-decisions.md` (import granulaire + re-import).
- **🛠️ Env / infra** : **node dispo** (portable) → typecheck front via jonction `node_modules` + `tsc.cmd -b`.
  Déploiement staging via API : payload `{"ref":"main","inputs":{"ref":"<branche>"}}` (inputs.ref sinon
  déploie main). Staging = base SÉPARÉE `po2-staging-db` ; re-import BPU = `import_xlsx(..., force=True)`
  (remplacement propre du doc).

> Reprise **2026-07-06** (référentiels marchés) conservée pour trace :
> hub `/refonte-v1/referentiels` (PR #42) embarquant DPGF DALKIA + BPU ; vue BPU curée alors en cours (#43).
> Docs : `moteur-metier-referentiels-decisions.md` §0bis-0ter, `referentiel-bpu-ux-decisions.md` §4bis.

> Reprise précédente (**2026-07-03**, Codex/Claude — budget révisé élec + cadrage moteur métier) conservée
> ci-dessous pour trace. ⚠️ La cible « onglet Référentiel par tier » y est **supplantée** par le hub central.

- **PR #41 MERGÉE EN PROD** (santé 200) : atterrissage **ENGIE élec** + **EDF éclairage public** (moteur élec
  générique fixe/variable par PRM, conso attendue = ENEDIS + DJU thermosensible ENGIE / photopériode EDF,
  prix BPU+TURPE fallback N-1), **calque « Cible conso & intéressement » DALKIA** (`/refonte-v1/marches`),
  **tri des colonnes** (DALKIA/ENGIE/EDF/gaz), **fix parser ENGIE** (soutirage variable : montant mal placé
  dans la colonne prix), et **DJU auto-sync planifié** (Open-Meteo, `scheduler.py`). Aucune migration.
- **Données prod corrigées** : 52 lignes ENGIE soutirage variable (6,50 M€ → 1 224 €). Vérifié prod : ENGIE
  2026 réalisé 724 923 € (0 anomalie, ENEDIS 176 PRM) ; EDF 2026 prévision 87 816 € (ENEDIS 326).
- **Infra** : staging a désormais un volume `energie_data` inscriptible + `ENERGIE_DIR` (repo monté `:ro`) ;
  prod = bind mount déjà inscriptible. ⚠️ **ENEDIS sur staging = snapshot figé copié de prod** (pas de creds
  live) ; DJU se récupèrent seuls (Open-Meteo) partout maintenant.
- **⚠️ Action utilisateur en attente** : **importer le lot de factures ENGIE N-1 (2025)** (case « Importer et
  mettre à jour ») → sinon la prévision ENGIE reste ≈ 0 (prix non dérivables sans historique).
- **🎯 Prochain chantier = MOTEUR MÉTIER** : centraliser les **référentiels de marché DPGF/BPU** (DALKIA CPE +
  Hérault Énergies ENGIE/EDF/TotalE, à venir SUEZ/SPIE) sous `/refonte-v1/marches` (onglet **Référentiel** par
  tier), avec cohérence des adresses. **Audit complet écrit** → `docs/refonte-v1/moteur-metier-referentiels-marches-audit.md`.
  Aujourd'hui les référentiels sont éclatés en legacy : DPGF = `/cpe/dalkia-import`, BPU = `/energie/bpu`.
  **Décision structurante à prendre (Q1 du doc)** : regrouper BPU+DPGF sous « Marchés » (vision user) vs BPU
  sous « Énergie » (doc 13). Réutilise le backend existant (`cpe-dalkia-ref`, `bpu`) = portage UX.
- **Poste entreprise** : tests via `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 DATABASE_URL='sqlite:///./test.db' python -m pytest <tests_ciblés> -p no:cacheprovider`. npm/node absents → typecheck front via CI.

### Précédent — 2026-07-02 (handoff Codex)

> Detail complet -> `Sessions/2026-07-02 - Indices variables marches staging.md`.

- **PR #37 MERGEE EN PROD** : budget contractuel revise par coefficient trimestriel DALKIA (P2/P3, P1 gaz exclu).
- **PR #38 DRAFT SUR STAGING** (`codex/indices-variables`) : nouvelle vue lecture seule **Indices & variables** sur `/refonte-v1/marches` + endpoint `GET /api/marches/indices-variables?year_from=&year_to=`. CI verte (`backend`, `frontend`). Staging redeploye apres correction, health 200, revue UI Chrome OK.
- **Correction importante deja faite dans #38** : coefficients observes DALKIA agreges a **un point par marche/trimestre** (moyenne ponderee par `line_count`) pour eviter les lignes quasi dupliquees en table.
- **Prochaine decision** : l'utilisateur relit staging ; si OK, passer #38 ready puis merger `main` (prod auto) et surveiller prod. Ne pas merger prod sans accord explicite.
- **Suite fonctionnelle apres #38** : budget revise fiable en reconstitution **FIXE/VARIABLE**, maille **site/PRM**, en branchant les moteurs existants (gaz TotalEnergies conseille en premier, puis ENGIE/TURPE+BPU+ENEDIS, puis EDF cible a definir).
- **Poste entreprise** : `pytest.exe` peut bloquer en collecte. Utiliser `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, `DATABASE_URL=sqlite:///./test.db`, `python -m pytest <tests_cibles> -p no:cacheprovider`.

> **Contexte antérieur (2026-07-01 soir) — PR #32, #33, #34, #35 mergées sur `main` et déployées en PROD** (migration 0066 en prod).

- **État global** : tout le travail de la session est **en production** (`patrimoineaucarre.com`, santé 200) :
  - **Budget par marché v1** (PR #33) : `accounting_budget_lines` (migration 0066), API `/api/accounting-budget/*`, module front « Marchés » (`/refonte-v1/marches`). Décisions : pilote DALKIA, annuel, atterrissage pro-rata.
  - **Import codification DALKIA** (PR #34) : lit le « Code contrat » de la feuille « Poste facturé vers Nature ctpab » + colonnes de validation compta. Classeur canonique = `MATRICE_DALKIA-COMPATBILITE.xlsx`. Règle process « fil du dev » actée (05-Conventions §2 + AGENTS/CLAUDE).
  - **Matrice versionnée éditable** (PR #35) : `/refonte-v1/matrices` = fenêtre pleine page éditable (axes comptables, tri, colonnes redimensionnables, import/export). Édition directe version active (archivée figée). Colonne « Désignation site » (facture). Antenne DALKIA = code court. Enrichissement suggested_antenna via **référentiel CIRIL** (`saas/backend/app/data/index_compta.json`). `prefill_energy_matrices()` pré-remplit ENGIE/EDF (antenne 100%, service/fonction best-effort, opération vide car élec=fonctionnement).
- **⚠️ Données ENGIE/EDF : faites sur STAGING, PAS en PROD.** Le code `prefill_energy_matrices` + seed est déployé en prod mais **pas encore exécuté** (prod n'a aucune matrice seedée). Pour activer en prod : lancer via container `prefill_energy_matrices(db, city_id)` puis `seed_from_existing`, après validation. Idem la correction antenne DALKIA (UPDATE) : faite sur staging seulement.
- **Objectif probable prochaine session** : (1) décider si on **rejoue le setup matrices en prod** (DALKIA seed + ENGIE/EDF prefill) ; (2) **service/fonction best-effort** ne couvrent que ~10-18% des PRM (bâtiments typés) → la compta complète le reste via l'éditeur ; (3) **grille_9 CIRIL = pôle/direction « BÂTIMENTS »** — pas encore un axe de matrice, à intégrer si besoin ; (4) budget : réalisé fiable dépend toujours des extracteurs de lignes (PO2-FIN-001).
- **⚠️ Staging vs migrations** : la base staging était stampée `0066` par les déploiements de branche ; maintenant que `main` a `0066`, les déploiements staging depuis `main` sont cohérents.
- **À ne pas faire sans validation** : rejouer prefill/seed en prod sans accord ; confondre atterrissage financier et intéressement (`cpe_atterrissage.py`) ; toucher les fichiers Codex (`PRONO/*`, `knockout_mc.py`).
- **Niveau de confiance** : élevé (v1 codée et déployée conformément au cadrage validé ; reste la revue utilisateur sur staging avant merge).

## 🟢 Ce qui tourne en prod (https://patrimoineaucarre.com)

| Module | Route | État |
|---|---|---|
| Auth | `/login`, `/register`, `/account` | Stable |
| Patrimoine — liste / détail | `/buildings`, `/buildings/:id` | Stable ; rattachement manuel PRM/PCE/eau avec contexte fournisseur/contrat |
| Patrimoine — création / import hiérarchique | `/buildings/create-edit` | `SITE`→`Site`, `BATIMENT`→`Building.site_id`, `LOCAL`→`Local.building_id` |
| Patrimoine — rapprochements (file) | `/patrimoine/rapprochements` | PRM ENEDIS + PCE GRDF → candidat Bâtiment/Site, lien canonique |
| Gestion technique SYPEMI | `/buildings/technique` | Stable (310 équip.) + onglet Terrain (import CVC) |
| CVC fluides — cockpit F-Gaz / ESP | `/buildings/cvc-fluides` | Cockpit, Registre F-Gaz, Actions, ESP/DESP, Import |
| Énergie — vue / détail PRM / préconisations | `/energie`, `/energie/:prmId`, `/energie/preconisations` | Stable ; collecte ENEDIS sync de secours |
| Factures ENGIE/EDF | `/energie/factures`, `/energie/factures/:id` | Stable (parser XLSX ENGIE, contrôle BPU/TURPE/ENEDIS, décision, lots, 9 filtres facettes) |
| Factures gaz TotalEnergies | onglet Factures marché > Hérault Énergie | Import + contrôle cohérence/fourniture/acheminement/taxes |
| Facturation TURPE | `/energie/facturation` | Stable |
| CPE DALKIA | `/cpe` | Avancé : cockpit finance, contrôle factures, référentiel DALKIA, conso multi-fluides |
| BPU | `/energie/bpu` | Timeline · TURPE · Documents/Import · Édition tableau |
| Matrices comptables versionnées | API `/api/accounting-matrices/*` | Backend complet mergé `main` (schéma + XLSX + apply/snapshots) |
| Refonte React V1 (labo) | `/refonte-v1/*` | `/matrices` branché API réelle ; `/factures` **mergé `main`** (PR #32) ; `/marches` = budget par marché (PR #33) + onglet **« Budget contractuel (poste) »** (PR #36, non mergée) |
| Atterrissage budget contractuel CPE | API `/api/cpe/finances/contract-budget-landing` | PR #36 non mergée : budget contractuel (prévu DPGF) − réalisé (factures CPE) par poste ; calcul à la volée |

## 📦 Migrations alembic

HEAD prod constaté (2026-08-19) : **`0074_add_local_address`** (référentiel patrimoine
historique ASTECH). Précédent : `0066_add_accounting_budget_lines` (budget par marché, maille opération, branche `feat/budget-marches` PR #33 — non encore sur `main`). Dernière migration sur `main` : `0065_add_supplier_contacts`.
Jalons : `0017` hiérarchie sites · `0041` seed CPE scope · `0048` CVC F-Gaz · `0056` rapprochements
patrimoine · `0057` gas_invoices · `0064` matrices. Liste complète prod → journal archivé.

## 🔥 Chantiers ouverts (présent)

| ID Backlog | Chantier | État / prochaine action |
|---|---|---|
| PO2-FIN-001 | Factures + matrice comptable + atterrissage | Backend matrices mergé ; reste extracteurs réels de lignes facture sur `apply`, droits par rôle. Bloque la fiabilité du réalisé du nouveau module Budget (PR #33) |
| PO2-FIN-002 | Budget par marché + suivi financier | v1 codée (PR #33, pilote DALKIA) : `accounting_budget_lines`, réalisé pro-rata, module « Marchés ». Reste : validation staging, merge, extension autres marchés, atterrissage physique doc 34 §F04 (v2) |
| PO2-UX-002 | Refonte frontend React V1 | Tranche `Factures & décisions` (doc 49) ; Phase 5 à brancher |
| PO2-CPE-001 | Contrôle factures DALKIA CPE | Reimport CSV, rattacher codes piscines, parser DPGF Lot 1/2 |
| PO2-FACT-001 | Audit facture ENGIE + socle EDF | Reimport XLSX force update, valider fiche liaison finance |
| PO2-PAT-003 | Rapprochements patrimoine | V1 livrée ; reste sources CPE/maintenance, cible Local, matching par adresse |
| PO2-ENEDIS-001 | ENEDIS async prod | Bloqué côté ENEDIS ; contournement sync de secours en place |
| PO2-GRDF-001 | Connecteur GRDF gaz | Scaffolding Phases 0-1 ; reste Phases 2-5 |

> Le détail complet des chantiers, dépendances et statuts vit dans `Backlog.md` (source de vérité du « quoi faire ensuite »).

## 📊 Données en prod (ordre de grandeur)

`cities` 1 (Sète) · `buildings` ~530 · `equipment_references` 310 · `bpu_documents` 17 / `bpu_price_components` 523 · `enedis_async_jobs` 0 (scheduler en attente du canal validé).

## ⚙️ Invariant gaz (2026-05-22)

- `BuildingMeterLink` = point central bâtiment → compteur multi-fluides.
- Le flux GRDF alimente PCE et consommations gaz quel que soit le fournisseur.
- BPU gaz HÉRAULT ÉNERGIE lot 7 importable comme référence `TOTALENERGIES` (compteurs Ville).
- La cotation OS3 gaz du P1 DALKIA reste dans le module CPE ; ne pas la fusionner avec la référence BPU TotalEnergies.

## 🔐 Secrets et accès

- **GitHub PAT** : `git credential fill` depuis la machine de l'utilisateur.
- **SSH VPS** : `~/.ssh/po2_vps2` → `ubuntu@135.125.152.112`.
- **Password FTP ENEDIS** : `/root/.ftp_password_enedis` sur le VPS (root only).
- **Clé AES ENEDIS** : `.env` prod `ENEDIS_DECRYPTION_KEY`. **Canal ENEDIS** : `506350699`.
- ⚠️ **Ne JAMAIS afficher de password/clé en clair** (chat, commit, vault).

## Liens utiles

- Pilotage : [[Backlog]] · [[03-Roadmap-fonctionnalites]]
- Tranche active : [[49-Spec-execution-refonte-Factures-Decisions-V1]]
- Décisions durables : [[Decisions/010-matrices-comptables-versionnees]] · [[Decisions/011-assistant-matrices-et-decisions-factures-V1]] · [[Decisions/012-auto-validation-et-semantique-controle-factures-V1]]
- Historique : `Archives/Journal-etat-dev-2026.md` · `Sessions/` *(ne pas lire par défaut)*
