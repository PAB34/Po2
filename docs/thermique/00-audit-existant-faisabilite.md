---
type: audit
status: actif
read_policy: si la tâche concerne l'outil thermique
related:
  - metre-thermique-decisions.md
---

# Outil de métré thermique — audit de l'existant et faisabilité

> Rédigé le **2026-09-11** (session Claude), avant toute ligne de code, en application de la
> règle « fil du dev » (`05-Conventions-IA.md` §2). Les chiffres sont **mesurés** sur les plans
> fournis, pas supposés. Questions ouvertes → `metre-thermique-decisions.md`.

## 1. La demande

Outil en ligne pour assister le thermicien dans la partie fastidieuse des métrés :

1. importer des plans et des coupes ;
2. les visualiser ;
3. distinguer une coupe d'un plan (leur rôle dans le calcul est différent) ;
4. définir un **point de calage** commun pour superposer les niveaux et garder la continuité des
   linéaires dans le calcul des ponts thermiques ;
5. détecter **tous les murs** ;
6. qualifier les murs **extérieurs** et **porteurs intérieurs**, à la main et si possible
   automatiquement ;
7. servir le tout sur **`thermique.patrimoineaucarre.com`**, avec **le même compte** que
   `patrimoineaucarre.com`.

Jeu d'essai : `Thermique/PLAN EXEMPLE PROJET/` (11 PDF). Référentiel métier : `Thermique/REGLES TH BAT/`
(fascicules Th-Bât parois opaques, parois vitrées, ponts thermiques).

## 2. Ce qui existe déjà dans Po2 (vérifié)

| Sujet | Constat | Réutilisation |
|---|---|---|
| Plans, métrés, DXF, IFC | **Rien.** Les résultats de recherche sur `services/`, `models/`, `api/routes/`, `pages/`, `components/` sont des faux positifs (« paramètre », CPE « thermique »). | Module **neuf** |
| Comptes utilisateurs | Table `users`, JWT HS256 (`app/services/auth.py`, `app/core/security.py`), `POST /api/auth/login` | **Tel quel** : même table, même mot de passe |
| Session côté navigateur | Jeton en `localStorage` (`patrimoineop_access_token`, `providers/AuthProvider.tsx`) | Le `localStorage` est **propre à chaque sous-domaine** : il faudra se connecter une fois sur `thermique.*`, **avec les mêmes identifiants** |
| Garde d'accès | Caddy `forward_auth` → `/api/internal/basic-auth` sur tout le front (fenêtre d'identification du navigateur, mêmes identifiants Po2) | Reproduire sur le sous-domaine |
| Sous-domaines | Caddy en sert déjà deux : `staging.*` et `ligue1.*` (`saas/infra/caddy/Caddyfile`) | Ajouter un bloc `thermique.*`. **Attention** : `ligue1` a **ses propres comptes**, c'est le contre-modèle ici |
| DNS | `thermique.patrimoineaucarre.com` **n'existe pas** (pas d'enregistrement générique : un nom au hasard ne résout pas). `ligue1` → `135.125.152.112` | **Action utilisateur** : créer l'enregistrement A chez le registrar |
| Base de données | `postgis/postgis:16-3.4` en prod | Stocker les murs en **géométrie native** (longueurs, intersections, superpositions en SQL) |
| Stockage de fichiers | Motif `invoice_storage_dir` + volume Docker `invoice_data` | Même motif, volume dédié aux plans |
| Bibliothèques backend | `pypdf 5.4`, `pdfplumber 0.11.9`, `pdf2image`, `Pillow` déjà dans `requirements.txt` | Suffisant pour l'extraction ; pas de nouvelle dépendance lourde en v1 |
| Patrimoine | `Building` / `Site` / `Local` | Rattachement **optionnel** d'un projet thermique à un bâtiment (Q2) |
| Front | React + Vite, `src/design-system/` | Réutiliser jetons et composants |

## 3. Les plans d'essai (mesuré)

**Projet** : Médiathèque intercommunale de Frontignan-La Peyrade, lot E1, ZAC des Pielles —
dossier PC, février 2012, échelle **1/100**, format **A1** (594 × 841 mm).

| Planche | Nature | Segments (ordre de grandeur) |
|---|---|---|
| PC01 plan masse | plan masse | 180 000 lignes + 81 000 courbes |
| PC02 à PC06 niveaux −1, 0, 1, 2, 3 | **plans** | 5 000 à 225 000 |
| PC07 toiture | plan de toiture | 80 000 |
| PC08, PC09 élévations | **façades** | 18 000 |
| PC10, PC11 coupes AB, CD | **coupes** | **400 000 à 440 000** |

Caractéristiques techniques, identiques sur les 11 fichiers :

- **100 % vectoriel** (sortie CAO imprimée par PDFCreator / Ghostscript 9.04). Les plans de niveau
  ne contiennent aucune image scannée.
- **Aucune police, aucun texte** : tous les textes (cotes, noms de pièces, cartouche) sont
  **dessinés en traits**. On ne peut donc pas lire l'échelle ou une cote automatiquement sans OCR.
- **Aucun calque** : les calques CAO (murs, cloisons, mobilier…) ont été **aplatis** à l'impression.
- La plupart des traits ont été convertis en **surfaces remplies** (`f*`) ; seuls les traits
  structurants restent des traits (`S`).
