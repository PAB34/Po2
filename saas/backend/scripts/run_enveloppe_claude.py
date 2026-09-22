"""Parcours de l'enveloppe extérieure par l'agent Claude Code ``thermicien-enveloppe``.

À lancer après la passe globale (run_thermicien_claude.py) : les pièces identifiées servent de guide.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
REPOSITORY = BACKEND.parents[1]
sys.path.insert(0, str(BACKEND))

from app.services import thermique_controle_image as controle  # noqa: E402
from app.services import thermique_enveloppe_pieces as pieces  # noqa: E402
from app.services import thermique_fiches_locaux as fiches_locaux  # noqa: E402
from app.services import thermique_lecture_locaux as lecture_locaux  # noqa: E402
from app.services import thermique_parcours_enveloppe as enveloppe  # noqa: E402
from app.services.thermique import ThermiqueError  # noqa: E402
from app.services.thermique_claude_agent import (  # noqa: E402
    claude_executable,
    cli_environment,
    render_projection,
)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Parcours de l'enveloppe extérieure le long des pièces.")
    result.add_argument("source", type=Path, help="PDF du plan")
    result.add_argument("--analysis", type=Path, required=True, help="JSON de la passe globale (pièces)")
    result.add_argument("--work-dir", type=Path, required=True, help="Dossier des bandes et planches")
    result.add_argument("--output", type=Path, required=True, help="JSON importable dans /analyse")
    result.add_argument("--page", type=int, default=1)
    result.add_argument("--dpi", type=int, default=300)
    result.add_argument("--echelle", type=float, default=100, help="Dénominateur d'échelle du plan")
    result.add_argument("--prepare-only", action="store_true")
    result.add_argument("--par-local", action="store_true",
                        help="Essai D42 : un tronçon par côté déperditif de chaque local (0 = face intérieure)")
    result.add_argument("--from-raw", type=Path, nargs="+", help="Réponse(s) brute(s) de l'agent déjà obtenue(s), fusionnées dans l'ordre")
    result.add_argument("--lot", type=int, help="Affiche la consigne du lot K (catalogue des lots précédents compris)")
    result.add_argument("--integrer-lot", nargs=2, metavar=("K", "FICHIER"),
                        help="Intègre la réponse du lot K : relevé enregistré, catalogue enrichi")
    result.add_argument("--model", default="opus")
    result.add_argument("--timeout", type=int, default=1800)
    return result


def catalogue_courant(dossier: Path) -> list:
    chemin = dossier / "catalogue.json"
    return json.loads(chemin.read_text(encoding="utf-8")) if chemin.is_file() else []


def consigne_du_lot(manifeste: dict, analyse: dict, source: Path, page: int, dossier: Path, rang: int) -> str:
    """Consigne du lot `rang` (base 1) avec le catalogue appris et sa planche de vignettes."""
    catalogue = catalogue_courant(dossier)
    image = None
    if catalogue:
        page_image = enveloppe.rendre_page(source, page, manifeste["dpi"], int(analyse["manifest"]["rotation_deg_ccw"]))
        image = str(enveloppe.planche_catalogue(page_image, manifeste, catalogue, dossier / f"catalogue-avant-lot-{rang}.png"))
    return enveloppe.consigne(manifeste, enveloppe.lots(manifeste)[rang - 1], catalogue, image)


def integrer_lot(dossier: Path, rang: int, brut: dict) -> None:
    (dossier / f"lot-{rang}.json").write_text(json.dumps(brut, ensure_ascii=False), encoding="utf-8")
    catalogue = enveloppe.fusionner_catalogue(catalogue_courant(dossier), brut.get("catalogue", []))
    (dossier / "catalogue.json").write_text(json.dumps(catalogue, ensure_ascii=False, indent=1), encoding="utf-8")


def appeler(manifeste: dict, modele: str, delai: int, consigne: str | None = None) -> dict:
    commande = [
        claude_executable(), "--add-dir", str(Path(manifeste["plan_guide"]).parent), "-p",
        consigne or enveloppe.consigne(manifeste),
        "--agent", "thermicien-enveloppe", "--model", modele, "--output-format", "json",
        "--json-schema", json.dumps(enveloppe.schema(), ensure_ascii=False, separators=(",", ":")),
        "--tools", "Read", "--permission-mode", "dontAsk", "--no-session-persistence",
    ]
    fini = subprocess.run(commande, cwd=REPOSITORY, env=cli_environment(), capture_output=True, text=True,
                          encoding="utf-8", timeout=delai, check=False)
    if fini.returncode != 0:
        raise ThermiqueError(f"Claude Code a interrompu le parcours ({fini.returncode}) : {(fini.stderr or fini.stdout)[-1200:]}")
    enveloppe_cli = json.loads(fini.stdout)
    brut = enveloppe_cli.get("structured_output") or enveloppe_cli.get("result")
    return json.loads(brut) if isinstance(brut, str) else brut


def bibliotheque_markdown(synthese: dict, perimetre: float) -> str:
    lignes = [f"# Enveloppe extérieure — composants candidats\n\nPérimètre parcouru : {perimetre:.1f} m\n",
              "## Catalogue appris pendant le parcours (à valider)\n",
              "| Id | Nom | Genre | Décision | Composition retenue (cm) | Occurrences | Linéaire | Règle de reconnaissance |",
              "|---|---|---|---|---|---|---|---|"]
    for fiche in synthese.get("composants", []):
        lignes.append(f"| {fiche['id']} | {fiche['nom']} | {fiche['genre']} | {fiche['decision']} | "
                      f"{fiche['composition_retenue'] or '—'} | {fiche['occurrences']} | {fiche['lineaire_m']:.1f} m | "
                      f"{fiche['regle']} |")
    lignes += ["\n## Familles de parois (regroupement par suite de couches)\n",
              "| Famille | Composition retenue (épaisseurs commerciales, cm) | Médiane lue (cm) | Fourchettes lues (cm) "
              "| Linéaire | Variantes |",
              "|---|---|---|---|---|---|"]
    for famille in synthese.get("familles", []):
        fourchettes = " / ".join(f"{c['min_cm']:g}–{c['max_cm']:g}" for c in famille["couches"])
        lignes.append(f"| {famille['famille']} | {famille['composition_retenue']} | {famille['composition_type']} | {fourchettes} | "
                      f"{famille['lineaire_m']:.1f} m | {famille['variantes']} |")
    lignes += ["\n## Parois opaques (détail des lectures)\n", "| Composition (ext → int, cm) | Épaisseur | Linéaire | Pièces |", "|---|---|---|---|"]
    for paroi in synthese["parois"]:
        lignes.append(f"| {paroi['composition']} | {paroi['epaisseur_cm']:g} cm | {paroi['lineaire_m']:.1f} m | {', '.join(paroi['pieces'])} |")
    lignes += ["\n## Menuiseries\n", "| Famille | Nombre | Largeurs (cm) | Pièces |", "|---|---|---|---|"]
    for famille in synthese["menuiseries"]:
        lignes.append(f"| {famille['famille']} | {famille['nombre']} | {', '.join(map(str, famille['largeurs_cm']))} | {', '.join(famille['pieces'])} |")
    lignes += ["\n## Liaisons (ponts thermiques)\n", "| Type | Tronçon | Abscisse | Pièce | Indice |", "|---|---|---|---|---|"]
    for liaison in synthese["liaisons"]:
        lignes.append(f"| {liaison['type']} | {liaison['troncon']} | {liaison['abscisse_m']:.2f} m | {liaison['piece']} | {liaison['indice']} |")
    lignes += ["\n## Par pièce (dimensions intérieures)\n",
               "| Pièce | Nature | Façade | Parois | Baies | Poteaux | Angles (ψ) | Refends (ψ, parts) | Liaison plancher |",
               "|---|---|---|---|---|---|---|---|---|"]
    for fiche in synthese.get("pieces", []):
        parois = ", ".join(f"{p['composant'] or p['composition']} {p['lineaire_m']:.2f} m" for p in fiche["parois"]) or "—"
        baies = ", ".join(f"{m['composant'] or m['type']} {m['lineaire_m']:.2f} m ({len(m['largeurs_cm'])})"
                          for m in fiche["menuiseries"]) or "—"
        ponts = fiche["ponts"]
        lignes.append(f"| {fiche['piece']} | {fiche.get('local', 'chauffe').replace('_', ' ')} | {fiche['facade_m']:.2f} m | {parois} | {baies} | {fiche['poteaux']} | "
                      f"{ponts['angle_sortant'] + ponts['angle_rentrant']:g} | {ponts['about_refend']:g} | "
                      f"{fiche['liaison_plancher_m']:.2f} m |")
    raccords = synthese.get("raccords", [])
    if raccords:
        rentrants = [r for r in raccords if r["nature"] == "rentrant"]
        sortants = [r for r in raccords if r["nature"] == "sortant"]
        lignes += [f"\nAngles raccordés (faces intérieures prolongées jusqu'à leur rencontre) : {len(raccords)} ; "
                   f"{len(rentrants)} rentrants ({sum(r['allongement_m'] for r in rentrants):+.2f} m), "
                   f"{len(sortants)} sortants ({sum(r['allongement_m'] for r in sortants):+.2f} m) ; "
                   f"{len(raccords) - len(rentrants) - len(sortants)} refusés (relevé à revoir : "
                   f"{', '.join(r['troncon'] for r in raccords if r['nature'] == 'refusé') or '—'}).\n"]
    bilan = synthese.get("controle")
    if bilan:
        isolant = bilan["isolant"]
        lignes += ["\n## Contrôle par l'image (indépendant de l'agent)\n",
                   f"Isolant : {isolant['vu_m']:.1f} m d'alvéoles vues sur l'image, {isolant['releve_m']:.1f} m comptés "
                   f"par l'agent, {isolant['commun_m']:.1f} m en commun ({isolant['taux_compte_pct']} % de l'isolant visible "
                   f"est compté). Écarts : planche `controle-image.png`.\n",
                   "| Composant | Type | Décision | Linéaire | Confirmé par l'image | Béton vu | Isolant vu |",
                   "|---|---|---|---|---|---|---|"]
        for ligne in bilan["composants"]:
            confirme = f"{ligne['confirme_pct']:g} %" if "confirme_pct" in ligne else "—"
            isolant_vu = f"{ligne['isolant_pct']:g} %" if "isolant_pct" in ligne else "—"
            lignes.append(f"| {ligne['composant']} | {ligne['type']} | {ligne['decision'] or '—'} | {ligne['lineaire_m']:.2f} m | "
                          f"{confirme} | {ligne['beton_pct']:g} % | {isolant_vu} |")
    demandes = synthese.get("demandes", [])
    if demandes:
        lignes += ["\n## Demandes à formuler (apport de l'étude)\n", "| Pièce | Demande | Motif | En attendant |", "|---|---|---|---|"]
        for demande in demandes:
            lignes.append(f"| {demande['piece']} | {demande['objet']} | {demande['motif']} | {demande['consequence']} |")
    return "\n".join(lignes) + "\n"


ADJACENCES = {"exterieur": "extérieur", "non_chauffe": "local non chauffé", "vide": "vide / patio",
              "circulation": "circulation", "chauffe": "local chauffé", "inconnu": "rien trouvé à moins de 1,2 m"}


def fiches_markdown(fiches: list) -> str:
    """Fiches par local, lisibles : un tableau des côtés par local."""
    lignes = ["# Fiches par local (dimensions intérieures)\n",
              "Adjacence de chaque côté sondée sur le plan ; déperditif = sur l'extérieur, un local non chauffé ou un vide.",
              "Planchers et hauteurs : à compléter avec les coupes.\n"]
    for fiche in fiches:
        lignes.append(f"## {fiche['piece']} — {fiche['local'].replace('_', ' ')}, {fiche['surface_m2']:.1f} m², "
                      f"périmètre {fiche['perimetre_m']:.1f} m, dont {fiche['deperditif_m']:.2f} m déperditifs\n")
        lignes += ["| Côté | Derrière | Voisin | Longueur | Épaisseur | Orientation | Déperditif | Enveloppe relevée |",
                   "|---|---|---|---|---|---|---|---|"]
        for rang, cote in enumerate(fiche["cotes"], 1):
            enveloppe = ", ".join(f"{e['composant']} {e['lineaire_m']:.2f} m" for e in cote["enveloppe"]) or "—"
            lignes.append(f"| {rang} | {ADJACENCES.get(cote['adjacence'], cote['adjacence'])} | {cote['voisin'] or '—'} | "
                          f"{cote['longueur_m']:.2f} m | {cote['epaisseur_cm']} cm | {cote['orientation']} | "
                          f"{'oui' if cote['deperditif'] else 'non'} | {enveloppe} |")
        ponts = fiche.get("ponts") or {}
        if any(ponts.values()):
            lignes.append(f"\nPonts thermiques : angles {ponts.get('angle_sortant', 0) + ponts.get('angle_rentrant', 0):g}, "
                          f"refends {ponts.get('about_refend', 0):g} ; liaison plancher {fiche['liaison_plancher_m']:.2f} m.")
        if fiche["alertes"]:
            lignes.append("\nÀ vérifier : " + " ; ".join(fiche["alertes"]) + ".")
        lignes.append("")
    return "\n".join(lignes) + "\n"


def main() -> int:
    # console Windows : la consigne contient des caractères hors page de code (≠, «, ») ;
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parser().parse_args()
    analyse = json.loads(args.analysis.read_text(encoding="utf-8"))
    try:
        manifeste_chemin = args.work_dir / "enveloppe-manifeste.json"
        if (args.from_raw or args.lot or args.integrer_lot) and manifeste_chemin.is_file():
            manifeste = json.loads(manifeste_chemin.read_text(encoding="utf-8"))
        else:
            if args.par_local:
                manifeste = lecture_locaux.preparer(args.source.resolve(), analyse, args.work_dir.resolve(), args.page,
                                                    args.dpi, args.echelle)
            else:
                # façade par tronçons + côtés des locaux chauffés sur local non chauffé ou vide (D46)
                manifeste = enveloppe.preparer(args.source.resolve(), analyse, args.work_dir.resolve(), args.page, args.dpi,
                                               args.echelle, complement=lecture_locaux.complement)
        dossier = args.work_dir.resolve()
        if args.lot:
            print(consigne_du_lot(manifeste, analyse, args.source.resolve(), args.page, dossier, args.lot))
            return 0
        if args.integrer_lot:
            rang, fichier = int(args.integrer_lot[0]), Path(args.integrer_lot[1])
            integrer_lot(dossier, rang, json.loads(fichier.read_text(encoding="utf-8")))
            print(f"lot {rang} intégré ; catalogue : {len(catalogue_courant(dossier))} composants")
            return 0
        if args.prepare_only:
            print(manifeste_chemin.resolve())
            print(f"{len(manifeste['troncons'])} tronçons, {manifeste['perimetre_m']} m, {len(manifeste['planches'])} planches")
            return 0
        if args.from_raw:
            parties = [json.loads(chemin.read_text(encoding="utf-8")) for chemin in args.from_raw]
        else:
            # parcours autonome : lots successifs, le catalogue appris passe d'un lot au suivant
            parties = []
            for rang in range(1, len(enveloppe.lots(manifeste)) + 1):
                consigne = consigne_du_lot(manifeste, analyse, args.source.resolve(), args.page, dossier, rang)
                partie = appeler(manifeste, args.model, args.timeout, consigne)
                integrer_lot(dossier, rang, partie)
                parties.append(partie)
        catalogue: list = []
        for partie in parties:
            catalogue = enveloppe.fusionner_catalogue(catalogue, partie.get("catalogue", []))
        brut = {"catalogue": catalogue,
                "elements": [e for partie in parties for e in partie["elements"]],
                "observations": [o for partie in parties for o in partie.get("observations", [])]}
        args.output.with_suffix(".raw.json").write_text(json.dumps(brut, ensure_ascii=False), encoding="utf-8")
        # chaque élément est rattaché à la pièce située derrière sa face intérieure (D18 à D20)
        brut = pieces.decouper_par_piece(brut, manifeste, analyse)
        releve = enveloppe.reprojeter(brut, manifeste, analyse)
        natures = pieces.natures_du_plan(analyse)
        releve["bibliotheque"]["pieces"] = [{**fiche, "local": natures.get(fiche["piece"], "chauffe")}
                                            for fiche in pieces.synthese_pieces(brut, manifeste)]
        releve["bibliotheque"]["raccords"] = brut.get("raccords", [])
        # fiche par local : ce qu'il y a derrière chaque côté, parois déperditives, enveloppe rattachée (D29 à D33)
        releve["bibliotheque"]["fiches_locaux"] = fiches_locaux.fiches(analyse, manifeste, brut, releve["bibliotheque"]["pieces"])
        releve["bibliotheque"]["demandes"] = pieces.demandes_etude(releve["bibliotheque"]["pieces"])
        page_image = enveloppe.rendre_page(args.source.resolve(), args.page, manifeste["dpi"],
                                           int(analyse["manifest"]["rotation_deg_ccw"]))
        # contrôle indépendant par l'image (alvéoles d'isolant, béton) : taux de confirmation par composant
        bilan = controle.controler(page_image, manifeste, brut)
        (dossier / "controle.json").write_text(json.dumps(bilan, ensure_ascii=False), encoding="utf-8")
        releve["bibliotheque"]["controle"] = {k: v for k, v in bilan.items() if k != "cellules"}
        print(controle.planche_controle(page_image, manifeste, brut, bilan, controle.troncons_a_montrer(bilan),
                                        dossier / "controle-image.png"))
        fusion = enveloppe.fusionner(analyse, releve, manifeste)
        args.output.write_text(json.dumps(fusion, ensure_ascii=False, indent=1), encoding="utf-8")
        args.output.with_suffix(".bibliotheque.md").write_text(
            bibliotheque_markdown(releve["bibliotheque"], manifeste["perimetre_m"]), encoding="utf-8")
        projection = args.output.with_suffix(".projection.png")
        render_projection(fusion, projection)
        # planches de relevé : ce que l'agent a lu, dessiné sur les bandes
        for chemin in enveloppe.annoter(page_image, manifeste, brut, dossier):
            print(chemin)
        print(pieces.planche_pieces(page_image, manifeste, analyse, brut, releve["bibliotheque"]["pieces"],
                                    args.output.with_suffix(".pieces.png")))
        print(fiches_locaux.planche_adjacences(page_image, analyse, manifeste, releve["bibliotheque"]["fiches_locaux"],
                                               args.output.with_suffix(".adjacences.png")))
        args.output.with_suffix(".locaux.md").write_text(fiches_markdown(releve["bibliotheque"]["fiches_locaux"]), encoding="utf-8")
        if catalogue:
            print(enveloppe.planche_catalogue(page_image, manifeste, catalogue, dossier / "catalogue.png"))
        print(args.output.resolve())
        print(projection.resolve())
        return 0
    except (ThermiqueError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
