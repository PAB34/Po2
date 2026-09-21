# 2026-09-21 — Pièces avant composants

> IA : Codex GPT-5
> Durée approximative : 1 h
> Précédente session : `[[Sessions/2026-09-18 — Contours de pièces éditables]]`

## 🎯 Objectif de la session

Permettre au thermicien de définir les pièces avant toute identification des portes et menuiseries,
puis rattacher localement les composants graphiques qui longent chaque contour. Corriger également
l'impossibilité constatée de déplacer les sommets d'une pièce existante.

## ✅ Ce qui a été fait

### Parcours pièce d'abord

- Ajout d'une création de pièce par polygone, indépendante des calques désignés.
- Si aucun calque n'existe, le premier clic hors d'une pièce commence directement le tracé manuel.
- Après un échec de détection assistée, le point cliqué peut devenir le premier sommet du tracé.
- La détection fondée sur les limites connues reste disponible comme aide optionnelle.
- Les familles graphiques bordantes continuent d'être relevées avant qualification ; un test de service
  confirme qu'une famille sans nature est déjà rattachée au contour.

### Édition des sommets

- La tolérance de prise est désormais exprimée en pixels écran puis convertie selon le zoom.
- Le glisser d'un sommet et les clics d'ajout/retrait restent donc alignés sur les poignées visibles.

### Validation

- `pytest -q -p no:cacheprovider saas/backend/tests/test_thermique_pieces.py saas/backend/tests/test_thermique_composants.py` : 9 tests réussis.
- `npm test -- --run src/thermique/metre.test.ts` : 5 tests réussis.
- `npm run build` : bundle de production construit (826 modules).
- Import FastAPI : route `/api/thermique/sheets/{sheet_id}/pieces/tracer` présente.

## 🚧 Ce qui reste à faire / handoff

### Priorité 1 — Validation métier sur le vrai R+1

- Tracer une pièce sans passer par Calques, enregistrer, déplacer plusieurs sommets à différents zooms,
  puis vérifier la liste des familles bordantes.
- La détection automatique conserve ses limites connues sur les façades ouvertes ; le tracé manuel est
  désormais le chemin fiable qui ne bloque plus le métré.

## 📝 Notes & décisions

- Décisions durables consignées dans `thermique/contours-pieces-decisions.md`, section du 2026-09-21.
- Le moteur suit désormais explicitement l'ordre : géométrie de la pièce → composants bordants →
  qualification réutilisable par signature.

## 🔁 Pour la prochaine IA — entrée en matière

```text
J'ai lu :
- docs/00-Index.md
- docs/07-Environnement-poste-entreprise.md
- docs/04-Etat-actuel-du-dev.md
- docs/Sessions/2026-09-21 — Pièces avant composants.md

Je sais que le poste utilisateur est verrouillé entreprise : je ne demanderai aucune installation locale.
Je comprends que la priorité 1 est la validation métier du parcours « pièce d'abord » sur le vrai R+1.
Je propose de commencer par tracer une pièce sans calques puis de vérifier ses sommets et ses composants bordants.

OK pour partir là-dessus ?
```
