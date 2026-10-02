# Essai : étude du R+2 en session cloud, avec le bon modèle

Consigne pour la session Claude Code **cloud** lancée par le thermicien sur la branche `essai/r2-cloud`.
Réponds en français. Exécute tout, jusqu'au bout, sans demander de confirmation, en suivant les règles ci-dessous.

## Pourquoi cet essai

Le R+1 a été étudié le 2026-09-21/23 avec la chaîne complète (inventaire des composants → pièces recalées →
locaux → façade et côtés sur local non chauffé → découpage pièce par pièce), agents en **claude-opus-5** : 130
objets, 22 pièces. Le R+2 du 2026-10-01 a suivi la même chaîne, mais en mode automatique, et la commande
`claude` du poste a traduit l'alias `opus` par **claude-opus-4-7**. Résultat : 25 objets, 8 pièces, 21
incohérences (`essais/R2-cloud/journal-R2-opus-4-7.json`). **Question de l'essai : la même chaîne avec un
modèle Opus 5 retrouve-t-elle la qualité du R+1 ?**

## Règles (impératives)

1. **Mode session uniquement** : jamais `--mode cli`. C'est toi qui lances les agents avec l'outil Agent.
2. **Modèle** : chaque agent doit tourner sur un modèle **claude-opus-5** (5, 5-5 ou plus récent). Après
   **chaque** appel d'agent, vérifie le modèle réellement utilisé dans sa trace : fichiers
   `~/.claude/projects/*/*/subagents/agent-*.jsonl` (ou `~/.claude/projects/*/subagents/`), le plus récent, champ
   `"model"` des messages. Note-le dans `essais/R2-cloud/sorties/MODELES.md` (étape, agent, modèle, durée). Si
   ce n'est pas un Opus 5 : **arrête tout**, écris la raison dans `essais/R2-cloud/sorties/ARRET.md`, commite et
   pousse.
3. **Ne modifie aucun fichier du dépôt** hors de `essais/R2-cloud/sorties/` : ni le code, ni `.claude/agents/`,
   ni les consignes. Ne corrige ni n'invente rien dans les réponses des agents.
4. **Pixels seuls**, jamais les vecteurs du PDF (la chaîne le fait déjà).
5. **Sobriété** : une seule passe par étape, pas de deuxième tirage. Un agent qui échoue deux fois de suite sur la
   même étape → arrêt (règle 2 pour la façon de s'arrêter).
6. **Sauvegarde au fil de l'eau** : après chaque étape terminée, commite `essais/R2-cloud/sorties/` et pousse sur
   `origin essai/r2-cloud` (jamais sur `main`, jamais de force-push). Ajoute `git add -f` si un fichier est ignoré.

## Mise en route

```bash
cd saas/backend
pip install -r requirements.txt
```

Si l'installation complète échoue, installer au moins : `pypdfium2 Pillow numpy scipy shapely pydantic
sqlalchemy` et ce que réclament les imports du script.

## Exécution

Suis la compétence `.claude/skills/etude-thermique/SKILL.md` (boucle code 3 → agent → réponse → relance),
avec cette commande, depuis `saas/backend` :

```bash
python scripts/run_etude_niveau.py ../../essais/R2-cloud/PC05-FRONT-NIVEAU2.pdf --niveau R2 --sorties ../../essais/R2-cloud/sorties --rotation 90 --catalogue ../../essais/R2-cloud/catalogue-R1.json
```

Étapes attendues : passe globale (`thermicien-plan`), locaux (`thermicien-plan`, consigne courte), guide,
lots de l'enveloppe (`thermicien-enveloppe`, environ 6 lots), restitution, fichier d'étude.

## À la fin : `essais/R2-cloud/sorties/RESULTAT.md`

Un tableau qui compare cet essai au R+2 Opus 4.7 (journal joint) et au R+1 (130 objets, 22 pièces, 24 locaux
dont 5 circulations, 23 composants) :

- objets de la passe globale, par catégorie ; pièces ; locaux finaux dont circulations et non chauffés ;
- pièces recalées et espaces libres ;
- tronçons et périmètre du guide ; nombre de lots ; composants du catalogue à la fin ;
- incohérences du fichier d'étude ;
- modèle et durée de chaque agent (repris de `MODELES.md`).

Puis commite et pousse une dernière fois. N'importe rien sur le site.
