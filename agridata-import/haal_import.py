"""Wekelijkse EU-invoer van pluimvee uit de TAXUD-gegevens van de Europese Commissie.

Bron: de openbare API van het Agri-food data portal,
https://api.tech.ec.europa.eu/agrifood/api/taxud/weeklyData/import
(documentatie: https://agridata.ec.europa.eu/extensions/DataPortal/API_Documentation.html).

Het script haalt alle invoerrijen van de pluimveesector op (alle lidstaten, alle herkomstlanden)
en telt ze op tot twee overzichten die het dashboard leest:

    import_herkomst.json   per marktjaar, week, herkomstland, product en preferentie
    import_lidstaat.json   per marktjaar, week, lidstaat en product

Gebruik:
    python haal_import.py                  # schrijft naar ./uitvoer
    python haal_import.py --jaren 3        # alleen de laatste drie marktjaren
    python haal_import.py --sector "..."   # andere sector (zie --sectoren)
    python haal_import.py --sectoren       # toon de sectoren die de API kent
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

BASE = os.environ.get("AGRIFOOD_API_BASE", "https://api.tech.ec.europa.eu/agrifood/api").rstrip("/")
TIMEOUT = 300


class ApiFout(Exception):
    """De API is niet bereikbaar of geeft een fout."""


def haal(pad: str, params: dict | None = None):
    url = f"{BASE}/{pad.lstrip('/')}"
    if params:
        url += "?" + urllib.parse.urlencode(params, doseq=True)
    req = urllib.request.Request(url, headers={"accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as res:
            return json.load(res)
    except urllib.error.HTTPError as e:
        tekst = e.read().decode("utf-8", "replace")[:400]
        raise ApiFout(f"De API van de Commissie gaf HTTP {e.code} op {url}: {tekst}") from e
    except (urllib.error.URLError, TimeoutError) as e:
        raise ApiFout(f"De API van de Commissie is niet bereikbaar ({url}): {e}") from e


def pluimveesectoren(sectoren: list) -> list[str]:
    """De sectornamen die over pluimvee gaan (de API noemt ze in het Engels)."""
    namen = [s if isinstance(s, str) else (s.get("sector") or s.get("name") or "") for s in sectoren]
    return [n for n in namen if re.search(r"poult", n, re.I)]


def marktjaar_sleutel(jaar: str) -> int:
    """'2025' of '2025/2026' → 2025, voor sorteren."""
    m = re.match(r"\d{4}", str(jaar or ""))
    return int(m.group()) if m else 0


def getal(x) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def tel_op(rijen: list[dict], sleutels: tuple[str, ...]) -> list[dict]:
    som: dict[tuple, dict] = {}
    for r in rijen:
        k = tuple(r.get(s) for s in sleutels)
        doel = som.setdefault(k, {**{s: r.get(s) for s in sleutels}, "kg": 0.0, "euroValue": 0.0})
        doel["kg"] += getal(r.get("kg"))
        doel["euroValue"] += getal(r.get("euroValue"))
    uit = []
    for d in som.values():
        d["kg"] = round(d["kg"])
        d["euroValue"] = round(d["euroValue"])
        d["euroPerKg"] = round(d["euroValue"] / d["kg"], 3) if d["kg"] else None
        uit.append(d)
    uit.sort(key=lambda d: (marktjaar_sleutel(d.get("marketingYear")), d.get("week") or 0,
                            *(str(d.get(s)) for s in sleutels[2:])))
    return uit


def overzichten(rijen: list[dict], jaren: int | None = None) -> dict[str, list[dict]]:
    if jaren:
        alle = sorted({marktjaar_sleutel(r.get("marketingYear")) for r in rijen})
        houden = set(alle[-jaren:])
        rijen = [r for r in rijen if marktjaar_sleutel(r.get("marketingYear")) in houden]
    return {
        "import_herkomst": tel_op(rijen, ("marketingYear", "week", "partnerCode", "partner", "product", "preference")),
        "import_lidstaat": tel_op(rijen, ("marketingYear", "week", "memberStateCode", "memberStateName", "product")),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Wekelijkse EU-invoer van pluimvee (TAXUD) ophalen.")
    p.add_argument("--sector", help="sectornaam zoals de API hem kent; standaard alle pluimveesectoren")
    p.add_argument("--jaren", type=int, default=3, help="aantal laatste marktjaren (standaard 3)")
    p.add_argument("--uit", default="uitvoer", help="map voor de JSON-bestanden")
    p.add_argument("--sectoren", action="store_true", help="toon de sectoren van de API en stop")
    a = p.parse_args(argv)
    try:
        sectoren = haal("taxud/weeklyData/sectors")
        if a.sectoren:
            print(json.dumps(sectoren, indent=2, ensure_ascii=False))
            return 0
        kies = [a.sector] if a.sector else pluimveesectoren(sectoren)
        if not kies:
            raise ApiFout(f"Geen pluimveesector gevonden in {sectoren!r}; geef er een op met --sector.")
        rijen: list[dict] = []
        for s in kies:
            antwoord = haal("taxud/weeklyData/import", {"sectors": s})
            if not isinstance(antwoord, list):
                raise ApiFout(f"Onverwacht antwoord voor sector {s}: {str(antwoord)[:300]}")
            rijen += antwoord
            print(f"{s}: {len(antwoord)} rijen", file=sys.stderr)
    except ApiFout as e:
        print(f"Fout: {e}", file=sys.stderr)
        return 1
    uit = Path(a.uit)
    uit.mkdir(parents=True, exist_ok=True)
    for naam, data in overzichten(rijen, a.jaren).items():
        (uit / f"{naam}.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        print(f"{naam}.json: {len(data)} rijen", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
