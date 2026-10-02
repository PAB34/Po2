# En attente de l'agent `thermicien-enveloppe` (lot-1)

1. Lancer l'agent `thermicien-enveloppe` avec, pour consigne, le contenu de `/home/user/Po2/essais/R2-cloud/sorties-fable51-xhigh/R2/consigne-lot-1.md`.
2. Sa réponse doit être un JSON conforme à `/home/user/Po2/essais/R2-cloud/sorties-fable51-xhigh/R2/schema-lot-1.json` ; l'enregistrer telle quelle dans
   `/home/user/Po2/essais/R2-cloud/sorties-fable51-xhigh/R2/enveloppe/reponse-lot-1.json`.
3. Relancer (depuis `saas/backend`) :

```
python scripts/run_etude_niveau.py "/home/user/Po2/essais/R2-cloud/PC05-FRONT-NIVEAU2.pdf" --niveau R2 --sorties "/home/user/Po2/essais/R2-cloud/sorties-fable51-xhigh" --rotation 90 --page 1
```
