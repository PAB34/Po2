# Po2 — Index du vault Obsidian

> Vault partagé entre toutes les IA qui interviennent sur le projet **PatrimoineOp** / Po2.
> Toute IA qui commence une session **lit d'abord ce fichier**, puis enchaîne sur les fichiers cités.
> Toute IA qui finit une session **met à jour** `04 État actuel du dev.md` + crée une note dans `Sessions/`.

## 🗺️ Navigation

### 📌 Démarrer ici (5 min de lecture)
- [[01-Vision-Utilisateur]] — Le but, qui est l'utilisateur, le contexte métier
- [[02-Architecture]] — Stack technique, où vit quoi, conventions de code
- [[05-Conventions-IA]] — **Comment passer la main à une autre IA** ⚠️ Lire avant toute modif

### 📊 État du produit
- [[Backlog]] — Priorites operationnelles, dependances, prochaines actions
- [[03-Roadmap-fonctionnalites]] — Les 13 fonctionnalités cibles (issues du fichier `Fonctionnalités.xlsx`) avec statut fait/en cours/todo
- [[04-Etat-actuel-du-dev]] — Snapshot précis : ce qui tourne en prod, les dernières PRs, les chantiers ouverts
- [[06-Rapport-audit-projet-obsidian-2026-05-19]] — Audit code + Obsidian, dépendances entre tâches, recommandations
- [[07-Environnement-poste-entreprise]] — Contrainte zero installation locale et workflow de validation

### 🧩 Modules métier (1 fichier par grand bloc)
- [[Modules/Patrimoine]] — Inventaire bâtiments, locaux, propriétaire / locataire
- [[Modules/Gestion-technique]] — Équipements CVC, enveloppe, occupation, température
- [[Modules/Energie-Consommation]] — ENEDIS (élec), GRDF (gaz), SUEZ (eau)
- [[Modules/Energie-Facturation]] — Vérification ENGIE, DALKIA, TOTAL, SUEZ
- [[Modules/Energie-BPU]] — Suivi temporel des prix unitaires d'achat
- [[Modules/Energie-Preconisations]] — Calibrage contrat + recommandations puissance
- [[Modules/Energie-TURPE]] — Référentiel TURPE 7 (CRE)

### 📚 Specs historiques
- [[Specs]] — Catalogue des 9 specs `saas/specs/` avec verdict (à jour / partiel / archive)

### 🧠 Décisions durables (ADR)
- [[Decisions/000-format-ADR]] — Pourquoi ce format
- [[Decisions/001-vault-obsidian-versionne-dans-git]]
- [[Decisions/002-bpu-schema-normalise-5-tables]]
- [[Decisions/003-enedis-async-ftp-meme-vps-que-po2]]
- [[Decisions/004-specs-restent-dans-saas-specs]]
- [[Decisions/005-poste-entreprise-zero-install-local]]
- [[Decisions/006-secrets-jamais-en-chat-IA]]
- [[Decisions/007-bpu-schema-on-read-vs-parser]]
- Template : [[Decisions/_template]]

### 📅 Journal des sessions
- [[Sessions/]] — Un fichier par session de travail IA. Le plus récent en haut.
- Template : [[Sessions/_template]]

## 🔁 Workflow IA-à-IA — version courte

```
1. Toute nouvelle IA lit :  00 Index → 04 État actuel → 05 Conventions IA
2. Verifie la contrainte poste entreprise : 07 Environnement poste entreprise
3. Identifie sa tâche dans :  Backlog puis 03 Roadmap (statut "todo" ou "en cours")
4. Met à jour le statut "en cours" dans le backlog + crée fichier Sessions/AAAA-MM-JJ Titre.md
5. À la fin : statut "fait" dans le backlog, dernière section du fichier Session = "Handoff suivant"
6. Si limite de tokens approche : "Handoff suivant" = TODO précis pour l'IA suivante avec contextes
```

Détail complet : [[05-Conventions-IA]].

## 🔗 Liens externes utiles
- Repo GitHub : https://github.com/PAB34/Po2
- Application prod : https://patrimoineaucarre.com
- VPS OVH (Po2 + FTP ENEDIS) : `ubuntu@135.125.152.112` via clé SSH `po2_vps2`
