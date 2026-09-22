"""Étude thermique d'un niveau à partir de son plan raster : une seule commande, reprise là où elle s'est arrêtée.

Enchaîne (docs/thermique/chaine-analyse-plan-raster.md) : passe globale (agent thermicien-plan) → guide et
bandes de l'enveloppe → parcours par lots avec catalogue appris (agent thermicien-enveloppe) → résolution,
découpage par pièce, raccords d'angles, contrôle par l'image, restitution.

Deux façons de faire travailler les agents, sans clé d'API :

- ``--mode session`` (par défaut) : la commande s'arrête quand un agent doit intervenir et écrit dans
  ``A-FAIRE.md`` la consigne, le fichier où enregistrer sa réponse et la commande à relancer. C'est la session
  Claude Code de l'utilisateur qui lance l'agent (compétence ``etude-thermique``), puis relance la commande ;
- ``--mode cli`` : la commande appelle elle-même Claude Code en ligne de commande (``claude -p --agent …``),
  avec l'abonnement Claude de l'utilisateur ; il faut que la commande ``claude`` soit connectée.

Code de sortie : 0 terminé, 3 en attente d'un agent, 1 erreur.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image

SCRIPTS = Path(__file__).resolve().parent
BACKEND = SCRIPTS.parent
REPOSITORY = BACKEND.parents[1]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(SCRIPTS))

import run_enveloppe_claude as parcours  # noqa: E402
import run_thermicien_claude as passe  # noqa: E402

from app.services import thermique_claude_agent as agent  # noqa: E402
from app.services import thermique_locaux as recaler  # noqa: E402
from app.services import thermique_parcours_enveloppe as enveloppe  # noqa: E402
from app.services.thermique import ThermiqueError  # noqa: E402

EN_ATTENTE = 3


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Étude thermique d'un niveau à partir de son plan raster.")
    result.add_argument("source", type=Path, help="PDF du plan (ou image)")
    result.add_argument("--niveau", required=True, help="Nom court du niveau (ex. R1)")
    result.add_argument("--sorties", type=Path, required=True, help="Dossier de l'étude ; le niveau y a son sous-dossier")
    result.add_argument("--rotation", type=int, choices=(0, 90, 180, 270), default=0,
                        help="Rotation antihoraire à appliquer (= (360 - rotation de la visionneuse) % 360)")
    result.add_argument("--page", type=int, default=1)
    result.add_argument("--echelle", type=float, default=100, help="Dénominateur d'échelle du plan")
    result.add_argument("--catalogue", type=Path, help="Catalogue validé d'un autre niveau ou projet, point de départ")
    result.add_argument("--mode", choices=("session", "cli"), default="session")
    result.add_argument("--model", default="opus")
    return result


class Etude:
    """Dossier d'un niveau et journal des étapes."""

    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.source = args.source.expanduser().resolve()
        self.dossier = (args.sorties / args.niveau).resolve()
        self.dossier.mkdir(parents=True, exist_ok=True)
        self.passe_dir = self.dossier / "passe-globale"
        self.passe_json = self.dossier / "passe-globale.json"
        self.passe_reponse = self.dossier / "passe-globale.reponse.json"
        self.locaux_json = self.dossier / "locaux.json"
        self.env_dir = self.dossier / "enveloppe"
        self.env_json = self.dossier / "enveloppe.json"
        self.journal_chemin = self.dossier / "journal.json"
        self.journal = json.loads(self.journal_chemin.read_text(encoding="utf-8")) if self.journal_chemin.is_file() else {
            "niveau": args.niveau, "source": str(self.source), "etapes": []}

    def noter(self, etape: str, etat: str, detail: str = "") -> None:
        self.journal["etapes"].append({"etape": etape, "etat": etat, "detail": detail,
                                       "date": time.strftime("%Y-%m-%d %H:%M:%S")})
        self.journal_chemin.write_text(json.dumps(self.journal, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"[{etape}] {etat}{' : ' + detail if detail else ''}")

    def relance(self) -> str:
        a = self.args
        morceaux = [f'python scripts/run_etude_niveau.py "{self.source}"', f"--niveau {a.niveau}",
                    f'--sorties "{a.sorties.resolve()}"', f"--rotation {a.rotation}", f"--page {a.page}"]
        if a.echelle != 100:
            morceaux.append(f"--echelle {a.echelle:g}")
        return " ".join(morceaux)

    def attendre(self, agent_nom: str, consigne: str, schema: dict, reponse: Path, etape: str) -> int:
        """Écrit la tâche de l'agent pour la session Claude Code et s'arrête."""
        consigne_chemin = self.dossier / f"consigne-{etape}.md"
        schema_chemin = self.dossier / f"schema-{etape}.json"
        consigne_chemin.write_text(consigne, encoding="utf-8")
        schema_chemin.write_text(json.dumps(schema, ensure_ascii=False, indent=1), encoding="utf-8")
        (self.dossier / "A-FAIRE.md").write_text(
            f"# En attente de l'agent `{agent_nom}` ({etape})\n\n"
            f"1. Lancer l'agent `{agent_nom}` avec, pour consigne, le contenu de `{consigne_chemin}`.\n"
            f"2. Sa réponse doit être un JSON conforme à `{schema_chemin}` ; l'enregistrer telle quelle dans\n"
            f"   `{reponse}`.\n"
            f"3. Relancer (depuis `saas/backend`) :\n\n```\n{self.relance()}\n```\n", encoding="utf-8")
        self.noter(etape, "en attente", f"agent {agent_nom} ; réponse attendue dans {reponse.name}")
        return EN_ATTENTE


def passe_globale(etude: Etude) -> int | None:
    if etude.passe_json.is_file():
        return None
    etude.passe_dir.mkdir(parents=True, exist_ok=True)
    raster = passe.rasterize(etude.source, etude.args.page, 150, etude.passe_dir)
    with Image.open(raster) as image:
        manifest = agent.prepare_bundle(image, etude.passe_dir, etude.args.rotation, True)
    if etude.passe_reponse.is_file():
        raw, enveloppe_cli = agent.parse_cli_output(etude.passe_reponse.read_text(encoding="utf-8")), None
    elif etude.args.mode == "cli":
        raw, enveloppe_cli = agent.run_agent(manifest, REPOSITORY, None, etude.args.model, 900)
        etude.passe_reponse.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    else:
        return etude.attendre("thermicien-plan", agent.build_prompt(manifest), agent.output_schema(),
                              etude.passe_reponse, "passe-globale")
    resultat = agent.save_result(raw, manifest, etude.passe_json, etude.args.model, enveloppe_cli)
    agent.render_projection(resultat, etude.passe_json.with_suffix(".projection.png"))
    etude.noter("passe-globale", "faite", f"{len(resultat['objects'])} objets")
    return None


def appeler_agent(nom: str, consigne: str, schema: dict, dossier_images: Path, modele: str, delai: int = 900) -> dict:
    """Mode cli : un agent du dépôt appelé par Claude Code en ligne de commande (abonnement, pas de clé d'API)."""
    commande = [agent.claude_executable(), "--add-dir", str(dossier_images), "-p", consigne, "--agent", nom,
                "--model", modele, "--output-format", "json",
                "--json-schema", json.dumps(schema, ensure_ascii=False, separators=(",", ":")),
                "--tools", "Read", "--permission-mode", "dontAsk", "--no-session-persistence"]
    fini = subprocess.run(commande, cwd=REPOSITORY, env=agent.cli_environment(), capture_output=True, text=True,
                          encoding="utf-8", timeout=delai, check=False)
    if fini.returncode != 0:
        raise ThermiqueError(f"Claude Code a interrompu l'agent {nom} ({fini.returncode}) : {(fini.stderr or fini.stdout)[-1200:]}")
    enveloppe_cli = json.loads(fini.stdout)
    brut = enveloppe_cli.get("structured_output") or enveloppe_cli.get("result")
    return json.loads(brut) if isinstance(brut, str) else brut


def locaux(etude: Etude) -> int | None:
    """Contours recalés sur les murs, nature des locaux, espaces libres nommés (D24 à D27)."""
    if etude.locaux_json.is_file():
        return None
    analyse = json.loads(etude.passe_json.read_text(encoding="utf-8"))
    recalage_chemin = etude.dossier / "recalage.json"
    if recalage_chemin.is_file():
        recalage = json.loads(recalage_chemin.read_text(encoding="utf-8"))
    else:
        page = enveloppe.rendre_page(etude.source, etude.args.page, 300, int(analyse["manifest"]["rotation_deg_ccw"]))
        px_par_m = 300 / enveloppe.M_PAR_POUCE / etude.args.echelle
        batiment = enveloppe.contour_guide(analyse, page.width, page.height, px_par_m, page)["polygone"]
        recalage = recaler.recaler_pieces(page, analyse, px_par_m, batiment)
        recalage_chemin.write_text(json.dumps(recalage, ensure_ascii=False), encoding="utf-8")
        garde = sum(1 for p in recalage["pieces"] if p["recale"])
        etude.noter("recalage", "fait", f"{garde}/{len(recalage['pieces'])} pièces recalées, {len(recalage['candidats'])} espaces libres")
    analyse = recaler.appliquer(analyse, recalage)
    reponse = etude.dossier / "locaux.reponse.json"
    if reponse.is_file():
        brut = json.loads(reponse.read_text(encoding="utf-8"))
    else:
        consigne = recaler.consigne_locaux(analyse, recalage)
        if etude.args.mode != "cli":
            return etude.attendre("thermicien-plan", consigne, recaler.schema_locaux(), reponse, "locaux")
        brut = appeler_agent("thermicien-plan", consigne, recaler.schema_locaux(), etude.passe_dir, etude.args.model)
        reponse.write_text(json.dumps(brut, ensure_ascii=False), encoding="utf-8")
    finale = recaler.integrer_locaux(analyse, recalage, brut)
    etude.locaux_json.write_text(json.dumps(finale, ensure_ascii=False, indent=1), encoding="utf-8")
    pieces_finales = [o for o in finale["objects"] if o["category"] == "piece"]
    etude.noter("locaux", "faits", f"{len(pieces_finales)} pièces, dont "
                f"{sum(1 for o in pieces_finales if o.get('local') == 'circulation')} circulations")
    return None


def preparer_enveloppe(etude: Etude) -> dict:
    chemin = etude.env_dir / "enveloppe-manifeste.json"
    analyse = json.loads(etude.locaux_json.read_text(encoding="utf-8"))
    if chemin.is_file():
        return json.loads(chemin.read_text(encoding="utf-8"))
    manifeste = enveloppe.preparer(etude.source, analyse, etude.env_dir, etude.args.page, 300, etude.args.echelle)
    if etude.args.catalogue and not (etude.env_dir / "catalogue.json").is_file():
        shutil.copyfile(etude.args.catalogue, etude.env_dir / "catalogue.json")
        etude.noter("catalogue", "repris", str(etude.args.catalogue))
    etude.noter("guide", "fait", f"{len(manifeste['troncons'])} tronçons, {manifeste['perimetre_m']} m")
    return manifeste


def parcourir(etude: Etude, manifeste: dict) -> int | None:
    analyse = json.loads(etude.locaux_json.read_text(encoding="utf-8"))
    for rang in range(1, len(enveloppe.lots(manifeste)) + 1):
        fait = etude.env_dir / f"lot-{rang}.json"
        if fait.is_file():
            continue
        reponse = etude.env_dir / f"reponse-lot-{rang}.json"
        if reponse.is_file():
            brut = json.loads(reponse.read_text(encoding="utf-8"))
        else:
            consigne = parcours.consigne_du_lot(manifeste, analyse, etude.source, etude.args.page, etude.env_dir, rang)
            if etude.args.mode != "cli":
                return etude.attendre("thermicien-enveloppe", consigne, enveloppe.schema(), reponse, f"lot-{rang}")
            brut = parcours.appeler(manifeste, etude.args.model, 1800, consigne)
            reponse.write_text(json.dumps(brut, ensure_ascii=False), encoding="utf-8")
        parcours.integrer_lot(etude.env_dir, rang, brut)
        etude.noter(f"lot-{rang}", "intégré", f"catalogue : {len(parcours.catalogue_courant(etude.env_dir))} composants")
    return None


def restituer(etude: Etude, manifeste: dict) -> None:
    lots = [str(etude.env_dir / f"lot-{rang}.json") for rang in range(1, len(enveloppe.lots(manifeste)) + 1)]
    commande = [sys.executable, str(SCRIPTS / "run_enveloppe_claude.py"), str(etude.source),
                "--analysis", str(etude.locaux_json), "--work-dir", str(etude.env_dir), "--output", str(etude.env_json),
                "--page", str(etude.args.page), "--from-raw", *lots]
    fini = subprocess.run(commande, cwd=BACKEND, capture_output=True, text=True, encoding="utf-8", check=False)
    if fini.returncode != 0:
        raise ThermiqueError(f"Restitution interrompue : {(fini.stderr or fini.stdout)[-1500:]}")
    etude.noter("restitution", "faite", etude.env_json.name)


def a_faire_final(etude: Etude) -> None:
    """Ce qui reste au thermicien : décisions à confirmer, raccords refusés, demandes."""
    fusion = json.loads(etude.env_json.read_text(encoding="utf-8"))
    bibliotheque = fusion["enveloppe"]["bibliotheque"]
    lignes = [f"# Niveau {etude.args.niveau} : étude terminée — ce qui reste à vous\n",
              f"Résultats : `{etude.env_json.with_suffix('.bibliotheque.md').name}`, "
              f"`{etude.env_json.with_suffix('.pieces.png').name}`, `enveloppe/catalogue.png`, "
              f"`enveloppe/controle-image.png`, `enveloppe/releve-XX.png`.\n"]
    confirmer = [c for c in bibliotheque["composants"] if c.get("decision") == "a_confirmer"]
    if confirmer:
        lignes.append("## Composants à confirmer (catalogue)\n")
        lignes += [f"- {c['id']} « {c['nom']} » : {c['composition'] or '—'} ({c['lineaire_m']:.1f} m)" for c in confirmer]
    refuses = [r for r in bibliotheque.get("raccords", []) if r["nature"] == "refusé"]
    if refuses:
        lignes.append("\n## Angles au relevé à revoir (raccord refusé)\n")
        lignes += [f"- {r['troncon']} à {r['abscisse_m']:.2f} m ({', '.join(r['pieces'])})" for r in refuses]
    demandes = bibliotheque.get("demandes", [])
    if demandes:
        lignes.append("\n## Demandes à formuler (architecte, maître d'ouvrage)\n")
        lignes += [f"- {d['piece']} : {d['objet']} ({d['motif']})" for d in demandes]
    alertes = [(f["piece"], a) for f in bibliotheque.get("fiches_locaux", []) for a in f["alertes"]]
    if alertes:
        lignes.append(f"\n## Fiches par local : points à vérifier ({len(alertes)})\n")
        lignes += [f"- {piece} : {alerte}" for piece, alerte in alertes]
    controle = bibliotheque.get("controle", {}).get("isolant", {})
    if controle:
        lignes.append(f"\n## Contrôle par l'image\n\n{controle.get('taux_compte_pct')} % de l'isolant visible est compté ;"
                      f" écarts sur `enveloppe/controle-image.png`.")
    (etude.dossier / "A-FAIRE.md").write_text("\n".join(lignes) + "\n", encoding="utf-8")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parser().parse_args()
    etude = Etude(args)
    if not etude.source.is_file():
        print(f"Plan introuvable : {etude.source}", file=sys.stderr)
        return 1
    try:
        attente = passe_globale(etude) or locaux(etude)
        if attente:
            return attente
        manifeste = preparer_enveloppe(etude)
        attente = parcourir(etude, manifeste)
        if attente:
            return attente
        restituer(etude, manifeste)
        a_faire_final(etude)
        etude.noter("etude", "terminée", str(etude.dossier / "A-FAIRE.md"))
        return 0
    except (ThermiqueError, ValueError) as exc:
        etude.noter("erreur", "arrêt", str(exc)[:300])
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
