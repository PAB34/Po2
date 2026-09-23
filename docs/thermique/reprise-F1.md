---
read_policy: lire en premier pour reprendre l'outil thermique (point de reprise du 2026-09-23, lot F1)
---

# Reprise — outil thermique, lot F1

## 1. Où on en est

- Dépôt : worktree `C:\Users\pa.borja\Documents\Po2-thermique`, branche `feat/thermique-socle-raster`.
- **En production** (thermique.patrimoineaucarre.com) : jusqu'au commit `365a9055` — espace de travail (E1),
  import d'une étude de niveau (E2), édition pièce par pièce (E3). Migrations 0083 et 0084 appliquées.
- **Commits locaux non poussés** : `812c2405`, `fafcbecc` (décisions E3 bis) et `9e385d2d` (correction de
  l'emprise intérieure). Un push sur `main` déclenche le déploiement : **jamais sans l'accord de l'utilisateur**.
- L'utilisateur a repris un projet propre en production, importé le R+1, et travaillé dessus.

## 2. Ce que l'utilisateur a demandé, et qui est décidé

Tout est dans [parcours-par-niveau-E3bis-decisions.md](parcours-par-niveau-E3bis-decisions.md), décisions
**D66 à D77, toutes validées**. En résumé, le travail se réorganise en étapes par niveau :

| Étape | Contenu |
|---|---|
| 1 | Plans : import, échelle, dénomination, classement |
| 2 | **Analyse** : bouton qui met les niveaux en file, relais local qui lance la chaîne et importe (D76) |
| 3 | **Contours** : reprendre, couper, fusionner — une passe sur le niveau, sans recalcul |
| 4 | **Recalcul** du niveau, automatique en fin de passe et disponible à tout moment |
| 5 | **Éléments** : isoler d'un clic, modifier, exclure avec trace, puis valider le local |

Ordre des lots retenu : **F1 → F0 (relais) → F2 (parcours) → F3 (métrés sur le plan) → F4 (éléments)**.

## 3. Lot F1 — ce qui est fait, ce qui reste

### Fait (commit `9e385d2d`, testé sur le R+1 réel)

- `app/services/thermique_calage_contours.py` : reconstruit le **corps des parois** (du nu extérieur au nu
  intérieur mesuré) et le retire des contours de locaux. Sur le R+1, corrige sept locaux qui mordaient
  réellement dans les murs (escalier encloisonné −4,4 m², locaux techniques −3,8 m²). Fournit aussi
  `liaisons_localisees` (positions des ponts thermiques), **écrite mais pas encore branchée**.
- `thermique_etude_geometrie.emprise_interieure(manifeste, releve)` retranche les murs, et
  `controler_couverture` ignore les bandes de moins de 30 cm (les cloisons, non mesurées).
  **Sur le R+1 : couverture 86,2 % → 92,5 %, et 113 m² signalés en nappe → 31 m² en dix zones réelles.**
  C'est ce défaut que l'utilisateur voyait comme « la limite des pièces ne s'est pas faite au pied de la
  menuiserie » sur toute une façade : la bande rouge dessinait l'épaisseur des murs.

### Reste à faire dans F1

1. **Contrôle de cohérence de fin de chaîne (D77)** — la demande la plus importante de la journée : la chaîne
   doit confronter les deux lectures (contours de `thermicien-plan` contre nus de `thermicien-enveloppe`) et
   écrire ce qu'elle trouve dans `A-FAIRE.md` **et** dans le fichier d'étude. Les six contrôles sont listés
   dans D77. Le défaut corrigé aujourd'hui aurait été détecté par le contrôle n° 1.
2. **Brancher le calage** dans `assembler_etude_niveau` (sur le poste, jamais au serveur — D66), avec
   `contours_cales: true` et le rapport de déplacement par local.
3. **Brancher les liaisons localisées** dans le fichier d'étude (D74), pour que F3 puisse les dessiner.
4. **Remettre le tracé reprojeté des éléments** dans le fichier (D75) : la version 2 ne garde que le relevé
   brut, donc les éléments ne sont plus dessinables. Régression introduite par moi en E3.
5. Passer le contrat en `format_version: 3`, adapter `valider_et_convertir` et les tests.
6. Réassembler `etude-R1.json` en v3 et le faire réimporter par l'utilisateur (l'ancienne étude devient une
   version, rien n'est perdu).

## 4. Ce qu'il faut savoir pour ne pas se tromper

- **Les contours du R+1 sont bons.** Mesuré : 46,6 cm où le mur fait 45, 26,2 cm où le mur-rideau fait 26,
  36,4 cm où la façade fait 33-34. Ne pas repartir sur l'idée d'un défaut de contour : c'était une erreur
  de diagnostic de ma part, corrigée.
- **`batiment_px` suit la face extérieure** du bâtiment et inclut même une partie de la bande d'escalier est,
  que l'utilisateur a tranchée comme **extérieure** le 2026-09-23. Toujours passer par
  `emprise_interieure(manifeste, releve)`.
- **Le relevé d'enveloppe ne mesure que le pourtour** : aucune épaisseur n'est connue pour les cloisons
  intérieures. C'est pour cela que les bandes de moins de 30 cm sont ignorées.
- `reconstruire()` est fidèle : rejouée sans modification sur le R+1, elle redonne exactement les 24 fiches,
  32 composants, 16 raccords et 4 demandes importés. C'est le test de non-régression le plus utile.
- Le recalcul coûte 10 à 15 s, dont 4,4 s dans `thermique_fiches_locaux.fiches` (sondage de tous les côtés de
  tous les locaux). D68 supprime le problème en ne recalculant qu'une fois par passe ; une indexation
  spatiale dans `_sonder` reste possible si besoin.

## 5. Données et commandes

Données réelles, sans relancer aucun agent :

- étude v2 du R+1 : `C:\Users\pa.borja\Documents\Codex\2026-09-18\tu\outputs\complement_R1\etude-R1.v2.json`
- sources d'assemblage : même dossier (`enveloppe.raw.json`, `enveloppe.json`, `enveloppe/controle.json`) et
  l'analyse `...\outputs\claude_agent_R1_locaux.json`
- plan : `C:\Users\pa.borja\Documents\Po2\Thermique\PLAN EXEMPLE PROJET 1\PC04-FRONT-NIVEAU1.pdf`
  (empreinte `e2da3c91d3756be0…`, page 1, rotation visionneuse 270)

```powershell
# tests ciblés (depuis saas/backend)
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; $env:DATABASE_URL='sqlite:///./test.db'
python -m pytest tests -k thermique -p no:cacheprovider
```

```bash
# interface (depuis saas/frontend)
npx tsc -b && npx vitest run src/thermique && npm run build
```

Banc d'essai local complet (base SQLite, vrai PDF, étude importée, uvicorn + vite) :
`…\scratchpad\banc_e3.py` puis `…\scratchpad\serveur_banc.py`. Le site se regarde sur
`http://thermique.localhost:5173/projets/1`.

## 6. Règles de l'utilisateur, à ne pas oublier

- Répondre en **français**, finir chaque tâche par « ce que j'ai fait, en clair » (non technique).
- **Fichier de décisions avant de coder**, questions numérotées, validation avant de commencer.
- **Ne rien pousser sans autorisation explicite** ; un push sur `main` met en production.
- Dépôt partagé avec Codex : `git status` d'abord, `git commit -- <chemins>`, jamais de force-push.
- Jamais de mot de passe, de clé ni de jeton affiché, saisi ou copié.
- Jamais de retour à une détection par les vecteurs du PDF ; pas de clé d'API ; pas d'installation locale.
- Les agents tournent dans Claude Code sur le poste. Ne pas modifier `.claude/agents/thermicien-plan.md`.
