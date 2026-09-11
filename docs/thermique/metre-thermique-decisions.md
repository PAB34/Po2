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

## 1. Décisions prises

| Date | Décision | Raison |
|---|---|---|
| 2026-09-11 | Même table `users`, même JWT, routes `/api/thermique/*` sur **le backend Po2 existant** | Seule façon d'avoir réellement « le même compte » ; le modèle `ligue1` (comptes séparés) est écarté |
| 2026-09-11 | Comptes **bureaux d'études** = rôle `THERMIQUE_EXTERNE` (sans ville). `get_current_user`, utilisé par **toutes** les routes Po2, leur répond **403** ; l'outil et le profil passent par `get_authenticated_user`. Garde navigateur distincte : `basic-auth` (site principal) les refuse, `basic-auth-thermique` les accepte | Réponse Q1 : ils ne voient que l'outil. Verrou posé en un seul point, testé |
| 2026-09-11 | **Pas d'inscription libre** sur `thermique.*` (Caddy répond 404). Comptes bureaux d'études créés par un admin Po2 : `POST /api/thermique/admin/external-accounts` | Une inscription ouverte créerait un compte `USER`, donc un accès Po2 |
| 2026-09-11 | Projets **indépendants du patrimoine** (Q2), visibles de leur **seul propriétaire** (pas de partage à l'étape 1) | Réponse Q2 ; un bureau d'études ne doit voir que ses projets |
| 2026-09-11 | Front : **point d'entrée dédié** `thermique.html` dans le même build. nginx sert l'un ou l'autre selon l'hôte ; l'outil répond aussi sous `/thermique/` (essais sur staging) | Q4 : même conteneur, même design-system, aucun code d'authentification dupliqué |
| 2026-09-11 | Source v1 = **PDF vectoriel** ; détection des murs par **épaisseur de trait**, seuil ajustable par planche | Mesuré : correspondance exacte avec les cotes 31.82 / 33.13 sur le niveau 0 |
| 2026-09-11 | La nature d'une planche (plan / coupe / façade / plan masse) est **suggérée** (nom de fichier) puis **validée** par l'utilisateur | Pas de texte lisible dans les PDF ; un classement faux fausserait tout le métré. 11/11 suggestions justes sur le projet d'essai |
| 2026-09-11 | **Visionneuse = tuiles d'images rendues côté serveur par pdfium**, pas pdf.js dans le navigateur | Mesuré : pdf.js met 10 s (niveau 0) et **46,8 s** (coupe AB) à dessiner, et recommence à chaque zoom. En tuiles, la coupe s'affiche en **0,49 s** ; rendu 2 à 3,6 s, une fois par planche et par rotation ; 4 à 8 Mo par planche |
| 2026-09-11 | Tuiles servies par **adresse signée** (HMAC, une planche, 12 h) | Une balise `<img>` ne peut pas envoyer d'en-tête d'authentification |
| 2026-09-11 | Les mesures sont stockées en **points PDF** ; la transformation PDF → pixels est fournie par pdfium (`FPDF_PageToDevice`) | Cohérente avec le rendu par construction ; testée sur 8 combinaisons de rotation (planche et `/Rotate` du PDF) |
| 2026-09-11 | Toute détection automatique reste **corrigeable à la main** (ajouter, supprimer, reclasser un mur) | Des traits épais ne sont pas des murs (paroi courbe, garde-corps) |
| 2026-09-11 | Extraction des murs en **tâche de fond** avec cache (étape 2) | 20 à 40 s de lecture brute par plan, beaucoup plus par coupe |
| 2026-09-11 | **DXF et DWG à l'étape 2** (Q3) : un import DXF/DWG est refusé avec un message explicite | Le DXF garde les calques (meilleure source) ; le DWG demande un convertisseur (Q15) |
| 2026-09-11 | Les plans d'essai (`Thermique/`, ≈ 50 Mo, documents d'un projet client) **ne sont pas versionnés** (`.gitignore`) | Poids et confidentialité |

## 2. Questions ouvertes

### Produit

- ~~**Q1 — Pour qui ?**~~ → **Répondu** : aussi des bureaux d'études extérieurs (voir §1).
- ~~**Q2 — Lien avec le patrimoine ?**~~ → **Répondu** : indépendant.
- ~~**Q3 — Formats d'entrée.**~~ → **Répondu** : PDF vectoriel **et** DWG/DXF (pas de scans).
  Un DWG ou DXF du projet d'essai permettrait de comparer avec le PDF.
- **Q7 — Livrable attendu.** Proposition : tableau Excel par paroi (type, orientation, surface
  brute, surface des baies, surface nette) + linéaires de ponts thermiques **par type de liaison
  Th-Bât**, niveau par niveau. Faut-il un format d'échange vers un logiciel de calcul
  (Pléiades, ClimaWin, Perrenoud…) ? Lequel utilisez-vous ?
