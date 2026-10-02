---
type: decisions
status: actif
read_policy: si la tâche concerne l'outil thermique
related:
  - 00-audit-existant-faisabilite.md
  - ../Decisions/013-outil-thermique-comptes-externes-et-tuiles.md
---

# Outil de métré thermique — décisions et questions ouvertes

> Fichier « fil du dev » : on y répond au fil de l'eau. Existant vérifié →
> `00-audit-existant-faisabilite.md`. Ouvert le **2026-09-11**. Décisions durables →
> ADR [[Decisions/013-outil-thermique-comptes-externes-et-tuiles]].
>
> ⚠️ **Ce fichier est la seule version à jour** (branche `main`). Pour répondre, écrire ici.

## 1. Décisions prises

| Date | Décision | Raison |
|---|---|---|
| 2026-09-11 | **Projet à part**, sans lien avec Po2 ni le patrimoine de la Ville ; public = **thermiciens privés en bureau d'études** | Réponses Q1 et Q2 |
| 2026-09-11 | Même table `users`, même JWT, routes `/api/thermique/*` sur **le backend Po2 existant**, pour le MVP | Besoin « même compte que patrimoineaucarre.com » ; séparation possible plus tard (voir §3) |
| 2026-09-11 | Comptes **bureaux d'études** = rôle `THERMIQUE_EXTERNE` (sans ville). `get_current_user`, utilisé par **toutes** les routes Po2, leur répond **403** ; l'outil et le profil passent par `get_authenticated_user`. La garde navigateur du site principal les refuse | Ils ne voient que l'outil. Verrou posé en un seul point, testé |
| 2026-09-11 | **Une seule connexion** sur `thermique.*` : plus de fenêtre d'identification du navigateur, seulement la page de connexion de l'outil | Réponse Q6 |
| 2026-09-11 | **Pas d'inscription libre** sur `thermique.*`. Comptes bureaux d'études créés par un admin : `POST /api/thermique/admin/external-accounts` | Une inscription ouverte créerait un compte `USER`, donc un accès Po2 |
| 2026-09-11 | Projets visibles de leur **seul propriétaire** (pas de partage pour l'instant) | Un bureau d'études ne doit voir que ses projets |
| 2026-09-11 | Front : **point d'entrée dédié** `thermique.html` dans le même build (voir Q4 expliquée ci-dessous) | Même conteneur, même design, aucun code de connexion dupliqué |
| 2026-09-11 | **Priorité de l'étape 2 = une géométrie irréprochable** : murs, cloisons, menuiseries, planchers. La **bibliothèque d'entités thermiques** (classes de parois, porteurs, ponts thermiques) vient **ensuite**, construite sur les règles Th-Bât de `Thermique/REGLES TH BAT` | Réponses Q8 et Q9 |
| 2026-09-11 | Source v1 = **PDF vectoriel** ; détection des murs par **épaisseur de trait**, seuil ajustable par planche | Mesuré : correspondance exacte avec les cotes 31.82 / 33.13 sur le niveau 0 |
| 2026-09-11 | Formats : **PDF vectoriel, DWG/DXF, et parfois des scans**. DXF/DWG à l'étape 2 ; scans plus tard (tracé assisté à la main, la détection automatique ne s'applique pas à une image) | Réponse Q3 |
| 2026-09-11 | La nature d'une planche (plan / coupe / façade / plan masse) est **suggérée** (nom de fichier) puis **validée** par l'utilisateur | Pas de texte lisible dans les PDF. 11/11 suggestions justes sur le projet d'essai |
| 2026-09-11 | **Visionneuse = tuiles d'images rendues côté serveur par pdfium**, pas pdf.js dans le navigateur | Mesuré : pdf.js 10 s (niveau 0) et **46,8 s** (coupe AB) à chaque zoom ; en tuiles, la coupe s'affiche en **0,49 s** |
| 2026-09-11 | Tuiles servies par **adresse signée** (HMAC, une planche, 12 h) ; mesures stockées en **points PDF**, transformation fournie par pdfium | Une balise `<img>` ne peut pas envoyer d'en-tête ; cohérence testée sur 8 combinaisons de rotation |
| 2026-09-11 | **Calage** entre niveaux : un croisement d'axes de trame cliqué sur chaque plan + un 2e point pour la rotation | Réponse Q10 (à réajuster à l'usage si besoin) |
| 2026-09-11 | **Nord** saisi à la main (flèche posée sur un plan) | Réponse Q11 |
| 2026-09-11 | Le **moteur géométrique** (lecture PDF/DXF, détection) sera écrit comme une **brique autonome**, sans dépendance à la base, au serveur web ni à Po2 | Garder ouvertes les deux voies « logiciel » de Q13 |
| 2026-09-11 | Toute détection automatique reste **corrigeable à la main** | Des traits épais ne sont pas des murs (paroi courbe, garde-corps) |
| 2026-09-11 | Les plans d'essai (`Thermique/`) **ne sont pas versionnés** (`.gitignore`) | Poids et confidentialité |

