# 012 — Auto-validation et sémantique des états de contrôle facture (V1)

> **Statut** : Accepté
> **Date** : 2026-06-29
> **Décideur(s)** : PAB34 + Claude Code
> **Session liée** : journal `[[Archives/Journal-etat-dev-2026]]` (2026-06-29)

## Contexte

Sur `/refonte-v1/factures`, le moteur de contrôle produisait beaucoup de faux signaux (trous de période lors de transitions fournisseur, doublons d'export, lignes fixes sans période), ce qui bloquait des factures saines. Il fallait fixer une sémantique stable, partagée entre l'énergie (`EnergyInvoiceImport`) et le CPE (`CpeFinanceInvoice`), pour distinguer ce qui exige une action humaine de ce qui est neutralisé.

## Décision

1. **Cinq états de contrôle** : OK · Écart · À expliquer (anomalie non résolue) · Bloquée (donnée manquante) · Expliquée (anomalie neutralisée, non bloquante). Une issue `explained` ne compte plus dans les warnings et n'exige aucun contrôle.
2. **Auto-validation** : une facture au contrôle entièrement vert (énergie `control_status == valid` ; CPE aucun contrôle `error` ni `blocked`) ET encore en décision initiale (`to_review` / `a_controler`) passe automatiquement en `approved` / `valide`. Une décision humaine déjà prise (`approved`/`rejected`/`dispute_sent` ; `valide`/`refuse`/`conteste`) n'est **jamais** écrasée. Côté énergie, `decision_by_user_id` reste nul = marqueur « auto ».

## Conséquences

### Positives
- La comptable ne voit que les factures qui demandent une action réelle.
- Sémantique unique énergie + CPE, réutilisable pour les futures tranches (Fluides, etc.).

### Négatives / coûts assumés
- L'auto-validation s'exécute au (re)calcul des contrôles : changer la logique impose de recalculer le stock existant (staging + prod).
- CPE n'a pas de champ décision distinct (`status` sert aux deux) ni de `decision_by_user_id` : l'origine « auto » n'est tracée que par une note.

### Alternatives écartées
- **Reclasser les faux positifs en simples warnings** — garderait du bruit ; on a préféré les neutraliser explicitement (`explained`).
- **Validation toujours manuelle** — volume ingérable pour un portefeuille de centaines de factures saines.

## Liens

- Module / tranche : `[[49-Spec-execution-refonte-Factures-Decisions-V1]]`
- Glossaire métier : `docs/refonte-v1/factures-glossaire-controles.md`
- Code : `app/services/invoice_analysis.py` (`_auto_validate_if_clean`), `app/services/cpe_accounting.py` (`_should_auto_validate_cpe`)
- Commits : `42ca294`, `976da87` · PR #32
