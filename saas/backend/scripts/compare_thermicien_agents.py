"""Compare deux sorties d'agents thermiciens sur le même paquet raster, sans déclarer de vainqueur."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.services.thermique_agent_benchmark import comparer_sorties, ecrire_rapport, rendre_divergences  # noqa: E402


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Compare deux inventaires IA issus des mêmes images raster.")
    result.add_argument("--reference", type=Path, required=True, help="JSON brut de référence d'appariement")
    result.add_argument("--candidate", type=Path, required=True, help="JSON brut du candidat")
    result.add_argument("--background", type=Path, required=True, help="Vue globale raster du plan")
    result.add_argument("--output-dir", type=Path, required=True)
    result.add_argument("--reference-label", default="Claude Code")
    result.add_argument("--candidate-label", default="OpenAI")
    return result


def main() -> int:
    args = parser().parse_args()
    reference = json.loads(args.reference.read_text(encoding="utf-8"))
    candidate = json.loads(args.candidate.read_text(encoding="utf-8"))
    report = comparer_sorties(reference, candidate, args.reference_label, args.candidate_label)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    ecrire_rapport(report, args.output_dir / "comparatif.json", args.output_dir / "comparatif.md")
    rendre_divergences(args.background, reference, candidate, report, args.output_dir / "divergences.png")
    print(json.dumps(report["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
