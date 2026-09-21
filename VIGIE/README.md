# Vigie Foncier Sète

Carte de présélection de parcelles (réserve foncière, division, densification) —
`https://immobilier.patrimoineaucarre.com`. Projet à part, sans lien avec Po2.
Cadrage et décisions : `docs/immobilier/vigie-foncier-decisions.md`.

## Arborescence

| Chemin | Rôle |
|---|---|
| `sources/` | XML du règlement (fait foi), Excel de classement (qualitatif), cadrage V0.1 |
| `config/familles.yaml` | Familles d'opération par secteur (seul fichier saisi à la main) |
| `config/plu_sete.yaml`, `config/rapport_regles.md` | Matrice PLU **générée** + rapport d'anomalies |
| `pipeline/build_regles.py` | É1 : XML + Excel + familles → matrice |
| `pipeline/build_parcelles.py` | É2 : cadastre + zonage → parcelles enrichies (`web/data/*.geojson.gz`) |
| `web/` | Site statique : carte MapLibre + filtres (tout se calcule dans le navigateur) |
| `Dockerfile`, `nginx.conf` | Conteneur `vigie` (déployé par `saas/infra/docker-compose.prod.yml`) |

## Régénérer les données

```bash
cd VIGIE
python -m pipeline.build_regles            # après modification du XML, de l'Excel ou des familles
python -m pipeline.build_parcelles         # --refresh pour retélécharger cadastre et zonage
python -m pytest tests -p no:cacheprovider
```

Dépendances : `shapely`, `pyproj`, `openpyxl`, `pyyaml`. Seuls les `.geojson.gz` sont versionnés.

## Aperçu local

```bash
python -m http.server 8765 -d VIGIE/web
```

## Déploiement

Push sur `main` (chemin `VIGIE/**`) → workflow `Deploy`. Caddy protège le site par `basic_auth`
(`VIGIE_AUTH_USER`, `VIGIE_AUTH_HASH` dans `saas/.env` du VPS ; hash via `caddy hash-password`).
