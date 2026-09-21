# 2026-09-21 — Analyse IA visuelle du R+1

> IA : GPT-5 / Codex
> Durée approximative : 2 h
> Précédente session : `[[Sessions/2026-09-18 — Contours de pièces éditables]]`

## 🎯 Objectif de la session

Reprendre le MVP thermique sur le R+1 avec une analyse IA du plan rendu en image, sans utiliser les vecteurs
PDF, afin de proposer tous les composants du bâtiment avant la détection des pièces.

## ✅ Ce qui a été fait

### Chantier thermique — inventaire visuel des composants

- Commit `eb72978a` : moteur IA raster, contrat API, projection et édition des objets.
- Audit du bouton `Analyser le plan` existant : il appelait encore le pipeline vectoriel objets -> pièces ->
  enveloppe -> menuiseries.
- Nouveau service raster-only `app/services/thermique_vision.py` : vue globale + six tuiles, appel multimodal,
  JSON Schema strict, confiance et conversion des coordonnées vers le repère PDF.
- Nouvelles routes d'analyse, modification, ajout et suppression d'objets.
- Écran `/analyse` remplacé par une projection colorée des composants avec légende, sélection directe,
  correction de chaque point et validation des objets douteux.
- Taxonomie complétée avec poteaux et garde-corps.
- Tests ciblés : 17 tests backend réussis (dont démarrage API) ; build frontend réussi.
- Fichiers principaux : `saas/backend/app/services/thermique_vision.py`,
  `saas/frontend/src/thermique/pages/AutoZoningPage.tsx`, `docs/thermique/analyse-ia-visuelle-r1-decisions.md`.

## 🛠️ Outils / dépendances découverts ou installés

- Aucune dépendance ajoutée : Pillow et httpx sont déjà présents.
- Le premier adaptateur suit l'API Responses avec entrées image et sortie JSON Schema stricte.

## 🚧 Ce qui reste à faire / handoff

### Priorité 1 — Recette réelle du R+1

- **Problème** : aucune clé de vision n'est configurée dans l'environnement de travail ; l'appel réel n'a donc
  pas encore produit l'inventaire du R+1.
- **Solution proposée** : ajouter `THERMIQUE_VISION_API_KEY` au secret serveur, déployer la branche sur staging,
  lancer le R+1 puis mesurer faux positifs, faux négatifs et distance des points aux composants réels.
- **Fichiers cibles** : `saas/.env.example`, `saas/backend/app/core/config.py`,
  `saas/backend/app/services/thermique_vision.py`.
- **Commandes pour reprendre** : tests ciblés puis `npm run build`; la clé ne doit jamais être écrite dans Git
  ou dans la conversation.
- **Piège connu** : ne pas réintroduire `traits.py`, `calques.py` ou `reconnaissance.py` dans le score de cette
  piste. Un recalage algorithmique ultérieur doit travailler sur les pixels raster seulement.

### Priorité 2 — Évaluation multi-projets

- Faire valider le R+1 par le thermicien et conserver cette version comme vérité terrain.
- Ajouter au moins trois conventions graphiques différentes avant de régler les seuils de confiance.
- Migrer les objets en base seulement lorsque le contrat géométrique est stabilisé.

### Côté utilisateur — Pending validations externes

- Autoriser/configurer une clé API de vision côté serveur ; ne jamais la transmettre dans le chat.

## 📝 Notes & décisions

- `[[Decisions/015-analyse-thermique-ia-raster]]` : la nouvelle analyse ignore les vecteurs PDF.
- Décisions de détail : `[[thermique/analyse-ia-visuelle-r1-decisions]]`.

## 🔁 Pour la prochaine IA — entrée en matière

```
J'ai lu :
- docs/00-Index.md
- docs/07-Environnement-poste-entreprise.md
- docs/04-Etat-actuel-du-dev.md
- docs/Sessions/2026-09-21 — Analyse IA visuelle du R+1.md

Je sais que le poste utilisateur est verrouille entreprise : je ne demanderai aucune installation locale.
Je comprends que la priorité 1 est : configurer le secret serveur puis faire la recette réelle du R+1.
Je propose de commencer par : déployer la branche sur staging et lancer une analyse de la planche R+1.

OK pour partir là-dessus ?
```
