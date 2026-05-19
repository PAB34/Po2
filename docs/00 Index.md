# Po2 — Index du vault Obsidian

> Vault partagé entre toutes les IA qui interviennent sur le projet **PatrimoineOp** / Po2.
> Toute IA qui commence une session **lit d'abord ce fichier**, puis enchaîne sur les fichiers cités.
> Toute IA qui finit une session **met à jour** `04 État actuel du dev.md` + crée une note dans `Sessions/`.

## 🗺️ Navigation

### 📌 Démarrer ici (5 min de lecture)
- [[01 Vision & Utilisateur]] — Le but, qui est l'utilisateur, le contexte métier
- [[02 Architecture]] — Stack technique, où vit quoi, conventions de code
- [[05 Conventions IA]] — **Comment passer la main à une autre IA** ⚠️ Lire avant toute modif

### 📊 État du produit
- [[03 Roadmap fonctionnalités]] — Les 13 fonctionnalités cibles (issues du fichier `Fonctionnalités.xlsx`) avec statut fait/en cours/todo
- [[04 État actuel du dev]] — Snapshot précis : ce qui tourne en prod, les dernières PRs, les chantiers ouverts

### 🧩 Modules métier (1 fichier par grand bloc)
- [[Modules/Patrimoine]] — Inventaire bâtiments, locaux, propriétaire / locataire
- [[Modules/Gestion technique]] — Équipements CVC, enveloppe, occupation, température
- [[Modules/Énergie - Consommation]] — ENEDIS (élec), GRDF (gaz), SUEZ (eau)
- [[Modules/Énergie - Facturation]] — Vérification ENGIE, DALKIA, TOTAL, SUEZ
- [[Modules/Énergie - BPU]] — Suivi temporel des prix unitaires d'achat
- [[Modules/Énergie - Préconisations]] — Calibrage contrat + recommandations puissance
- [[Modules/Énergie - TURPE]] — Référentiel TURPE 7 (CRE)

### 📚 Specs historiques
- [[Specs]] — Catalogue des 9 specs `saas/specs/` avec verdict (à jour / partiel / archive)

### 📅 Journal des sessions
- [[Sessions/]] — Un fichier par session de travail IA. Le plus récent en haut.

## 🔁 Workflow IA-à-IA — version courte

```
1. Toute nouvelle IA lit :  00 Index → 04 État actuel → 05 Conventions IA
2. Identifie sa tâche dans :  03 Roadmap (statut "todo" ou "en cours")
3. Met à jour le statut "en cours" dans la roadmap + crée fichier Sessions/AAAA-MM-JJ Titre.md
4. À la fin : checkbox "fait" dans la roadmap, dernière section du fichier Session = "Handoff suivant"
5. Si limite de tokens approche : "Handoff suivant" = TODO précis pour l'IA suivante avec contextes
```

Détail complet : [[05 Conventions IA]].

## 🔗 Liens externes utiles
- Repo GitHub : https://github.com/PAB34/Po2
- Application prod : https://patrimoineaucarre.com
- VPS OVH (Po2 + FTP ENEDIS) : `ubuntu@135.125.152.112` via clé SSH `po2_vps2`
