"""Relais local : vide la file d'analyse du site en faisant travailler Claude Code sur ce poste (D96).

Le serveur ne peut pas lancer un programme chez vous. Il tient la file ; ce relais la vide :

    python scripts/relais_thermique.py

Pour chaque niveau, il télécharge le plan, lance ``run_etude_niveau.py --mode cli`` — qui fait travailler
les agents avec **votre** abonnement Claude, sans clé d'API — puis renvoie l'étude au site.

Il traite un niveau à la fois, du plus bas au plus haut, en passant le catalogue appris d'un niveau au
suivant : c'est ce qui donne aux composants le même identifiant dans tout le bâtiment.

Il s'arrête de lui-même, sans rien casser, quand une session a expiré ; il vous dit alors quoi relancer.
Aucun mot de passe n'est écrit sur le disque : seul le jeton de session l'est, dans votre dossier
personnel, jamais dans le dépôt.
"""
from __future__ import annotations

import argparse
import getpass
import json
import subprocess
import sys
from pathlib import Path

import requests

SCRIPTS = Path(__file__).resolve().parent
CHAINE = SCRIPTS / "run_etude_niveau.py"
REGLAGES = Path.home() / ".thermique-relais.json"
SITE_PAR_DEFAUT = "https://thermique.patrimoineaucarre.com"

# Codes de sortie de la chaîne (voir l'en-tête de run_etude_niveau.py).
CHAINE_FINI = 0
CHAINE_ERREUR = 1
CHAINE_EN_ATTENTE = 3

# Ce que dit Claude Code quand la session du poste a expiré. D98 : ce n'est pas un échec d'analyse.
SESSION_EXPIREE = ("oauth access token is invalid", "failed to authenticate")


class Arret(Exception):
    """Ce qui doit arrêter le relais au lieu de faire échouer les niveaux un par un."""


class Site:
    """Le site, vu du poste : jeton de session, reconnexion, et les routes de la file."""

    def __init__(self, url: str, jeton: str | None) -> None:
        self.url = url.rstrip("/")
        self.jeton = jeton

    def _entetes(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.jeton}"} if self.jeton else {}

    def _appel(self, methode: str, chemin: str, **kwargs) -> requests.Response:
        reponse = requests.request(
            methode, f"{self.url}/api{chemin}", headers=self._entetes(), timeout=120, **kwargs
        )
        if reponse.status_code == 401:
            raise Arret("votre session sur le site a expiré : relancez le relais pour vous reconnecter")
        if reponse.status_code >= 400:
            raise RuntimeError(f"{methode} {chemin} → {reponse.status_code} {reponse.text[:300]}")
        return reponse

    def connecter(self) -> str:
        """Demande les identifiants dans ce terminal (Q2 = a) et garde le jeton, pas le mot de passe."""
        print(f"Connexion à {self.url}")
        courriel = input("  courriel : ").strip()
        motdepasse = getpass.getpass("  mot de passe (invisible) : ")
        reponse = requests.post(
            f"{self.url}/api/auth/login", json={"email": courriel, "password": motdepasse}, timeout=60
        )
        if reponse.status_code == 401:
            raise Arret("identifiants refusés par le site")
        reponse.raise_for_status()
        self.jeton = reponse.json()["access_token"]
        return self.jeton

    def file(self) -> list[dict]:
        return self._appel("GET", "/thermique/travaux").json()

    def prendre(self, travail_id: int) -> dict:
        return self._appel("POST", f"/thermique/travaux/{travail_id}/prendre").json()

    def plan(self, document_id: int, destination: Path) -> Path:
        reponse = self._appel("GET", f"/thermique/documents/{document_id}/file", stream=True)
        destination.write_bytes(reponse.content)
        return destination

    def rendre(self, travail_id: int, etude: Path) -> None:
        with etude.open("rb") as fichier:
            self._appel(
                "POST",
                f"/thermique/travaux/{travail_id}/rendre",
                files={"fichier": (etude.name, fichier, "application/json")},
            )

    def reporter(self, travail_id: int, message: str) -> None:
        self._appel("POST", f"/thermique/travaux/{travail_id}/reporter", json={"message": message[:2000]})

    def echec(self, travail_id: int, message: str) -> None:
        self._appel("POST", f"/thermique/travaux/{travail_id}/echec", json={"message": message[:2000]})


def lire_reglages() -> dict:
    if REGLAGES.is_file():
        try:
            return json.loads(REGLAGES.read_text(encoding="utf-8"))
        except ValueError:
            return {}
    return {}


def ecrire_reglages(reglages: dict) -> None:
    REGLAGES.write_text(json.dumps(reglages, ensure_ascii=False, indent=1), encoding="utf-8")
    try:  # Le jeton de session ne regarde que son propriétaire.
        REGLAGES.chmod(0o600)
    except OSError:
        pass


def catalogue_precedent(sorties: Path, project_id: int, dernier_niveau: str | None) -> Path | None:
    """Catalogue validé du niveau précédent du même projet, s'il existe (D95)."""
    if not dernier_niveau:
        return None
    chemin = sorties / str(project_id) / dernier_niveau / "enveloppe" / "catalogue.json"
    return chemin if chemin.is_file() else None


