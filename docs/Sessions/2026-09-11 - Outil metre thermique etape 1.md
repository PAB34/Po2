# 2026-09-11 — Outil de métré thermique, étape 1 (socle)

> IA : Claude (Opus 5)
> Précédente session : `[[Sessions/2026-08-21 - ASTECH increment 3 et nouvel export]]`

## 🎯 Objectif de la session

Nouvelle demande de l'utilisateur : un outil en ligne d'assistance aux thermiciens pour les
métrés (import et visualisation de plans et coupes, distinction plan/coupe, point de calage
entre niveaux, détection des murs, murs extérieurs et porteurs), sur
`thermique.patrimoineaucarre.com` avec les comptes Po2. Jeu d'essai : 11 PDF du dossier PC de la
médiathèque de Frontignan (`Thermique/PLAN EXEMPLE PROJET/`, non versionné).

## ✅ Ce qui a été fait

### Audit et faisabilité (avant code)

- Aucun module plan/métré existant dans Po2. Rapport : `docs/thermique/00-audit-existant-faisabilite.md`.
- PDF 100 % vectoriels, sans texte ni calques. Prototype `docs/thermique/proto_detection_murs.py` :
  un filtre d'épaisseur de trait isole les murs du niveau 0 (550 traits sur 225 000), emprise
  **31,82 × 33,13 m = cotes imprimées**. Preuve : `docs/thermique/preuve_detection_murs_niveau0.png`.
- Réponses utilisateur (Q1, Q2, Q3, Q14) : voir `docs/thermique/metre-thermique-decisions.md` §4.

### Étape 1 — PR #178, mergée et déployée en prod

- Vérifié par SSH après déploiement : migration `0076`, 3 tables, volume `thermique_data`
  inscriptible, rendu pdfium sous Linux (1,04 s), routes présentes, API sans identifiants en 401,
  nginx sert « Métré thermique » pour `thermique.*` et Po2 pour l'hôte principal. Caddy attend le
  DNS (NXDOMAIN, nouvel essai toutes les 5 min) sans gêner les autres sites.

- Backend : rôles (`core/roles.py`), verrou des comptes externes (`api/deps.py`,
  `routes/internal_auth.py`), service + routes `/api/thermique/*`, rendu en tuiles pdfium
  (`services/thermique_raster.py`), migration `0076` (projets, fichiers, planches).
- Front : second point d'entrée `thermique.html` + `src/thermique/` (connexion, projets, page
  projet, visionneuse en tuiles avec mesure et contrôle d'échelle).
- Infra : bloc Caddy `thermique.*`, volume `thermique_data`, nginx aiguille selon l'hôte.
- Décision durable : ADR [[Decisions/013-outil-thermique-comptes-externes-et-tuiles]].

## 🛠️ Outils / dépendances

- `pypdfium2==5.10.1` ajouté à `requirements.txt` (déjà présent sur le poste).
- Essai visuel local : page d'essai non commitée + serveur Vite de la copie de travail.

## 🚧 Ce qui reste à faire / handoff

### Priorité 1 — Étape 2 : murs
- Porter le prototype en service (tâche de fond, cache) : faces épaisses → appariement → axe +
  épaisseur ; poteaux ; ouvertures ; seuil d'épaisseur par planche (histogramme).
- Calque des murs sur la visionneuse (coordonnées PDF, transformation déjà fournie par la fiche
  des tuiles) + correction manuelle + classement extérieur/intérieur.
- Import DXF (`ezdxf`) ; DWG selon Q15.
- **Pièges connus** : les segments à 45° sont des lettres vectorisées, pas des hachures ; les
  vitrages sont en trait fin ; il faut exclure cadre et cartouche.

### Côté utilisateur
- Créer le DNS **A `thermique` → `135.125.152.112`**.
- Trancher Q5-Q11 et Q15-Q17 du fichier de décisions.

## 📝 Notes & décisions

- pdf.js écarté après mesure (46,8 s pour une coupe) au profit de tuiles pdfium (0,49 s).
- Toute nouvelle route Po2 doit dépendre de `get_current_user`, jamais de
  `get_authenticated_user` (ADR 013).

## 🔁 Pour la prochaine IA — entrée en matière

```
Lire docs/thermique/metre-thermique-decisions.md (décisions + questions) puis
docs/thermique/00-audit-existant-faisabilite.md §4-5 (preuve et chaîne technique).
Tâche : étape 2 (murs). Point de départ : docs/thermique/proto_detection_murs.py.
```
