# En attente de l'agent `thermicien-plan` (passe-globale)

1. Lancer l'agent `thermicien-plan` avec, pour consigne, le contenu de `/home/user/Po2/essais/R2-cloud/sorties-fable51-xhigh/R2/consigne-passe-globale.md`.
2. Sa réponse doit être un JSON conforme à `/home/user/Po2/essais/R2-cloud/sorties-fable51-xhigh/R2/schema-passe-globale.json` ; l'enregistrer telle quelle dans
   `/home/user/Po2/essais/R2-cloud/sorties-fable51-xhigh/R2/passe-globale.reponse.json`.
3. Relancer (depuis `saas/backend`) :

```
python scripts/run_etude_niveau.py "/home/user/Po2/essais/R2-cloud/PC05-FRONT-NIVEAU2.pdf" --niveau R2 --sorties "/home/user/Po2/essais/R2-cloud/sorties-fable51-xhigh" --rotation 90 --page 1
```
