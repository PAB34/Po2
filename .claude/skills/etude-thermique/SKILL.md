---
name: etude-thermique
description: Mène l'étude thermique d'un niveau à partir de son plan raster (PDF aplati) de bout en bout, en faisant travailler les agents thermicien-plan et thermicien-enveloppe depuis la session Claude Code, sans clé d'API. À utiliser quand l'utilisateur demande d'analyser, de métrer ou d'étudier thermiquement un plan de niveau.
---

# Étude thermique d'un niveau (mode session)

Mode d'emploi complet : `docs/thermique/chaine-analyse-plan-raster.md`. Règles permanentes : pixels seuls (jamais
les vecteurs du PDF), ne jamais remplacer silencieusement l'agent Claude par un autre modèle, répondre en
français, ne rien pousser sur GitHub sans autorisation.

## 1. Rassembler les paramètres

- le plan (chemin du PDF) et la page ;
- le nom court du niveau (R1, R2, RDC…) ;
- le dossier de l'étude (un sous-dossier par niveau y sera créé) ;
- la rotation antihoraire = (360 − rotation de la visionneuse) % 360 ; demander si elle n'est pas connue ;
- un catalogue validé d'un autre niveau ou projet (`<dossier>/<niveau>/enveloppe/catalogue.json`), s'il existe.

## 2. Boucle

Depuis `saas/backend` :

```
python scripts/run_etude_niveau.py "<plan.pdf>" --niveau <N> --sorties "<dossier>" --rotation <R> [--page P] [--catalogue <catalogue.json>]
```

- **Code 3 (en attente d'un agent)** : lire `<dossier>/<N>/A-FAIRE.md`. Il donne l'agent, le fichier de consigne,
  le fichier de schéma et le fichier où enregistrer la réponse.
  1. Lancer l'outil Agent avec `subagent_type` = l'agent indiqué (`thermicien-plan` ou `thermicien-enveloppe`),
     au premier plan (`run_in_background: false`), avec pour prompt : le contenu intégral du fichier de consigne,
     suivi de « Réponds uniquement par un JSON conforme à ce schéma, sans bloc Markdown : » et du contenu du
     fichier de schéma.
  2. Extraire le JSON de la réponse (retirer un éventuel bloc Markdown), vérifier qu'il se lit
     (`python -c "import json,sys; json.load(open(sys.argv[1], encoding='utf-8'))" <fichier>`) et l'enregistrer
     tel quel dans le fichier de réponse indiqué. Ne rien inventer ni corriger dans la réponse de l'agent.
  3. Relancer la même commande. Répéter jusqu'au code 0.
- **Code 0** : l'étude est terminée. Lire `A-FAIRE.md` (composants à confirmer, angles à revoir, demandes à
  formuler, contrôle par l'image) et le présenter à l'utilisateur ; lui envoyer `enveloppe.pieces.png`,
  `enveloppe/catalogue.png` et `enveloppe/controle-image.png`.
- **Code 1** : lire l'erreur (et `journal.json`), la signaler en clair ; ne pas contourner.

Informer l'utilisateur à chaque étape (passe globale, guide, lot K sur N, restitution). Un lot du parcours prend
plusieurs minutes.

## 3. Mode autonome (optionnel)

`--mode cli` fait appeler Claude Code en ligne de commande par le script lui-même (abonnement Claude de
l'utilisateur, pas de clé d'API) ; il faut que la commande `claude` du poste soit connectée. Le mode session
ci-dessus n'en a pas besoin.
