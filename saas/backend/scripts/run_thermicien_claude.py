"""Lance l'agent Claude Code de lecture thermique sur un PDF aplati ou une image."""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image

BACKEND = Path(__file__).resolve().parents[1]
REPOSITORY = BACKEND.parents[1]
sys.path.insert(0, str(BACKEND))

from app.services.thermique import ThermiqueError  # noqa: E402
from app.services.thermique_claude_agent import (  # noqa: E402
    prepare_bundle,
    render_projection,
    run_agent,
    save_result,
)


def rasterize(source: Path, page: int, dpi: int, directory: Path) -> Path:
    if source.suffix.lower() != ".pdf":
        return source
    executable = shutil.which("pdftoppm") or shutil.which("pdftoppm.exe")
    if not executable:
        raise ThermiqueError("Poppler/pdftoppm est requis pour convertir le PDF en pixels.")
    destination = directory / "source"
    completed = subprocess.run(
        [executable, "-f", str(page), "-l", str(page), "-singlefile", "-r", str(dpi), "-jpeg", str(source), str(destination)],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise ThermiqueError(f"Rendu raster impossible : {completed.stderr.strip()[-600:]}")
    return destination.with_suffix(".jpg")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Analyse raster d'un plan avec le compte Claude Code local.")
    result.add_argument("source", type=Path, help="PDF aplati ou image PNG/JPEG du plan")
    result.add_argument("--output", type=Path, required=True, help="Fichier JSON de sortie")
    result.add_argument("--projection", type=Path, help="Projection PNG (par défaut : à côté du JSON)")
    result.add_argument("--work-dir", type=Path, help="Dossier des images intermédiaires")
    result.add_argument("--page", type=int, default=1, help="Page PDF à rendre (base 1)")
    result.add_argument("--dpi", type=int, default=150, help="Résolution du rendu PDF")
    result.add_argument("--rotation", type=int, choices=(0, 90, 180, 270), default=0, help="Rotation antihoraire")
    result.add_argument("--no-auto-crop", action="store_true", help="Conserve la feuille entière, cartouche compris")
    result.add_argument("--model", default="opus", help="Alias ou identifiant du modèle Claude")
    result.add_argument("--claude-bin", help="Chemin explicite du binaire Claude Code")
    result.add_argument("--timeout", type=int, default=900, help="Délai maximal de l'appel Claude, en secondes")
    result.add_argument("--prepare-only", action="store_true", help="Prépare les images sans appeler Claude")
    return result


def main() -> int:
    args = parser().parse_args()
    source = args.source.expanduser().resolve()
    if not source.is_file():
        print(f"Source introuvable : {source}", file=sys.stderr)
        return 2
    work_dir = (args.work_dir or args.output.with_suffix("").with_name(args.output.stem + "-bundle")).resolve()
    work_dir.mkdir(parents=True, exist_ok=True)
    try:
        raster = rasterize(source, args.page, args.dpi, work_dir)
        with Image.open(raster) as image:
            manifest = prepare_bundle(image, work_dir, args.rotation, not args.no_auto_crop)
        if args.prepare_only:
            print(work_dir / "manifest.json")
            return 0
        raw, envelope = run_agent(manifest, REPOSITORY, args.claude_bin, args.model, args.timeout)
        result = save_result(raw, manifest, args.output.resolve(), args.model, envelope)
        projection = (args.projection or args.output.with_suffix(".projection.png")).resolve()
        render_projection(result, projection)
        print(args.output.resolve())
        print(projection)
        return 0
    except ThermiqueError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
