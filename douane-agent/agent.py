"""Douane-tariefagent: stel in gewone taal een vraag over invoer, krijg de kosten en de TRQ.

    python agent.py
    > Wat kost het om 20 ton bevroren kipfilet uit Brazilië in te voeren, en is er een TRQ?

De agent zoekt de goederencode, haalt de maatregelen op bij tarief.douane.nl (via
douane_tarief.py) en rekent de heffing voor je uit. Vereist ANTHROPIC_API_KEY (of `ant auth login`).
"""

from __future__ import annotations

import datetime as dt
import json
import sys

import anthropic
from anthropic import beta_tool

import douane_tarief

MODEL = "claude-opus-5-5"

SYSTEM = """Je bent een douane-tariefassistent voor een Nederlands levensmiddelenbedrijf.
Je beantwoordt vragen over invoer in de EU via Nederland: wat het kost (invoerrecht, btw,
accijns, antidumping, aanvullende rechten) en onder welk tariefcontingent (TRQ) het kan vallen.

Werkwijze:
1. Bepaal de goederencode van tien cijfers (GN/TARIC). Weet je de code niet zeker, noem dan de
   code die je aanneemt met een korte reden, en controleer hem met de tool: een code die de
   douane weigert, is niet aangeefbaar; probeer dan een fijnere of andere code.
2. Vraag de maatregelen op met `zoek_maatregelen`, met het land van oorsprong als ISO-code.
   Gebruik alleen wat de tool teruggeeft voor tarieven en contingentnummers: verzin nooit een
   tarief of volgnummer. Geeft de tool een fout, zeg dat dan eerlijk.
3. Rijen met `let_op` gelden voor een landengroep (bijv. SAP/GSP, een handelsakkoord): ga na of
   het land daar lid van is en zeg erbij als je dat niet zeker weet.
4. Antwoord in het Nederlands met:
   - de goederencode en omschrijving;
   - het recht derde landen (ERGA OMNES) en, als die er zijn, preferentiële tarieven voor het land
     (met de oorsprongsvoorwaarde, bijv. bewijs van oorsprong);
   - elk tariefcontingent: volgnummer (09.xxxx), het tarief binnen het contingent en voor wie;
   - btw en andere heffingen;
   - als de gebruiker een hoeveelheid of waarde noemt: een voorbeeldberekening met de
     formule zichtbaar (bijv. 12,8% x douanewaarde + EUR 303,40 per 100 kg). Ontbreekt de
     douanewaarde, reken dan met een aanname en zeg dat;
   - de bronlink naar tarief.douane.nl zodat men het kan nakijken.
5. Of er in een contingent nog saldo is, staat niet in dit antwoord; verwijs daarvoor naar het
   contingentoverzicht van de douane of de TARIC-quotaconsultatie van de Europese Commissie.

Houd het kort en zakelijk. Dit is een hulpmiddel, geen bindend douaneadvies (dat is een BTI)."""


@beta_tool
def zoek_maatregelen(goederencode: str, land: str = "", datum: str = "", richting: str = "I") -> str:
    """Haal alle douanemaatregelen op voor een goederencode bij het Gebruikstarief (tarief.douane.nl):
    invoerrechten, preferentiële tarieven, tariefcontingenten (TRQ) met volgnummer, btw, accijns en
    antidumping. Rijen die niet voor het opgegeven land gelden, zijn al weggefilterd.

    Args:
        goederencode: GN/TARIC-code, bij voorkeur tien cijfers, bijv. 0207141000. Korter wordt aangevuld met nullen.
        land: ISO-landcode van het land van oorsprong (twee letters, bijv. BR, US, UA). Leeg = alle landen.
        datum: Datum JJJJ-MM-DD waarop de invoer plaatsvindt. Leeg = vandaag.
        richting: I voor invoer (standaard) of E voor uitvoer.
    """
    try:
        res = douane_tarief.zoek(goederencode, land or None, datum or None, richting or "I")
    except (ValueError, douane_tarief.DouaneFout) as e:
        return f"Fout: {e}"
    return json.dumps(res, ensure_ascii=False)


def beantwoord(client: anthropic.Anthropic, history: list) -> str:
    """Laat de agent de laatste vraag in `history` afhandelen; vult `history` aan met de beurten."""
    runner = client.beta.messages.tool_runner(
        model=MODEL,
        max_tokens=16000,
        system=f"{SYSTEM}\n\nVandaag is het {dt.date.today().isoformat()}.",
        thinking={"type": "adaptive"},
        output_config={"effort": "medium"},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        tools=[zoek_maatregelen],
        messages=list(history),
    )
    laatste = None
    for message in runner:
        laatste = message
        history.append({"role": "assistant", "content": message.content})
        for block in message.content:
            if block.type == "tool_use":
                print(f"  … {block.name}({json.dumps(block.input, ensure_ascii=False)})", file=sys.stderr)
        tool_response = runner.generate_tool_call_response()
        if tool_response is not None:
            history.append(tool_response)
    if laatste is None:
        return ""
    if laatste.stop_reason == "refusal":
        return "(Het model weigerde deze vraag te beantwoorden.)"
    return "".join(b.text for b in laatste.content if b.type == "text")


def main() -> int:
    client = anthropic.Anthropic()
    history: list = []
    vragen = sys.argv[1:]
    if vragen:  # eenmalige vraag: python agent.py "wat kost ..."
        history.append({"role": "user", "content": " ".join(vragen)})
        print(beantwoord(client, history))
        return 0
    print("Douane-tariefagent. Stel je vraag (leeg of 'stop' om te stoppen).")
    while True:
        try:
            vraag = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not vraag or vraag.lower() in ("stop", "exit", "quit"):
            return 0
        begin = len(history)
        history.append({"role": "user", "content": vraag})
        try:
            print("\n" + beantwoord(client, history))
        except anthropic.APIConnectionError as e:
            print(f"Geen verbinding met de Claude API: {e}")
            del history[begin:]
        except anthropic.APIStatusError as e:
            print(f"Claude API-fout {e.status_code}: {e.message}")
            del history[begin:]


if __name__ == "__main__":
    sys.exit(main())
