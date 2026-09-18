"""Empêche la mise en veille automatique de Windows pendant un travail long.

Sur un poste d'entreprise, la stratégie de veille est souvent verrouillée par
GPO. Ce script ne la modifie pas : il utilise le mécanisme prévu par Windows
pour cela — `SetThreadExecutionState` — celui qu'emploient les lecteurs vidéo
pour empêcher l'écran de s'éteindre pendant un film. Aucun droit
administrateur, aucun réglage changé, et tout redevient normal à l'arrêt.

L'écran, lui, a le droit de s'éteindre : cela n'interrompt aucun traitement et
évite de laisser un poste allumé en évidence toute la nuit.

Usage :
    python scripts/garder_eveille.py               # jusqu'a Ctrl+C
    python scripts/garder_eveille.py --heures 6    # s'arrete tout seul
"""

from __future__ import annotations

import argparse
import ctypes
import sys
import time
from datetime import datetime, timedelta

# Constantes Windows (winbase.h).
ES_CONTINUOUS = 0x80000000        # l'etat reste actif jusqu'a nouvel ordre
ES_SYSTEM_REQUIRED = 0x00000001   # le systeme ne doit pas se mettre en veille
ES_DISPLAY_REQUIRED = 0x00000002  # l'ecran ne doit pas s'eteindre


def appliquer(garder_ecran: bool) -> bool:
    if not sys.platform.startswith("win"):
        print("Ce script ne sert que sous Windows.")
        return False
    etat = ES_CONTINUOUS | ES_SYSTEM_REQUIRED
    if garder_ecran:
        etat |= ES_DISPLAY_REQUIRED
    return ctypes.windll.kernel32.SetThreadExecutionState(etat) != 0


def relacher() -> None:
    if sys.platform.startswith("win"):
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)


def main() -> int:
    parser = argparse.ArgumentParser(description="Empeche la veille automatique de Windows.")
    parser.add_argument("--heures", type=float, default=0, help="duree max (0 = sans limite)")
    parser.add_argument("--ecran", action="store_true", help="garde aussi l'ecran allume")
    args = parser.parse_args()

    if not appliquer(args.ecran):
        print("Windows a refuse la demande : la veille n'est pas bloquee.")
        return 1

    fin = datetime.now() + timedelta(hours=args.heures) if args.heures else None
    print("Veille bloquee." + (f" Jusqu'a {fin:%H:%M}." if fin else " Ctrl+C pour rendre la main."))
    print("L'ecran peut s'eteindre : cela n'interrompt rien.")
    try:
        while fin is None or datetime.now() < fin:
            # Re-affirme l'etat toutes les minutes : certaines strategies le
            # reinitialisent apres un changement de session ou de profil d'alim.
            appliquer(args.ecran)
            time.sleep(60)
    except KeyboardInterrupt:
        pass
    finally:
        relacher()
        print("\nVeille rendue au systeme.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
