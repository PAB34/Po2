# Conventions IA — handoff inter-IA

> Ce fichier est la **règle du jeu**. Toute IA qui intervient sur Po2 doit le lire avant d'écrire du code.
> Il sert à éviter que deux IA cassent le travail l'une de l'autre, et à garder un fil cohérent malgré les limites de tokens.

## 1. Au démarrage de session

L'IA qui ouvre une nouvelle conversation doit :

1. **Lire dans cet ordre** :
   - [[00-Index]]
   - [[04-Etat-actuel-du-dev]] (snapshot du présent)
   - [[03-Roadmap-fonctionnalites]] (ce qui reste à faire)
   - Le ou les fichiers `Modules/...md` pertinents pour la tâche
2. **Lire la dernière note `Sessions/AAAA-MM-JJ ...md`** — c'est le passing-the-baton de l'IA précédente
3. **Récupérer l'environnement** :
   ```powershell
   # Activer gh CLI (déjà installé en user-scope)
   $env:Path = [Environment]::GetEnvironmentVariable("Path","User") + ";" + [Environment]::GetEnvironmentVariable("Path","Machine")
   $env:GH_TOKEN = (echo "protocol=https`nhost=github.com`n" | git credential fill | Select-String "password=" | ForEach-Object { ($_ -split "=")[1] })
   gh auth status
   ```
4. **Confirmer à l'utilisateur** quelle tâche elle prend (en référence à la roadmap) — pas juste foncer

## 2. Pendant la session

### Règles tooling
- **Lire avant d'écrire** : utiliser Read sur les fichiers à modifier
- **Petits commits cohérents** : 1 commit = 1 idée (pas de mégacommit "feat: tout fait")
- **Suivre le format** : voir [[02-Architecture]] section "Conventions de code"
- **Commit + push systématique** : ne jamais finir une étape sans committer/pousser
- **PR + squash-merge** : pour les changements significatifs, créer une PR via `gh pr create`, attendre CI verte, puis `gh pr merge --squash --delete-branch`

### Règles vault
- **Au moindre changement structurel** (nouvelle table, nouveau module, nouvelle route majeure) → mettre à jour [[03-Roadmap-fonctionnalites]] et le `Modules/`. Ce n'est pas une option.
- **Pas de duplication** : la roadmap fait référence aux modules, les modules font référence à l'architecture. Pas de copier-coller.
- **Liens [[]]** : utiliser les liens Obsidian, pas des chemins relatifs (Obsidian les résout)

## 3. À la fin de session

L'IA qui finit doit **OBLIGATOIREMENT** :

### A. Mettre à jour [[04-Etat-actuel-du-dev]]
- Cocher ce qui est fait dans la roadmap
- Ajouter les nouveaux chantiers ouverts si pertinent
- Mettre à jour la liste des derniers commits

### B. Créer un fichier `Sessions/AAAA-MM-JJ — Titre.md`

**Copier le template** [[Sessions/_template]] et le renommer `AAAA-MM-JJ — Titre court.md`. Le template contient les sections obligatoires : objectif, ce qui a été fait, handoff, notes & décisions, modèle de message pour la prochaine IA.

### C. Si une décision durable a été prise → créer une ADR

Une **décision durable** = un choix de schéma SQL, de pattern, d'outillage ou de convention qui contraindra le futur. Cf. [[Decisions/000-format-ADR]] pour la définition précise.

- Copier [[Decisions/_template]] → renommer `NNN-titre-court.md` (incrémenter le numéro)
- Remplir les 6 sections : statut, contexte, décision, conséquences, alternatives écartées, liens
- Référencer l'ADR depuis la note de session (champ "Notes & décisions")

### D. Commit + push de la mise à jour du vault
```bash
git add docs/
git commit -m "docs: session AAAA-MM-JJ — résumé"
git push
```

## 4. Quand la limite de tokens approche

Si tu sens que tu vas être coupée :

1. **Stop immédiatement** ce que tu codes
2. **Termine proprement** ce qui est commité (jamais de demi-commit)
3. **Écris la section "Handoff" du fichier Session** très précisément :
   - "L'IA suivante doit ouvrir `chemin/du/fichier.py` ligne X et faire Y"
   - "Le test reproduit le bug : `commande exacte`"
   - "Attention : Z ne fonctionne pas comme prévu, voir le commit truc qui le mentionne"
4. **Commit + push** du vault
5. **Dis à l'utilisateur** : "Je dois passer la main, j'ai laissé toutes les infos dans `docs/Sessions/AAAA-MM-JJ ...md`. La prochaine IA peut reprendre à partir de là."

## 5. Anti-patterns à éviter ABSOLUMENT

| ❌ Ne pas faire | ✅ Faire à la place |
|---|---|
| Ignorer le vault et coder direct | Lire au moins `00 Index` + `04 État actuel` avant |
| Recoder un module qui existe déjà | Chercher dans `services/` / `models/` / `routes/` avant de créer |
| Inventer une convention de nommage | Suivre celles documentées dans `02 Architecture` |
| Mettre des emoji dans le code applicatif | Réservés aux docs et aux conversations |
| Faire des force-push sur main | Toujours via PR + squash-merge |
| Skip les hooks (--no-verify) | Investiguer la cause de l'échec |
| Afficher un secret dans la conversation | Le récupérer côté serveur sans l'afficher |
| Oublier le filtre `city_id` sur une query | Tous les modèles métier sont tenant-scoped |
| Inventer un PRM ou une donnée test en BDD prod | Toujours dev en local d'abord |

## 6. Outils à disposition de l'IA

L'environnement de l'utilisateur PAB34 (Windows entreprise) :

- ✅ `git` (avec credentials helper "manager", PAT GitHub stocké)
- ✅ `gh` CLI 2.92.0 (installé en user-scope, pas d'admin requis)
- ✅ `ssh` + clé `~/.ssh/po2_vps2` pour `ubuntu@135.125.152.112`
- ✅ `docker exec` sur les conteneurs prod via SSH
- ✅ `python` (avec pandas/openpyxl installés en --user)
- ❌ pas de `npm` / `node` direct (le build TS se fait en CI ou via Docker)
- ❌ pas d'install de logiciels admin sans le code admin

## 7. Modèle de message d'ouverture pour l'IA suivante

Quand tu reprends à froid, commence ta réponse par :

```
J'ai lu :
- docs/04 État actuel du dev (snapshot du Y-M-D)
- docs/Sessions/<dernière session>
- docs/Modules/<module pertinent>

Je comprends que la tâche en cours est : <description>
Je propose de commencer par : <étape 1>

OK pour partir là-dessus ?
```

Ce préambule évite à l'utilisateur de tout te ré-expliquer.
