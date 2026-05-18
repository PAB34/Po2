"""
Import des BPU (Bordereaux de Prix Unitaires) depuis un répertoire de PDFs.

Usage (dans le conteneur backend) :
    # Import par défaut : /app/energie/HERAULT ENERGIE/HISTORIQUE BPU/
    python -m app.scripts.import_bpu_documents

    # Répertoire personnalisé
    python -m app.scripts.import_bpu_documents --source-dir "/app/energie/HERAULT ENERGIE/HISTORIQUE BPU"

    # Un seul fichier (debug)
    python -m app.scripts.import_bpu_documents --only "BPU 2024 LOT 1 Elec.pdf"

    # Forcer le remplacement des BPU déjà importés
    python -m app.scripts.import_bpu_documents --force

    # Désactiver l'OCR (skip les scans)
    python -m app.scripts.import_bpu_documents --no-ocr
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from app.core.db import SessionLocal
from app.services.bpu import DEFAULT_BPU_SOURCE_DIR, import_directory


def main() -> int:
    parser = argparse.ArgumentParser(description="Import des BPU depuis des PDFs.")
    parser.add_argument(
        "--source-dir",
        default=str(DEFAULT_BPU_SOURCE_DIR),
        help=f"Répertoire contenant les PDFs (défaut : {DEFAULT_BPU_SOURCE_DIR})",
    )
    parser.add_argument(
        "--only",
        default=None,
        help="N'importer qu'un fichier spécifique (debug).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Forcer le remplacement des BPU déjà importés (delete + reinsert).",
    )
    parser.add_argument(
        "--no-ocr",
        action="store_true",
        help="Désactive l'OCR : les PDFs scannés sont skippés.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Logs plus détaillés.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    source = Path(args.source_dir)
    if not source.exists():
        print(f"Répertoire introuvable : {source}", file=sys.stderr)
        return 1

    with SessionLocal() as session:
        try:
            results = import_directory(
                session,
                source_dir=source,
                only_filename=args.only,
                enable_ocr=not args.no_ocr,
                force=args.force,
            )
        except FileNotFoundError as exc:
            print(str(exc), file=sys.stderr)
            return 1

    # Résumé final
    by_status: dict[str, int] = {}
    total_segments = 0
    total_components = 0
    total_charges = 0
    for r in results:
        by_status[r.status] = by_status.get(r.status, 0) + 1
        total_segments += r.segments_count
        total_components += r.components_count
        total_charges += r.fixed_charges_count

    print("\n=== RÉSUMÉ IMPORT BPU ===")
    print(f"  Fichiers traités    : {len(results)}")
    for status, count in sorted(by_status.items()):
        print(f"  {status:<14}      : {count}")
    print(f"  Segments créés      : {total_segments}")
    print(f"  Prix unitaires      : {total_components}")
    print(f"  Frais fixes         : {total_charges}")
    print()

    errors = [r for r in results if r.status == "error"]
    if errors:
        print("Erreurs :")
        for r in errors:
            print(f"  - {r.filename} : {r.error}")
        print()

    reviews = [r for r in results if r.status == "ocr_review"]
    if reviews:
        print("À revoir (confidence faible) :")
        for r in reviews:
            print(
                f"  - {r.filename} : {r.segments_count} segments, "
                f"{r.components_count} prix, conf={r.extraction_confidence:.2f}"
            )

    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
