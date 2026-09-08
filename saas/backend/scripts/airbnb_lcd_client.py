#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Couche d'accès à Airbnb : hash de recherche, réessais, cache disque.

Ce module concentre tout ce qui touche au réseau, pour que la collecte et
l'extraction n'aient à s'occuper que de leur logique.

Trois problèmes mesurés sur le POC v1 sont traités ici :

1. le hash StaysSearch était récupéré une seule fois ; sur une collecte de
   plusieurs heures il expire — on le renouvelle sur échec ;
2. aucun réessai : la moindre coupure perdait une tuile — backoff exponentiel ;
3. aucun cache : relancer le passage 2 re-téléchargeait tout — cache par room_id.

Aucune tentative de contournement d'un blocage, d'une authentification ou d'un
CAPTCHA. Si Airbnb refuse, on journalise et on passe.
"""

from __future__ import annotations

import json
import random
import time
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlencode

import pyairbnb

# Plafond de résultats observé sur une recherche, quelle que soit l'emprise
# (mesuré : 40 sur trois emprises allant du centre-ville à la commune entière).
# Une tuile qui atteint ce nombre est réputée tronquée, pas complète.
PLAFOND_RESULTATS = 40

BASE_RECHERCHE = "https://www.airbnb.fr/s/homes"
DOMAINE = "www.airbnb.fr"


class ClientAirbnb:
    """Accès à Airbnb avec hash auto-renouvelé, réessais et cache disque."""

    def __init__(
        self,
        cache_dir: Path,
        pause: float = 1.0,
        timeout: int = 60,
        max_essais: int = 4,
        devise: str = "EUR",
        langue: str = "fr",
    ) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.pause = pause
        self.timeout = timeout
        self.max_essais = max_essais
        self.devise = devise
        self.langue = langue

        self._hash: str | None = None
        self.stats = {"recherches": 0, "details": 0, "cache_hits": 0,
                      "echecs": 0, "renouvellements_hash": 0}

    # ------------------------------------------------------------------ hash

    @property
    def hash_recherche(self) -> str:
        if self._hash is None:
            self._renouveler_hash()
        return self._hash  # type: ignore[return-value]

    def _renouveler_hash(self) -> None:
        self._hash = pyairbnb.fetch_stays_search_hash()
        self.stats["renouvellements_hash"] += 1

    # --------------------------------------------------------------- réessai

    def _avec_reessais(self, action: Callable[[], Any], libelle: str) -> Any:
        """
        Exécute `action` avec backoff exponentiel et jitter.

        Au deuxième échec on renouvelle le hash : c'est la panne la plus probable
        sur une collecte longue.
        """
        derniere: Exception | None = None
        for essai in range(1, self.max_essais + 1):
            try:
                return action()
            except Exception as exc:  # noqa: BLE001 - on journalise et on réessaie
                derniere = exc
                if essai == self.max_essais:
                    break
                if essai >= 2:
                    try:
                        self._renouveler_hash()
                    except Exception:  # noqa: BLE001
                        pass
                attente = min(60.0, (2 ** essai)) + random.uniform(0, 1.5)
                print(f"      ! {libelle} échec {essai}/{self.max_essais} "
                      f"({exc!r}) — nouvelle tentative dans {attente:.1f}s")
                time.sleep(attente)

        self.stats["echecs"] += 1
        raise RuntimeError(f"{libelle} : échec après "
                           f"{self.max_essais} tentatives") from derniere

    # ------------------------------------------------------------- recherche

    def url_recherche(self, sw_lat: float, sw_lon: float,
                      ne_lat: float, ne_lon: float) -> str:
        """
        Recherche par emprise, sans dates : on veut l'inventaire du parc,
        pas seulement les logements disponibles à une période donnée.
        """
        params = {
            "ne_lat": f"{ne_lat:.7f}", "ne_lng": f"{ne_lon:.7f}",
            "sw_lat": f"{sw_lat:.7f}", "sw_lng": f"{sw_lon:.7f}",
            "zoom": "15", "search_by_map": "true", "tab_id": "home_tab",
            "refinement_paths[]": "/homes",
        }
        return BASE_RECHERCHE + "?" + urlencode(params, doseq=True)

    def rechercher(self, sw_lat: float, sw_lon: float,
                   ne_lat: float, ne_lon: float) -> list[dict]:
        """Une recherche sur une emprise. Rend la liste brute des annonces."""
        url = self.url_recherche(sw_lat, sw_lon, ne_lat, ne_lon)

        def action():
            return pyairbnb.search_all_from_url(
                url, currency=self.devise, language=self.langue,
                proxy_url="", hash=self.hash_recherche, timeout=self.timeout,
            )

        res = self._avec_reessais(action, "recherche")
        self.stats["recherches"] += 1
        time.sleep(self.pause)
        return res or []

    # --------------------------------------------------------------- détails

    def _chemin_cache(self, room_id: str) -> Path:
        # Sous-dossiers à 2 caractères : évite des dizaines de milliers de
        # fichiers dans un seul répertoire (pénible sous Windows).
        rid = str(room_id)
        return self.cache_dir / rid[-2:] / f"{rid}.json"

    def en_cache(self, room_id: str) -> bool:
        return self._chemin_cache(room_id).exists()

    def details(self, room_id: str, forcer: bool = False) -> dict:
        """
        Fiche détaillée d'une annonce, servie par le cache si déjà téléchargée.

        Le cache est la reprise sur erreur : relancer le passage 2 ne
        retélécharge que ce qui manque.
        """
        chemin = self._chemin_cache(room_id)
        if chemin.exists() and not forcer:
            self.stats["cache_hits"] += 1
            return json.loads(chemin.read_text(encoding="utf-8"))

        def action():
            return pyairbnb.get_details(
                room_id=room_id, currency=self.devise, language=self.langue,
                proxy_url="", domain=DOMAINE,
            )

        fiche = self._avec_reessais(action, f"details {room_id}")
        self.stats["details"] += 1

        chemin.parent.mkdir(parents=True, exist_ok=True)
        chemin.write_text(json.dumps(fiche, ensure_ascii=False),
                          encoding="utf-8")
        time.sleep(self.pause)
        return fiche