- **Q8 — Classes de murs.** Proposition : *extérieur* · *sur local non chauffé* · *intérieur
  porteur (refend)* · *intérieur non porteur* · *poteau*. Le mur de l'abri containers ou d'un
  garage doit-il être « sur local non chauffé » plutôt qu'« extérieur » ?
- **Q9 — Critère « porteur » automatique.** Proposition : épaisseur ≥ **15 cm** ET mur présent au
  même endroit sur le niveau du dessus ou du dessous. Seuil à confirmer.
- **Q10 — Point de calage.** Proposition : sur chaque plan, l'utilisateur clique un croisement
  d'axes de trame (ex. A/1), puis un 2e point pour fixer la rotation. L'échelle étant déjà connue,
  deux points suffisent. D'accord ?
- **Q11 — Orientation.** Le nord est saisi à la main (une flèche à poser sur le plan masse ou un
  plan de niveau), pour ventiler les surfaces par orientation. D'accord ?
- **Q16 — Partage.** Un projet doit-il pouvoir être partagé entre plusieurs comptes (ex. un agent
  de la Ville et le bureau d'études) ? Étape 1 : chacun ne voit que ses projets.
- **Q17 — Création des comptes bureaux d'études.** Aujourd'hui par un appel d'API réservé aux
  admins (je peux les créer à la demande). Faut-il un écran d'administration ?

### Technique et accès

- ~~**Q4 — Forme du front.**~~ → **Appliqué par défaut** : point d'entrée dédié (voir §1).
- **Q5 — Connexion.** Appliqué : on se connecte **une fois** sur `thermique.*` avec les mêmes
  identifiants (le jeton navigateur ne traverse pas les sous-domaines). Session partagée
  automatique (cookie de domaine) possible plus tard. À confirmer.
- **Q6 — Fenêtre d'identification du navigateur.** Appliqué : même double verrou que le site
  principal (fenêtre du navigateur puis page de connexion), mêmes identifiants. À confirmer.
- **Q12 — DNS (action de votre part).** Créer chez le registrar un enregistrement **A**
  `thermique` → `135.125.152.112` (même IP que `ligue1`). Tant qu'il manque, Caddy réessaie
  d'obtenir le certificat sans gêner les autres sites.
- **Q13 — Conservation des plans.** Stockage sur le VPS (volume `thermique_data`). Durée de
  conservation à définir ; supprimer un projet efface ses fichiers et ses tuiles.
- **Q15 — Conversion DWG.** Le DWG est un format fermé : il faut un convertisseur vers DXF,
  soit ODA File Converter (gratuit, licence propriétaire), soit LibreDWG (libre, GPL, moins
  fiable sur les versions récentes). À trancher avant l'étape 2.

### Pilotage

- ~~**Q14 — Priorité.**~~ → **Répondu** : l'outil thermique passe devant le réexport ASTECH.

## 3. Découpage

| Incrément | Contenu | État |
|---|---|---|
| **1 — Socle** | Sous-domaine + connexion Po2 + comptes bureaux d'études · projets · import PDF · visionneuse en tuiles (zoom, déplacement, rotation 90°) · nature de planche · échelle + contrôle par une cote | **Codé** (branche `feat/thermique-socle`, migration `0076`) |
| **2 — Murs** | Extraction en tâche de fond · murs (axe + épaisseur), poteaux, ouvertures · correction manuelle · classement extérieur / intérieur automatique · import DXF (et DWG selon Q15) | À faire |
| **3 — Calage** | Point de calage multi-niveaux · superposition visuelle · porteurs par superposition | À faire |
| **4 — Métré** | Hauteurs lues sur les coupes · surfaces de parois par orientation · linéaires de ponts thermiques Th-Bât · export Excel | À faire |

## 4. Journal des réponses

- **2026-09-11 — réponses de l'utilisateur** : Q14 on lance l'étape 1 maintenant · Q3 PDF
  vectoriel + DWG/DXF · Q2 indépendant du patrimoine · Q1 aussi des bureaux d'études.
- **2026-09-11 — étape 1 codée et vérifiée** :
  - backend : `app/core/roles.py`, `app/services/thermique.py`, `app/services/thermique_raster.py`,
    `app/api/routes/thermique.py`, migration `0076` (3 tables) ; `deps.py` sépare
    `get_authenticated_user` / `get_current_user` ; garde `basic-auth-thermique` ;
  - front : `thermique.html` + `src/thermique/` (connexion, projets, page projet, visionneuse) ;
  - infra : bloc Caddy `thermique.*`, volume `thermique_data`, nginx selon l'hôte ;
  - tests : 34 backend (dont position exacte d'un repère dans 8 combinaisons de rotation) +
    7 front ; scénario de bout en bout sur les **11 PDF réels** : 19/19 (import, suggestions
    11/11, cote 31,82 m retrouvée à 31,818 m, verrous des comptes, tuiles signées).