## 2. Réponses et questions

### Produit

- **Q1 — Pour qui ?** → **Répondu** : « Tout thermicien privé en bureau d'étude ».
- **Q2 — Lien avec le patrimoine ?** → **Répondu** : « Pas du tout aucun rapport, c'est vraiment
  un autre projet ».
- **Q3 — Formats d'entrée.** → **Répondu** : PDF vectoriel, **DWG/DXF**, et **parfois des scans**.
  Un DWG ou DXF du projet d'essai permettrait de comparer avec le PDF.
- **Q7 — Livrable attendu.** → **Répondu** : « Pléiades, Perrenoud principalement ». Reste à
  vérifier ce que chacun sait importer (Q18).
- **Q8 / Q9 — Classes de murs, critère porteur.** → **Répondu** : d'abord une analyse
  **irréprochable de la géométrie** (murs, cloisons, menuiseries, planchers) ; la bibliothèque
  d'entités thermiques viendra ensuite, sur la base réglementaire de `Thermique/REGLES TH BAT`.
- **Q10 — Point de calage.** → **Répondu** : d'accord, réajustement à l'usage si besoin.
- **Q11 — Orientation (nord à la main).** → **Répondu** : d'accord.
- **Q16 — Partage.** Un projet doit-il pouvoir être partagé entre plusieurs comptes (ex. deux
  thermiciens du même bureau d'études) ? Aujourd'hui : chacun ne voit que ses projets.
- **Q17 — Création des comptes bureaux d'études.** Aujourd'hui par un appel réservé aux admins
  (je peux les créer à la demande). Faut-il un écran d'administration, ou une inscription
  libre (qui supposerait de séparer l'outil de Po2, voir Q13) ?
- **Q18 — Formats d'échange Pléiades / Perrenoud.** Je dois vérifier ce que chacun importe
  (maquette BIM au format IFC ou gbXML, fichier propre à l'éditeur, simple tableau). Avez-vous
  un exemple de fichier que vous importez aujourd'hui dans l'un ou l'autre ?

### Technique et accès

- **Q4 — Forme du front.** → **Réponse demandée : « besoin de plus de précision ».** En clair :
  l'outil thermique et Po2 sont **deux portes d'entrée dans le même programme**. Quand on tape
  `thermique.patrimoineaucarre.com`, le serveur montre les écrans de l'outil ; quand on tape
  `patrimoineaucarre.com`, il montre Po2. Pour vous et pour les thermiciens, **rien de
  visible** : ce sont deux sites distincts. Pour moi : un seul programme à entretenir et à
  déployer. L'autre option (deux programmes séparés) n'apporte rien tant que l'outil partage les
  comptes de Po2 ; elle redeviendra utile si l'outil devient un produit à part (Q13).
- **Q5 — Connexion une fois sur `thermique.*` avec les mêmes identifiants.** → **Répondu** : OK.
- **Q6 — Double verrou.** → **Répondu** : « Non une seule fois la connexion ». Appliqué : la
  fenêtre d'identification du navigateur est retirée sur `thermique.*`.
- **Q12 — DNS.** → **Fait** : `thermique` → `135.125.152.112`, certificat HTTPS obtenu le
  2026-09-11, site en ligne.
- **Q13 — Conservation des plans / stratégie.** → **Réponse** : « Je pense qu'en réalité la MVP se
  fera sur le cloud mais à terme ce sera un logiciel, je ne connais pas les conséquences de cette
  stratégie. » → explications au §3, question Q20.
- **Q15 — Conversion DWG.** Le DWG est un format fermé : il faut un convertisseur vers DXF,
  soit ODA File Converter (gratuit, licence propriétaire), soit LibreDWG (libre, GPL, moins
  fiable sur les versions récentes). À trancher avant l'import DWG.
- ~~**Q14 — Priorité face au réexport ASTECH.**~~ → **Sans objet** (« ce sujet n'a pas lieu
  d'être ») : ce sont deux projets distincts.

## 3. MVP en ligne, puis « logiciel » : les conséquences (Q13)

**Aujourd'hui (MVP en ligne, sur le serveur de Po2)**

- ✅ Rien à installer chez les thermiciens, une seule version, mises à jour immédiates ; le
  travail lourd (rendu des plans, détection) est fait par le serveur.
- ⚠️ Les plans des clients des bureaux d'études sont **stockés sur votre serveur** : cela
  engage votre responsabilité (confidentialité, RGPD, sauvegardes, conditions d'utilisation).
- ⚠️ Le coût du serveur grandit avec l'usage : ≈ 5 à 10 Mo par planche (PDF + tuiles) et du
  calcul à chaque import.
- ⚠️ L'outil partage le serveur, la base et les comptes de Po2 : une panne ou un pic de charge de
  l'un touche l'autre, et des comptes privés côtoient ceux de la Ville (protégés par le verrou
  testé, mais dans la même base).

**« Logiciel à terme » peut vouloir dire deux choses, aux conséquences différentes (Q20)**

| | (a) Logiciel **en ligne** vendu aux bureaux d'études | (b) Logiciel **installé** sur le poste |
|---|---|---|
| Où sont les plans | Sur votre serveur | Chez le thermicien (argument fort de confidentialité) |
| Ce qu'il faut changer | **Séparer l'outil de Po2** : sa base, ses comptes (inscription, mot de passe oublié, abonnements), éventuellement son nom de domaine, des conditions d'utilisation | **Faire tourner le moteur sans serveur** : empaqueter le moteur (Python + pdfium) dans une application Windows, gérer licences, mises à jour et versions de Windows |
| Effort | Limité : le code est déjà isolé (tables, routes et écrans à part) ; le gros morceau est la gestion des comptes | Plus lourd : nouvelle application à distribuer et à maintenir sur chaque poste |
| Mises à jour | Immédiates pour tous | À installer chez chacun |

**Ce que je fais dès maintenant pour garder les deux voies ouvertes** : le moteur géométrique de
l'étape 2 sera une **brique autonome** (aucun lien avec la base, le serveur web ou Po2), avec ses
propres tests ; le serveur ne fera que l'appeler. Aucun choix n'est à faire tout de suite.

- **Q20 — Quel « logiciel » visez-vous ?** (a) en ligne vendu aux bureaux d'études, (b) installé
  sur le poste, (c) pas encore décidé. Réponse utile avant de travailler les comptes (Q17).

## 4. Découpage

| Incrément | Contenu | État |
|---|---|---|
| **1 — Socle** | Sous-domaine + connexion + comptes bureaux d'études · projets · import PDF · visionneuse en tuiles (zoom, déplacement, rotation 90°) · nature de planche · échelle + contrôle par une cote | **En prod** (PR #178, migration `0076`) ; site en ligne ; connexion unique (Q6) en cours |
| **Bibliothèque** | Composants partagés par l'étude thermique et le calcul des déperditions : parois opaques (couches, épaisseur d'isolant), menuiseries, ponts thermiques, sourcés depuis les règles Th-Bât | **En cadrage — prioritaire** (décision utilisateur du 2026-09-11) : `bibliotheque-composants-decisions.md` |
| **2 — Géométrie des plans** | Moteur autonome : murs (axe + épaisseur), cloisons, poteaux, **menuiseries** (portes, fenêtres) · correction manuelle · import DXF (et DWG selon Q15) | À faire, après la bibliothèque : `etape2-geometrie-decisions.md` |
| **3 — Niveaux, planchers, pièces** | Calage multi-niveaux (Q10) · superposition · **planchers** et hauteurs lus sur les coupes · nord (Q11) · **pièces et zones** pour les déperditions | À faire |
| **4 — Calculs** | Rattachement des composants aux éléments · U × surface, ψ × longueur · déperditions par pièce et par zone · export vers Pléiades / Perrenoud (Q18) | À faire |
| **Plus tard** | Scans : tracé assisté à la main | À faire |

## 5. Journal des réponses

- **2026-09-11 — premières réponses** (questionnaire en séance) : on lance l'étape 1 · PDF
  vectoriel + DWG/DXF · indépendant du patrimoine · aussi des bureaux d'études.
- **2026-09-11 — étape 1 codée, vérifiée et mise en prod** (PR #178) : 35 tests backend + 7 front ;
  scénario de bout en bout sur les **11 PDF réels** : 19/19.
- **2026-09-11 — réponses écrites dans le fichier** (reportées ici mot pour mot depuis une copie
  locale obsolète) : Q1 « Tout thermicien privé en bureau d'étude » · Q2 « Pas du tout aucun
  rapport, c'est vraiment un autre projet » · Q3 « aussi des DWG/DXF et parfois des scan » ·
  Q7 « Pleiade Perrenoud principalement » · Q8/Q9 « obtenir un outil qui analyse de manière
  irréprochable la géométrie du bâtiment et ses composants, murs, cloisons, menuiseries,
  planchers ; ensuite une bibliothèque d'entités thermiques sur la base réglementaire »
  · Q10 « Ok, je verrai à l'usage » · Q11 « ok » · Q4 « besoin de plus de précision » ·
  Q5 « OK » · Q6 « Non une seule fois la connexion » · Q12 « déjà réalisé » ·
  Q13 « MVP sur le cloud, à terme un logiciel, je ne connais pas les conséquences » ·
  Q14 « ne pas traiter ce sujet ».
