"""Lecture des coupes par l'agent Claude Code ``thermicien-coupe`` (S5, D181), sans clé d'API.

    python scripts/run_lecture_coupes.py PLAN.pdf --type traits --sorties DOSSIER
    python scripts/run_lecture_coupes.py COUPES.pdf --type coupes --sorties DOSSIER

- ``traits`` : les traits de coupe d'un plan (vue d'ensemble, puis zoom sur chaque sommet) ;
- ``coupes`` : les vues d'une planche (vue d'ensemble), puis chaque coupe lue en tuiles quadrillées.

Écrit ``lecture.json`` dans le dossier, au format que le site attend (``{"traits": [...]}`` ou
``{"vues": [...]}``). ``--reponses DOSSIER`` rejoue des réponses d'agent déjà obtenues (une par étape,
``<etape>.json``) au lieu d'appeler Claude Code : c'est ainsi qu'on mesure sans rien dépenser.

Code de sortie : 0 terminé, 1 erreur.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
BACKEND = SCRIPTS.parent
REPOSITORY = BACKEND.parents[1]
sys.path.insert(0, str(BACKEND))

from app.services import thermique_consignes_coupes as consignes  # noqa: E402
from app.services import thermique_lecture_coupes as lecture  # noqa: E402
from app.services.thermique import ThermiqueError  # noqa: E402
from app.services.thermique_claude_agent import claude_executable, cli_environment  # noqa: E402

AGENT = "thermicien-coupe"


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Lecture des traits de coupe d'un plan ou des vues d'une planche de coupes.")
    result.add_argument("source", type=Path, help="PDF de la planche")
    result.add_argument("--type", choices=("traits", "coupes"), required=True)
    result.add_argument("--page", type=int, default=1)
    result.add_argument("--sorties", type=Path, required=True, help="Dossier de travail de cette planche")
    result.add_argument("--reponses", type=Path, help="Rejoue les réponses d'agent de ce dossier (<etape>.json)")
    result.add_argument("--model", default="opus")
    result.add_argument("--timeout", type=int, default=1800)
    return result


class Agent:
    """Appelle l'agent pour une étape, ou rejoue sa réponse enregistrée ; garde chaque réponse sur disque."""

    def __init__(self, dossier: Path, reponses: Path | None, modele: str, delai: int) -> None:
        self.dossier, self.reponses, self.modele, self.delai = dossier, reponses, modele, delai

    def __call__(self, etape: str, consigne: str, schema: dict) -> dict:
        (self.dossier / f"{etape}.consigne.txt").write_text(consigne, encoding="utf-8")
        if self.reponses is not None:
            return json.loads((self.reponses / f"{etape}.json").read_text(encoding="utf-8"))
        commande = [
            claude_executable(), "--add-dir", str(self.dossier), "-p", consigne,
            "--agent", AGENT, "--model", self.modele, "--output-format", "json",
            "--json-schema", json.dumps(schema, ensure_ascii=False, separators=(",", ":")),
            "--tools", "Read", "--permission-mode", "dontAsk", "--no-session-persistence",
        ]
        try:
            fini = subprocess.run(commande, cwd=REPOSITORY, env=cli_environment(), capture_output=True, text=True,
                                  encoding="utf-8", timeout=self.delai, check=False)
        except subprocess.TimeoutExpired as exc:
            raise ThermiqueError(f"Claude Code n'a pas fini l'étape « {etape} » dans le délai prévu.") from exc
        if fini.returncode != 0:
            raise ThermiqueError(f"Claude Code a interrompu l'étape « {etape} » ({fini.returncode}) : {(fini.stderr or fini.stdout)[-1200:]}")
        enveloppe = json.loads(fini.stdout)
        brut = enveloppe.get("structured_output") or enveloppe.get("result")
        reponse = json.loads(brut) if isinstance(brut, str) else brut
        (self.dossier / f"{etape}.json").write_text(json.dumps(reponse, ensure_ascii=False, indent=1), encoding="utf-8")
        return reponse


def taille_de_page(source: Path, page: int) -> list[float]:
    import pypdfium2 as pdfium

    document = pdfium.PdfDocument(str(source))
    try:
        gauche, bas, droite, haut = document[page].get_mediabox()
    finally:
        document.close()
    return [0.0, 0.0, droite - gauche, haut - bas]


def lire_traits(source: Path, page: int, dossier: Path, agent: Agent) -> dict:
    ensemble = consignes.rendre_quadrille(source, page, taille_de_page(source, page), consignes.PAS_ENSEMBLE_PT, 1600,
                                          dossier / "ensemble.png")
    reperes = agent("traits-ensemble", consignes.consigne_traits_ensemble(ensemble), consignes.schema_traits_ensemble())
    traits = [consignes.trait_de_lecture(t) for t in reperes.get("traits", [])]
    zooms = consignes.points_a_preciser(traits)
    for rang, zoom in enumerate(zooms):
        zoom["image"] = str(consignes.rendre_quadrille(source, page, zoom["cadre"], consignes.PAS_ZOOM_PT, 1200,
                                                       dossier / f"zoom-{rang:02d}-{zoom['trait']}.png"))
    if zooms:
        precis = agent("traits-precis", consignes.consigne_traits_precis(zooms), consignes.schema_traits_precis())
        traits = consignes.appliquer_precisions(traits, zooms, precis)
    return {"traits": lecture.valider_traits(traits)}


def lire_coupes(source: Path, page: int, dossier: Path, agent: Agent) -> dict:
    ensemble = consignes.rendre_quadrille(source, page, taille_de_page(source, page), consignes.PAS_ENSEMBLE_PT, 1600,
                                          dossier / "ensemble.png")
    reperes = agent("vues-ensemble", consignes.consigne_vues_ensemble(ensemble), consignes.schema_vues_ensemble())
    vues = []
    for rang, vue in enumerate(reperes.get("vues", [])):
        if vue["nature"] != "coupe":
            # Façades et détails sont gardés (repérage, S5e) mais pas lus pièce par pièce.
            vues.append(consignes.lecture_de_vue(vue, {"niveaux": [], "pieces": []}))
            continue
        images = [
            consignes.rendre_quadrille(source, page, cadre, consignes.PAS_TUILE_PT, 1400,
                                       dossier / f"vue-{rang:02d}-tuile-{i:02d}.png")
            for i, cadre in enumerate(consignes.tuiles(vue["cadre"]))
        ]
        brut = agent(f"vue-{rang:02d}", consignes.consigne_lecture_vue(vue, images), consignes.schema_lecture_vue())
        vues.append(consignes.lecture_de_vue(vue, brut))
    return {"vues": lecture.valider_vues(vues)}


def main() -> int:
    args = parser().parse_args()
    dossier = args.sorties.expanduser().resolve()
    dossier.mkdir(parents=True, exist_ok=True)
    agent = Agent(dossier, args.reponses, args.model, args.timeout)
    try:
        faire = lire_traits if args.type == "traits" else lire_coupes
        resultat = faire(args.source.expanduser().resolve(), args.page - 1, dossier, agent)
    except (ThermiqueError, KeyError, ValueError) as exc:
        print(f"Lecture impossible : {exc}", file=sys.stderr)
        return 1
    (dossier / "lecture.json").write_text(json.dumps(resultat, ensure_ascii=False, indent=1), encoding="utf-8")
    nombre = len(resultat.get("traits", resultat.get("vues", [])))
    print(f"{nombre} {'trait(s)' if args.type == 'traits' else 'vue(s)'} lu(s) → {dossier / 'lecture.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
