# Essai : R+2 en effort xhigh, Opus 5.5 puis Fable 5.1

Consigne pour une **nouvelle** session Claude Code cloud sur la branche `essai/r2-cloud`. Réponds en français et
exécute tout jusqu'au bout, sans demander de confirmation. Les règles de `docs/thermique/essai-R2-cloud.md`
s'appliquent (mode session, pixels seuls, une passe par étape, sauvegarde au fil de l'eau), avec les
différences ci-dessous.

## Ce qui change

- `.claude/agents/thermicien-plan.md` et `thermicien-enveloppe.md` portent `effort: xhigh` (déjà commité). En
  session, Claude Code ne relit pas les agents après une modification : c'est pour cela qu'il faut une nouvelle
  session.
- **Avant de lancer quoi que ce soit**, vérifie sur un premier appel que la trace
  (`~/.claude/projects/*/*/subagents/agent-*.jsonl`) montre `"effort":"xhigh"`. Sinon, arrête tout et écris la
  raison dans `ARRET.md` du dossier de sortie.
- Deux passes complètes, chacune dans son dossier :
  1. `sorties-opus55-xhigh` : outil Agent sans paramètre `model` ; modèle attendu `claude-opus-5-5`.
  2. `sorties-fable51-xhigh` : outil Agent avec `model: "fable"` ; modèle attendu `claude-fable-5-1`.
  Les deux chaînes peuvent avancer en parallèle.
- Commande, depuis `saas/backend` (remplacer `<dossier>`) :
  `python scripts/run_etude_niveau.py ../../essais/R2-cloud/PC05-FRONT-NIVEAU2.pdf --niveau R2 --sorties ../../essais/R2-cloud/<dossier> --rotation 90 --catalogue ../../essais/R2-cloud/catalogue-R1.json`
- Dans chaque `MODELES.md` (le tableau est déjà créé), note pour chaque appel : l'étape, l'agent, le modèle,
  l'effort et la durée.
- Mise en route : `pip install -r requirements.txt` échoue sur `scipy==1.18.0` (Python 3.11). Installe le
  fichier sans la ligne scipy, puis `pip install scipy`.

## À la fin : `essais/R2-cloud/RESULTAT-xhigh.md`

Reprends le tableau de `sorties/RESULTAT.md` avec quatre colonnes : R+2 Opus 4.7, R+2 Opus 5.5 medium
(`sorties/`), R+2 Opus 5.5 xhigh et R+2 Fable 5.1 xhigh, plus le R+1 en référence. Ajoute pour chaque colonne le
coût estimé au tarif API, calculé à partir de l'usage des traces. Tarifs par million de jetons : Opus 5.5 à 4 $
en entrée, 20 $ en sortie et 0,20 $ en lecture de cache ; Fable 5.1 à 10 $ en entrée et 50 $ en sortie. Indique
les tarifs d'écriture en cache retenus. Commite, pousse, puis remets `effort` à son état initial dans les agents
(supprime la ligne) et commite ce retour.
