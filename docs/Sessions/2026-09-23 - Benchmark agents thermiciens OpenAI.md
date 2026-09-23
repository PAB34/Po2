# 2026-09-23 — Benchmark agents thermiciens OpenAI

> IA : Codex avec sous-agents OpenAI
> Durée approximative : 2 h
> Précédente session : `[[Sessions/2026-09-22 - Espace thermicien lot E2]]`

## 🎯 Objectif de la session

Tester, sans API et sans vecteurs PDF, des agents OpenAI équivalents aux agents Claude Code de lecture de plan,
puis comparer objectivement leurs sorties raster sur le R+1 de la médiathèque.

## ✅ Ce qui a été fait

### Agents OpenAI et comparateur raster

- Commit `3eb0c5e4` : agents de projet `thermicien_plan_openai` et `thermicien_enveloppe_openai` en lecture seule.
- Comparateur neutre : contrat JSON strict, appariement par catégorie, IoU, qualité des pièces, divergences et
  projection sur le plan avec légende.
- Tests : **130 tests thermiques passés**, dont 7 nouveaux tests du comparateur.
- Aucun package installé, aucune API appelée, aucun secret saisi, aucun push ni déploiement.

### Pilote aveugle R+1

- Trois répétitions de base : 89, 116 et 78 objets ; aucune erreur JSON.
- IoU des pièces face à Claude : 85,0 %, 67,7 % et 77,9 %.
- IoU moyen des pièces entre répétitions OpenAI : 73,3 %.
- Le run 02 est mal recalé malgré 88,8 % de confiance déclarée : la confiance de l'agent ne doit jamais être le
  seul filtre.
- Run 04 avec transformation affine et contrôle global : meilleure précision géométrique (66,3 %), mais couverture
  des pièces à 44,3 % car le grand plateau ouvert est volontairement omis.
- Synthèse et projections :
  `C:\Users\pa.borja\Documents\Codex\2026-09-18\tu\outputs\benchmark_agents\R1\synthese.md`.

## 🚧 Ce qui reste à faire / handoff

### Priorité 1 — Séparer couverture physique et frontières fonctionnelles

- **Problème** : l'agent doit aujourd'hui choisir entre inventer des séparations sur les plateaux ouverts ou omettre
  une partie de la surface.
- **Solution proposée** : produire d'abord une partition physique complète contrôlée par le raster, puis superposer des
  frontières fonctionnelles IA marquées `à_recaler` quand aucune paroi ne les matérialise.
- **Fichiers cibles** : `saas/backend/app/services/thermique_claude_agent.py`, contrat d'étude E2/E3 et
  `docs/thermique/comparatif-agents-claude-openai.md` décision A6.
- **Piège connu** : le contrat actuel accepte seulement des polygones simples et ne distingue pas pièce physique,
  sous-zone fonctionnelle et vide intérieur.

### Priorité 2 — Garde-fous avant import

- Contrôle raster de couverture de l'emprise intérieure et de débordement vers axes/cartouche.
- Rejet si polygone invalide ou chevauchement de pièces supérieur à 2 %.
- Accord multi-run ou validation thermicien avant promotion d'une sortie.
- Comparer ensuite `thermicien_enveloppe_openai` lot par lot ; sa définition est prête mais son benchmark n'a pas été
  lancé pendant cette session.

### Commandes pour reprendre

Depuis `saas/backend` :

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
$env:DATABASE_URL='sqlite:///./test.db'
python -m pytest tests -k thermique -p no:cacheprovider

python scripts/compare_thermicien_agents.py `
  --reference "<sortie-Claude.raw.json>" `
  --candidate "<sortie-OpenAI.raw.json>" `
  --background "<overview.jpg>" `
  --output-dir "<dossier-comparaison>"
```

## 📝 Notes & décisions

- Claude Code est une référence d'appariement, jamais une vérité terrain.
- JSON valide et confiance élevée ne prouvent pas la justesse spatiale.
- La projection visuelle et les contrôles algorithmiques sont obligatoires.
- Décisions détaillées : `[[thermique/comparatif-agents-claude-openai]]`.
- Branche locale en avance de quatre commits après cette session ; aucun push sans accord explicite de l'utilisateur.

## 🔁 Pour la prochaine IA — entrée en matière

```text
J'ai lu :
- docs/00-Index.md
- docs/07-Environnement-poste-entreprise.md
- docs/04-Etat-actuel-du-dev.md
- docs/Sessions/2026-09-23 - Benchmark agents thermiciens OpenAI.md

Je sais que les quatre runs OpenAI du R+1 sont comparés et que le prompt seul ne garantit ni complétude ni recalage.
Je comprends que la priorité 1 est de séparer couverture physique complète et frontières fonctionnelles proposées,
puis de les contrôler sur le raster avant import E2/E3.
Je ne pousserai rien sans accord explicite.
```
