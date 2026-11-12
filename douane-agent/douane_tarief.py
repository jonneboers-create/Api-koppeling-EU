"""Opvragen van invoerheffingen en tariefcontingenten (TRQ) bij het Gebruikstarief van de Douane.

De website https://tarief.douane.nl/ite-tariff-public/ is een Angular-app boven op een JSON-dienst
zonder login of token. Hetzelfde pakket (ITE Tariff van KGH) draait ook in Luxemburg
(saturn.etat.lu), waar de dienst onder `/ite-tariff-public-proxy/ite-tariff-trusted-rs/v1` staat.
Voor Nederland gaan we uit van hetzelfde pad op tarief.douane.nl; is dat anders, zet dan
DOUANE_API_BASE (zie README).

Eén GET op `/mcc/measures` geeft alle maatregelen op een goederencode van tien cijfers voor een
datum en een richting (I = invoer, E = uitvoer): rechten derde landen, preferentiële rechten,
tariefcontingenten, btw, accijns, antidumping, enzovoort. Dit bestand haalt die lijst op en maakt
er een compacte samenvatting van die een taalmodel (of een mens) kan lezen.

Ook los te gebruiken:
    python douane_tarief.py 0207141000 --land BR
    python douane_tarief.py 0207141000 --land BR --ruw     # het volledige antwoord van de dienst
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

BASE = os.environ.get(
    "DOUANE_API_BASE",
    "https://tarief.douane.nl/ite-tariff-public-proxy/ite-tariff-trusted-rs/v1",
).rstrip("/")
WEBSITE = "https://tarief.douane.nl/ite-tariff-public/#/taric/nomenclature/sbn"
TIMEOUT = 20

ERGA_OMNES = "1011"  # alle derde landen
EU = "1010"

# TARIC-maatregeltypen voor tariefcontingenten.
QUOTA_TYPES = {
    "122": "Niet-preferentieel tariefcontingent",
    "123": "Niet-preferentieel tariefcontingent (bijzondere bestemming)",
    "143": "Preferentieel tariefcontingent",
    "146": "Preferentieel tariefcontingent (bijzondere bestemming)",
    "147": "Contingent douane-unie",
    "653": "Autonoom tariefcontingent (bijzondere bestemming)",
    "654": "Preferentieel tariefcontingent (bijzondere bestemming)",
}
# Velden die we zelf al samenvatten; alle andere velden van een maatregel gaan als `overig` mee,
# zodat er niets verloren gaat (bijvoorbeeld het veld met het volgnummer van een contingent).
KNOWN_FIELDS = {
    "sid", "national", "regulation", "commodityCode", "measureType", "footnotes",
    "geographicalArea", "excludedCountryIds", "dutyExpressions", "conditions", "startDate",
    "endDate", "certificates", "unreleased", "additionalCode",
}
TAAL = ("nl", "en")


class DouaneFout(Exception):
    """De dienst kon niet worden bereikt of gaf een onbruikbaar antwoord."""


def tekst(descriptions: Any) -> str | None:
    """De Nederlandse omschrijving, anders de Engelse, anders de eerste die er is."""
    if isinstance(descriptions, str):
        return descriptions
    if not isinstance(descriptions, dict) or not descriptions:
        return None
    for taal in TAAL:
        if descriptions.get(taal):
            return str(descriptions[taal]).strip()
    return str(next(iter(descriptions.values()))).strip()


def normaliseer_code(code: str) -> str:
    """Alleen de cijfers; een code korter dan tien cijfers wordt aangevuld met nullen."""
    digits = re.sub(r"\D", "", str(code))
    if not digits:
        raise ValueError("Geen goederencode opgegeven.")
    if len(digits) > 10:
        raise ValueError(f"Goederencode {code!r} heeft meer dan tien cijfers.")
    return digits.ljust(10, "0")


def maatregelen_url(code: str, datum: str, richting: str = "I") -> str:
    q = urllib.parse.urlencode({
        "count": "500", "offset": "0", "sortorder": "A",
        "simulationdate": datum, "tradedirection": richting,
        "commoditycode": code, "currency": "EUR",
    })
    return f"{BASE}/mcc/measures?{q}"


def website_url(code: str, datum: str, richting: str = "I") -> str:
    return f"{WEBSITE}?cc={code}&sd={datum}&d={richting}&l=nl&ql=nl&ea=true"


def haal_maatregelen(code: str, datum: str, richting: str = "I") -> dict:
    """Het ruwe antwoord van de dienst. Een 400/404 betekent meestal: code niet aangeefbaar."""
    req = urllib.request.Request(
        maatregelen_url(code, datum, richting),
        headers={"accept": "application/json", "user-agent": "douane-tarief-agent/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as res:
            return json.load(res)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:500]
        if e.code in (400, 404):
            return {"fout": e.code, "melding": body}
        raise DouaneFout(f"De douanedienst antwoordde met HTTP {e.code}: {body}") from e
    except (urllib.error.URLError, TimeoutError) as e:
        raise DouaneFout(f"De douanedienst is niet bereikbaar ({BASE}): {e}") from e
    except json.JSONDecodeError as e:
        raise DouaneFout("De douanedienst gaf geen JSON terug; klopt DOUANE_API_BASE?") from e


def contingent_nummer(m: dict) -> str | None:
    """Het volgnummer (09.xxxx) van een tariefcontingent, in welk veld de dienst het ook zet."""
    for key, val in m.items():
        if not re.search(r"quota|order", key, re.I):
            continue
        if isinstance(val, dict):
            for sub in ("orderNumber", "id", "number", "quotaOrderNumber"):
                if val.get(sub):
                    return str(val[sub])
        elif val:
            return str(val)
    return None


def geldt_voor_land(m: dict, land: str | None) -> str:
    """'ja', 'nee' of 'controleren' (landengroep waarvan we het lidmaatschap niet kennen)."""
    if not land:
        return "ja"
    area = (m.get("geographicalArea") or {}).get("id")
    excluded = {str(x).upper() for x in m.get("excludedCountryIds") or []}
    if land in excluded:
        return "nee"
    # ERGA OMNES geldt voor alle landen; nationale heffingen (btw, accijns) staan soms op EU (1010).
    if area is None or area in (ERGA_OMNES, EU):
        return "ja"
    if re.fullmatch(r"[A-Z]{2}", str(area)):
        return "ja" if area == land else "nee"
    return "controleren"


def _zonder_dubbele_eu_rijen(rijen: list[dict]) -> list[dict]:
    """Nationale heffingen komen vaak twee keer: voor ERGA OMNES en voor de EU. Houd er één."""
    def sleutel(r):
        return (r["type"], r["heffing"], r.get("aanvullende_code"), r["code"])
    omnes = {sleutel(r) for r in rijen if r["land_of_groep"].startswith(ERGA_OMNES)}
    return [r for r in rijen if not (r["land_of_groep"].startswith(EU + " ") and sleutel(r) in omnes)]


def vat_samen(antwoord: dict, land: str | None = None) -> dict:
    """Compacte samenvatting van het antwoord: per maatregel type, land(engroep), heffing en TRQ."""
    if "fout" in antwoord:
        return {"fout": f"De douane weigert deze code (HTTP {antwoord['fout']}): "
                        "waarschijnlijk geen aangeefbare code van tien cijfers.",
                "melding": antwoord.get("melding")}
    extra_codes = {
        str(a.get("typeAndId")): tekst(a.get("descriptions"))
        for a in antwoord.get("additionalCodes") or []
    }
    rijen = []
    for m in antwoord.get("items") or []:
        past = geldt_voor_land(m, land)
        if past == "nee":
            continue
        mt = m.get("measureType") or {}
        area = m.get("geographicalArea") or {}
        type_id = str(mt.get("id", ""))
        rij = {
            "type": type_id,
            "omschrijving": tekst(mt.get("descriptions")),
            "land_of_groep": f"{area.get('id')} {tekst(area.get('descriptions')) or ''}".strip(),
            "heffing": tekst(m.get("dutyExpressions")),
            "code": m.get("commodityCode"),
            "vanaf": m.get("startDate"),
            "tot": m.get("endDate"),
            "nationaal": m.get("national"),
            "voorwaarden": bool(m.get("conditions")),
        }
        if past == "controleren":
            rij["let_op"] = f"Landengroep: controleer of {land} hiertoe behoort."
        if m.get("excludedCountryIds"):
            rij["uitgezonderd"] = m["excludedCountryIds"]
        if m.get("additionalCode") is not None:
            ac = str(m["additionalCode"])
            rij["aanvullende_code"] = ac
            rij["aanvullende_code_omschrijving"] = extra_codes.get(ac)
        nummer = contingent_nummer(m)
        if type_id in QUOTA_TYPES or nummer:
            rij["tariefcontingent"] = {
                "volgnummer": nummer,
                "soort": QUOTA_TYPES.get(type_id, "tariefcontingent"),
            }
        if m.get("certificates"):
            rij["certificaten"] = m["certificates"]
        if m.get("footnotes"):
            rij["voetnoten"] = m["footnotes"]
        overig = {k: v for k, v in m.items() if k not in KNOWN_FIELDS and v not in (None, [], {}, "")}
        if overig:
            rij["overig"] = overig
        rijen.append(rij)
    rijen = _zonder_dubbele_eu_rijen(rijen)
    return {
        "aantal_maatregelen": len(rijen),
        "tariefcontingenten": [r for r in rijen if "tariefcontingent" in r],
        "maatregelen": rijen,
    }


def zoek(code: str, land: str | None = None, datum: str | None = None, richting: str = "I") -> dict:
    """Alle maatregelen op `code` voor herkomst `land` op `datum`, samengevat, met bronlink."""
    code = normaliseer_code(code)
    datum = datum or dt.date.today().isoformat()
    dt.date.fromisoformat(datum)  # ValueError bij een onjuiste datum
    richting = richting.upper()
    if richting not in ("I", "E"):
        raise ValueError("Richting is I (invoer) of E (uitvoer).")
    land = land.upper().strip() if land else None
    if land and not re.fullmatch(r"[A-Z]{2}", land):
        raise ValueError("Land is een ISO-landcode van twee letters, bijvoorbeeld BR of US.")
    resultaat = vat_samen(haal_maatregelen(code, datum, richting), land)
    return {
        "goederencode": code, "land": land, "datum": datum, "richting": richting,
        "bron": website_url(code, datum, richting), **resultaat,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Heffingen en tariefcontingenten uit het Gebruikstarief.")
    p.add_argument("code", help="goederencode (GN/TARIC), bijv. 0207141000")
    p.add_argument("--land", help="ISO-code van het land van oorsprong, bijv. BR")
    p.add_argument("--datum", help="JJJJ-MM-DD, standaard vandaag")
    p.add_argument("--richting", default="I", help="I = invoer (standaard), E = uitvoer")
    p.add_argument("--ruw", action="store_true", help="toon het volledige antwoord van de dienst")
    a = p.parse_args(argv)
    try:
        if a.ruw:
            code = normaliseer_code(a.code)
            out = haal_maatregelen(code, a.datum or dt.date.today().isoformat(), a.richting.upper())
        else:
            out = zoek(a.code, a.land, a.datum, a.richting)
    except (ValueError, DouaneFout) as e:
        print(f"Fout: {e}", file=sys.stderr)
        return 1
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
