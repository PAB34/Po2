# Modèles et effort réellement utilisés (essai R+2, fable51-xhigh)

Relevé dans la trace `subagents/agent-*.jsonl` de chaque appel.

| Étape | Agent | Modèle | Effort | Durée |
|---|---|---|---|---|
| Passe globale | thermicien-plan | claude-fable-5-1 | xhigh | 1524 s |
| Locaux | thermicien-plan | claude-fable-5-1 | xhigh | 142 s |
| Lot 1 | thermicien-enveloppe | claude-fable-5-1 | xhigh | 1217 s |
| Lot 2 | thermicien-enveloppe | claude-fable-5-1 | xhigh | 983 s |
| Lot 3 (fin en erreur max_output_tokens, JSON complet récupéré) | thermicien-enveloppe | claude-fable-5-1 | xhigh | 4107 s |
| Lot 4 | thermicien-enveloppe | claude-fable-5-1 | xhigh | 1577 s |
| Lot 5 | thermicien-enveloppe | claude-fable-5-1 | xhigh | 1337 s |
