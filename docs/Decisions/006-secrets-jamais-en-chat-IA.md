# 006 — Les secrets ne transitent jamais par la conversation IA

> **Statut** : Accepté
> **Date** : 2026-05-19
> **Décideur(s)** : PAB34 + IA (Claude Sonnet 4.5)
> **Session liée** : [[Sessions/2026-05-19 — Logs diagnostic FTP-ENEDIS]]

## Contexte

Sur les 3 sessions ENEDIS qui ont touché à la configuration du canal asynchrone, **3 secrets différents ont été affichés en clair dans la conversation** :

1. Password FTP `Papacaca0105` (canal historique) — affiché par l'utilisateur dans un message d'illustration
2. Password FTP généré pendant l'install vsftpd — affiché par une IA dans son output `openssl rand`, puis rotaté
3. Password FTP + clé AES actuels (session courante) — partagés par l'utilisateur en réponse à une `AskUserQuestion` pour comparer avec le VPS

Chaque leak nécessite une rotation côté portail ENEDIS et un re-déploiement. C'est :
- Du temps perdu (10 min × 3 = 30 min minimum, plus si ENEDIS a un délai de validation)
- Un risque résiduel (les secrets restent dans l'historique de conversation côté Claude/Anthropic et sur le poste utilisateur)
- Un signal organisationnel mauvais (on doit traiter les secrets comme des données sensibles)

## Décision

**Aucun secret ne doit transiter en clair par la conversation IA**, quel que soit le contexte (illustration, comparaison, configuration, debug).

Patterns autorisés à la place :

1. **Stockage côté serveur** + référence par chemin :
   - `sudo cat /root/.ftp_password_enedis` (sur le VPS, déjà en place)
   - Variables d'environnement chargées depuis `.env` (déjà en place)
2. **Comparaison sans révélation** : hashage avec `md5sum` ou `sha256sum` côté serveur, puis comparaison des hashes
3. **Tests de validité indirects** : hash de longueur, premier/dernier caractère, prefix, ou simplement "MATCH/MISMATCH" sans révéler la valeur
4. **Canaux out-of-band pour transmission ponctuelle** : 1Password Send, mail GPG, SMS, gestionnaire de secrets de l'entreprise

Si une IA a besoin de comparer un secret connu de l'utilisateur avec un secret stocké côté VPS :
- L'IA propose un script qui calcule un hash côté VPS
- L'utilisateur calcule le même hash localement
- Seuls les hashes transitent par le chat

## Conséquences

### Positives
- Pas de rotation forcée à chaque session
- Les conversations IA peuvent être conservées sans risque résiduel
- Procédure cohérente avec les bonnes pratiques DevOps (12-factor, secrets en env, pas en clair)
- Renforce la culture "secrets = données critiques" dans le projet

### Négatives / coûts assumés
- Workflow légèrement plus lourd quand on veut comparer un secret (passe par un hash)
- L'utilisateur doit avoir un outil out-of-band sous la main pour partager ponctuellement un nouveau secret (1Password, etc.)

### Alternatives écartées
- **Vérification "best effort" avec rotation systématique post-session** — coûte 10 min × N rotations + délai ENEDIS, non viable
- **Conversations IA chiffrées de bout en bout** — pas dans la portée de Claude Code actuel, pas une protection contre un user qui partage involontairement un secret
- **Autoriser les secrets en chat mais avec un marquage `<SECRET>...</SECRET>`** — illusion de sécurité, le secret est toujours stocké en clair côté provider

## Procédure de rotation quand un secret a leaké malgré tout

1. **Constater le leak** rapidement dans la session
2. **Ne pas répéter le secret dans les réponses IA** (l'IA ne doit pas l'utiliser comme paramètre visible)
3. **Faire la rotation côté provider du secret** (portail ENEDIS, dashboard OVH, etc.)
4. **Mettre à jour les copies côté VPS** (`.env`, fichiers dédiés)
5. **Redémarrer les services** qui consomment le secret
6. **Vérifier le fonctionnement** post-rotation
7. **Tracer** dans la note de session courante + créer une tâche dans [[Backlog]] avec priorité P0

## Liens

- Session déclenchante : [[Sessions/2026-05-19 — Logs diagnostic FTP-ENEDIS]]
- Tâche backlog : `PO2-SEC-001` dans [[Backlog]]
- Convention de fin de session : [[05-Conventions-IA]] section 5 "Anti-patterns"