def lancer_la_chaine(plan: Path, consignes: dict, dossier: Path, catalogue: Path | None) -> tuple[int, str]:
    """Lance ``run_etude_niveau.py --mode cli`` et rend son code de sortie et sa sortie écran."""
    commande = [
        sys.executable,
        str(CHAINE),
        str(plan),
        "--niveau",
        consignes["niveau"],
        "--sorties",
        str(dossier),
        "--rotation",
        str(consignes["rotation"]),
        "--page",
        str(consignes["page"]),
        "--mode",
        "cli",
    ]
    if consignes.get("echelle"):
        commande += ["--echelle", str(consignes["echelle"])]
    if catalogue:
        commande += ["--catalogue", str(catalogue)]
    print(f"    {' '.join(commande[1:])}")
    resultat = subprocess.run(commande, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return resultat.returncode, f"{resultat.stdout}\n{resultat.stderr}".strip()


def session_claude_expiree(sortie: str) -> bool:
    bas = sortie.lower()
    return any(marque in bas for marque in SESSION_EXPIREE)


def traiter(site: Site, travail: dict, sorties: Path, dernier_niveau: str | None) -> str | None:
    """Traite un niveau. Rend le nom du niveau s'il est allé au bout, sinon `None`."""
    print(f"\n▶ {travail['label']} (niveau {travail.get('level_label') or '?'})")
    consignes = site.prendre(travail["id"])
    dossier = sorties / str(consignes["project_id"])
    dossier.mkdir(parents=True, exist_ok=True)
    plan = site.plan(consignes["document_id"], dossier / f"plan-{consignes['document_id']}.pdf")

    catalogue = catalogue_precedent(sorties, consignes["project_id"], dernier_niveau)
    if catalogue:
        print(f"    catalogue repris du niveau {dernier_niveau}")
    code, sortie = lancer_la_chaine(plan, consignes, dossier, catalogue)

    if session_claude_expiree(sortie):
        site.reporter(travail["id"], "session Claude expirée sur le poste")
        raise Arret("votre session Claude a expiré : lancez `claude auth login`, puis relancez le relais")
    if code == CHAINE_EN_ATTENTE:
        site.reporter(travail["id"], "la chaîne attend une intervention à la main (voir A-FAIRE.md)")
        print("    en attente d'une intervention : niveau remis dans la file, on passe au suivant")
        return None
    if code != CHAINE_FINI:
        site.echec(travail["id"], sortie[-2000:] or f"la chaîne s'est arrêtée (code {code})")
        print("    échec : le niveau sort de la file, son message est visible sur le site")
        return None

    etude = dossier / consignes["niveau"] / f"etude-{consignes['niveau']}.json"
    if not etude.is_file():
        site.echec(travail["id"], f"la chaîne n'a pas écrit {etude.name}")
        print(f"    échec : {etude.name} est introuvable")
        return None
    site.rendre(travail["id"], etude)
    print(f"    importé sur le site ({etude.stat().st_size // 1024} Ko)")
    return consignes["niveau"]


def parser() -> argparse.ArgumentParser:
    reglages = lire_reglages()
    result = argparse.ArgumentParser(description="Vide la file d'analyse du site en local.")
    result.add_argument("--site", default=reglages.get("site", SITE_PAR_DEFAUT))
    result.add_argument(
        "--sorties",
        type=Path,
        default=Path(reglages["sorties"]) if reglages.get("sorties") else None,
        help="Dossier de travail des études ; demandé une fois puis mémorisé.",
    )
    result.add_argument("--reconnexion", action="store_true", help="Oublier le jeton et se reconnecter.")
    return result


def main() -> int:
    args = parser().parse_args()
    reglages = lire_reglages()
    sorties = args.sorties
    if sorties is None:
        saisi = input("Dossier de travail des études (il sera mémorisé) : ").strip()
        if not saisi:
            print("Aucun dossier : rien à faire.")
            return 1
        sorties = Path(saisi)
    sorties = sorties.expanduser().resolve()
    sorties.mkdir(parents=True, exist_ok=True)

    site = Site(args.site, None if args.reconnexion else reglages.get("jeton"))
    try:
        if site.jeton is None:
            site.connecter()
        try:
            file = site.file()
        except Arret:  # Jeton périmé : on redemande une fois, sans perdre le travail en cours.
            site.connecter()
            file = site.file()
        ecrire_reglages({"site": site.url, "sorties": str(sorties), "jeton": site.jeton})

        # Un niveau laissé « en cours » par une exécution coupée bloquerait la file : on le libère.
        for travail in [t for t in file if t["statut"] == "en_cours"]:
            site.reporter(travail["id"], "repris après une exécution interrompue")
            print(f"« {travail['label']} » était resté en cours : remis dans la file.")
        file = site.file()

        a_faire = [t for t in file if t["statut"] == "en_attente"]
        if not a_faire:
            print("La file est vide : rien à analyser.")
            return 0
        print(f"{len(a_faire)} niveau(x) à analyser, du plus bas au plus haut.")

        dernier_niveau: str | None = None
        for travail in a_faire:
            fini = traiter(site, travail, sorties, dernier_niveau)
            if fini:
                dernier_niveau = fini
        print("\nFile vidée.")
        return 0
    except Arret as raison:
        print(f"\nArrêt : {raison}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\nInterrompu. Le niveau en cours reste marqué « en cours » sur le site.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
