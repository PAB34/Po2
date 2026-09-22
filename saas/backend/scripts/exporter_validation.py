"""Page de validation tronçon par tronçon d'un relevé d'enveloppe (stratégie S1, vérité terrain).

Produit un dossier publiable : ``index.html`` (données du relevé intégrées), ``bandes/Txx.jpg`` (bande annotée
avec la lecture de l'agent) et ``bandes/Txx-brut.jpg`` (bande seule). Les validations et corrections du
thermicien sont enregistrées dans la base de la page (collections ``troncons`` et ``catalogue``), relue ensuite
par Claude Code pour écrire la référence du niveau.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
BACKEND = SCRIPTS.parent
sys.path.insert(0, str(BACKEND))

from app.services import thermique_parcours_enveloppe as enveloppe  # noqa: E402

GABARIT = SCRIPTS / "validation" / "page.html"
CHAMPS = ("debut_m", "fin_m", "type", "composant", "nu_exterieur_cm", "nu_interieur_cm", "nu_exterieur_fin_cm",
          "nu_interieur_fin_cm", "menuiserie_type", "cadre_cm", "confiance", "a_verifier", "indice")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Page de validation tronçon par tronçon d'un relevé d'enveloppe.")
    result.add_argument("source", type=Path, help="PDF du plan")
    result.add_argument("--niveau", required=True)
    result.add_argument("--analysis", type=Path, required=True, help="JSON de la passe globale")
    result.add_argument("--work-dir", type=Path, required=True, help="Dossier du parcours (manifeste, catalogue, contrôle)")
    result.add_argument("--raw", type=Path, required=True, help="Relevé brut fusionné (.raw.json)")
    result.add_argument("--sortie", type=Path, required=True, help="Dossier de la page à publier")
    result.add_argument("--page", type=int, default=1)
    return result


def signalements(dossier: Path, bibliotheque: dict | None) -> dict[str, list[str]]:
    """Ce que les contrôles signalent par tronçon (écarts avec l'image, raccords refusés)."""
    resultat: dict[str, list[str]] = {}
    controle = dossier / "controle.json"
    if controle.is_file():
        bilan = json.loads(controle.read_text(encoding="utf-8"))
        for suite in bilan["isolant"]["manques"]:
            resultat.setdefault(suite["troncon"], []).append(
                f"alvéoles vues non comptées {suite['debut_m']:.2f}–{suite['fin_m']:.2f} m ({suite['composant']})")
        for suite in bilan["isolant"]["non_vus"]:
            resultat.setdefault(suite["troncon"], []).append(
                f"isolant compté mais non vu {suite['debut_m']:.2f}–{suite['fin_m']:.2f} m ({suite['composant']})")
    for raccord in (bibliotheque or {}).get("raccords", []):
        if raccord["nature"] == "refusé":
            resultat.setdefault(raccord["troncon"], []).append(f"angle au relevé douteux vers {raccord['abscisse_m']:.2f} m")
    return resultat


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parser().parse_args()
    dossier = args.work_dir.resolve()
    manifeste = json.loads((dossier / "enveloppe-manifeste.json").read_text(encoding="utf-8"))
    analyse = json.loads(args.analysis.read_text(encoding="utf-8"))
    brut = json.loads(args.raw.read_text(encoding="utf-8"))
    catalogue = json.loads((dossier / "catalogue.json").read_text(encoding="utf-8"))
    sortie = args.sortie.resolve()
    (sortie / "bandes").mkdir(parents=True, exist_ok=True)
    page = enveloppe.rendre_page(args.source.resolve(), args.page, manifeste["dpi"], int(analyse["manifest"]["rotation_deg_ccw"]))
    for troncon, image in enveloppe.bandes_annotees(page, manifeste, brut):
        image.save(sortie / "bandes" / f"{troncon['id']}.jpg", quality=82, optimize=True)
        brute = enveloppe._graduer(enveloppe._bande(page, troncon, manifeste["px_par_m"]), troncon, manifeste["px_par_m"])
        brute.convert("RGB").save(sortie / "bandes" / f"{troncon['id']}-brut.jpg", quality=82, optimize=True)
    fusion_chemin = args.raw.with_name(args.raw.name.replace(".raw.json", ".json"))
    bibliotheque = json.loads(fusion_chemin.read_text(encoding="utf-8"))["enveloppe"]["bibliotheque"] if fusion_chemin.is_file() else None
    donnees = {
        "niveau": args.niveau,
        "plan": args.source.name,
        "troncons": [{"id": t["id"], "debut_m": t["debut_m"], "fin_m": t["fin_m"], "piece": t["piece"], "cote": t["cote"]}
                     for t in manifeste["troncons"]],
        "elements": [{k: e.get(k) for k in CHAMPS} | {"troncon": e["troncon"]} for e in brut["elements"]],
        "catalogue": [{"id": f["id"], "nom": f["nom"], "genre": f["genre"], "decision": f["decision"],
                       "composition": enveloppe.composition_libelle(f.get("couches") or []), "regle": f.get("regle", "")}
                      for f in catalogue],
        "signalements": signalements(dossier, bibliotheque),
        "types": list(enveloppe.TYPES),
    }
    html = GABARIT.read_text(encoding="utf-8").replace("/*DONNEES*/null", json.dumps(donnees, ensure_ascii=False))
    (sortie / "index.html").write_text(html, encoding="utf-8")
    print(sortie / "index.html")
    print(f"{len(donnees['troncons'])} tronçons, {len(donnees['elements'])} intervalles, "
          f"{sum(1 for t in donnees['troncons'] if t['id'] in donnees['signalements'])} tronçons signalés")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
