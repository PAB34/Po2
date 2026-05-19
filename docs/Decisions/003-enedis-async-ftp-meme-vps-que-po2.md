# 003 — Pipeline ENEDIS async via FTP hébergé sur le même VPS que Po2

> **Statut** : Accepté
> **Date** : 2026-05-19 (formalisation a posteriori, mise en œuvre antérieure)
> **Décideur(s)** : PAB34 + IA précédente
> **Session liée** : multiples — voir plan `.claude/plans/memoized-forging-taco.md`

## Contexte

Le backfill complet ENEDIS en mode synchrone est infaisable :
- 529 PRM × CDC 2 ans = 55 016 appels API
- ENEDIS limite à 950 appels/h par application
- Soit ~58 h de sync continue → trop fragile, exposé aux 429 et timeouts

L'API ENEDIS async (`commanderPublicationPonctuelle`) permet **1 appel pour 1000 PRM × 3 ans → fichier JSON chiffré déposé sur FTP** quelques minutes à 24h plus tard. Il faut donc un FTP receiver.

Le canal FTP DriveHQ historique est obsolète, et le projet ne dispose que d'**un seul VPS** (OVH `135.125.152.112`, Ubuntu 25.04) qui héberge déjà Po2.

Question : faut-il un VPS dédié pour le FTP receiver, ou monter `vsftpd` sur le même VPS que l'app Po2 ?

## Décision

Monter le FTP receiver **sur le même VPS que Po2** :
- `vsftpd` installé sur 135.125.152.112
- User dédié `enedis_ftp` avec chroot `/srv/ftp/enedis/upload`
- Shell `/usr/sbin/nologin`
- Mode passif ports 40000-40100
- UFW : whitelist stricte des IPs ENEDIS prod (`192.196.114.95`, `163.116.11.145`)
- Mot de passe stocké uniquement dans `/root/.ftp_password_enedis` (chmod 600)

Le backend Po2 (en conteneur Docker) accède au FTP via `FTP_HOST=135.125.152.112` + une règle UFW pour les subnets Docker (172.16.0.0/12).

## Conséquences

### Positives
- **Pas de coût supplémentaire** : 1 VPS au lieu de 2
- **Latence négligeable** : backend Docker ↔ FTP host = même machine
- **Simplicité opérationnelle** : 1 seul serveur à maintenir, monitorer, sauvegarder
- **Sécurité** : whitelist UFW + chroot + nologin shell → surface d'attaque limitée même si compromis

### Négatives / coûts assumés
- **Couplage** : si le VPS tombe, FTP + app tombent ensemble (mais avec 1 seul VPS, c'est déjà le cas pour tout le reste)
- **Saturation possible** : si beaucoup de fichiers ENEDIS arrivent en même temps, le disque doit pouvoir tenir — non observé en pratique
- **OS Ubuntu 25.04** : EOL approchant, réinstallation 24.04 LTS planifiée post-MVP (cf. plan ENEDIS)

### Alternatives écartées
- **VPS dédié au FTP** — Coût supplémentaire, complexité réseau, pour zéro bénéfice tangible à notre échelle
- **Service FTP managé (DriveHQ, etc.)** — Le canal DriveHQ historique justement déclaré obsolète, coût récurrent, dépendance externe
- **S3 / blob storage avec interface FTP** — ENEDIS exige FTP standard, pas d'autre protocole supporté

## Liens

- Plan détaillé : `.claude/plans/memoized-forging-taco.md` (sections setup VPS-2, sécurité)
- Module : [[Modules/Energie-Consommation]] section "ENEDIS Async"
- Service : `saas/backend/app/services/enedis_async.py`
- Modèle : `saas/backend/app/models/enedis_async.py` (`EnedisAsyncJob`)
- Migration : `saas/backend/alembic/versions/0013_add_enedis_async_jobs.py`
- Scheduler : `saas/backend/app/core/scheduler.py` (APScheduler, poll 5 min)