- Le dessin est **tourné de 90°** dans la feuille (à redresser à l'affichage).
- Une **trame d'axes** (A…Q, 1…15 avec primes) figure sur les plans de niveau : ce sont des
  **points de calage naturels** entre niveaux.
- Les **traits de coupe** A, C, D sont repérés en bord de plan : on peut relier une coupe à sa
  position sur le plan.

## 4. Preuve de faisabilité : détection des murs (plan niveau 0)

Prototype : `docs/thermique/proto_detection_murs.py` (lecture directe du flux PDF avec les
transformations de coordonnées, sans bibliothèque lourde). Résultat :
`docs/thermique/preuve_detection_murs_niveau0.png` (murs détectés en rouge sur le plan en gris).

| Mesure | Valeur |
|---|---|
| Segments lus sur la planche | 225 018 |
| Épaisseurs de trait présentes (pt) | 0,12 · 0,16 · 0,24 · 0,36 · 0,48 · **0,96 · 1,56** |
| Segments retenus (trait ≥ 0,9 pt, zone utile hors cadre et cartouche) | **550** |
| Emprise des murs détectés, convertie à 1/100 | **31,82 m × 33,13 m** |
| Cotes imprimées sur le plan | **31.82** et **33.13** → correspondance exacte |
| Longueur cumulée des faces de murs | 623 m (≈ 311 m de murs, 2 faces par mur, brut) |

Ce qu'on en tire :

1. **La convention de plume CAO porte l'information** : les éléments coupés (murs) sont dessinés en
   trait épais, le reste (mobilier, cotes, textes, trame, hachures) en trait fin. Un simple filtre
   d'épaisseur isole le squelette des murs : façade ouest en redans, noyaux, murs sud, poteaux.
2. **L'échelle est fiable dès qu'elle est déclarée** : 1 pt PDF = 0,3528 mm papier, soit 3,528 cm
   réels à 1/100. Vérifié à la cote près.
3. **Fausse piste écartée** : les segments à 45° ne sont **pas** des hachures de murs, ce sont les
   lettres des textes vectorisés.

Limites constatées (à traiter dans le moteur, pas bloquantes) :

- les **poteaux** ressortent comme des petits rectangles → à classer « poteau », pas « mur » ;
- les **vitrages et murs-rideaux** (façade est, entre les trumeaux nord) sont en trait fin, donc
  non retenus comme murs : c'est correct, mais il faut les capter comme **parois vitrées** pour
  l'enveloppe ;
- les **cloisons** fines ne sont pas captées (sans enjeu thermique, sauf si porteuses) ;
- quelques traits épais ne sont pas des murs (paroi courbe des sanitaires, garde-corps) →
  **correction manuelle** indispensable ;
- la lecture brute prend 20 à 40 s pour un plan de niveau et bien plus pour une coupe (≈ 650 000
  segments) → traitement **en tâche de fond**, résultat mis en cache.

Le filtre par épaisseur dépend du dessinateur : les seuils doivent être **calibrés par planche**
(histogramme des épaisseurs affiché, seuil ajustable), pas codés en dur.

## 5. Chaîne technique proposée

```
PDF importé ─► 1 planche par page ─► nature (plan / coupe / façade / plan masse), suggérée par le nom, validée
            ─► échelle déclarée (1/100) + contrôle par une cote (2 clics + valeur)
            ─► extraction vectorielle (tâche de fond, cache JSON)
            ─► murs : faces épaisses → appariement des faces parallèles → axe + épaisseur
                      poteaux = petits contours fermés isolés ; ouvertures = coupures alignées
            ─► enveloppe : contour extérieur de l'union murs + vitrages → murs extérieurs
            ─► calage : même point (croisement d'axes) sur chaque niveau + 2e point pour la rotation
            ─► porteurs intérieurs : épaisseur ≥ seuil ET mur superposé d'un niveau à l'autre
            ─► coupes : hauteurs d'étage, épaisseurs de plancher, acrotères
            ─► métré : surfaces de parois par orientation + linéaires de ponts thermiques (Th-Bât)
```

- **Affichage** : ~~rendu du PDF dans le navigateur (pdf.js)~~ écarté après mesure (2026-09-11) :
  pdf.js met 10 s à dessiner le niveau 0 et 46,8 s la coupe AB, à chaque zoom. Retenu : rendu
  **pdfium côté serveur en tuiles d'images** (coupe AB affichée en 0,49 s), avec un calque
  interactif par-dessus (mesures, puis murs à l'étape 2). Voir `metre-thermique-decisions.md`.
- **Point de calage et porteurs** : la superposition des niveaux sert deux fois — continuité des
  linéaires de façade **et** critère « porteur » (un mur qui se retrouve au même endroit à chaque
  étage porte).
- **Coupes** : elles ne servent pas à détecter les murs, elles donnent les **hauteurs**, sans
  lesquelles on ne peut pas passer des longueurs de plan aux surfaces de parois ni aux linéaires
  verticaux (angles, refends).
- **Sous-domaine** : bloc Caddy `thermique.*` → `/api/*` vers le **même backend** (routes
  `/api/thermique/*`, mêmes comptes, même JWT) ; le reste vers le front. Détail en Q4-Q6.

## 6. Ce qui n'est PAS couvert par la preuve

- les **plans scannés** (image) : la détection vectorielle ne s'applique pas → tracé manuel assisté
  en v1 (Q3) ;
- les fichiers **DWG/DXF** : ce serait une meilleure source (calques intacts) mais aucun fichier
  d'essai (Q3) ;
- les **coupes** : non prototypées (650 000 segments, extraction des niveaux à valider) ;
- la **correspondance fine avec les règles Th-Bât** (typologie des liaisons) : à cadrer avec
  l'utilisateur (Q7, Q8).
