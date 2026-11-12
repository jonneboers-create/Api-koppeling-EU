# Douane-tariefagent

Stel in gewone taal een vraag over invoer en krijg terug wat het kost en welk tariefcontingent
(TRQ) geldt. De gegevens komen live uit het [Gebruikstarief van de Douane](https://tarief.douane.nl/ite-tariff-public/#/taric/nomenclature/sbn).

```
> Wat kost het om 20 ton bevroren kipfilet uit Brazilië in te voeren, en is er een TRQ?
```

De agent bepaalt de goederencode, haalt alle maatregelen op (recht derde landen, preferenties,
tariefcontingenten met volgnummer, btw, accijns, antidumping), rekent een voorbeeld uit en geeft
de link naar tarief.douane.nl om na te kijken.

## Gebruik

Er zijn twee manieren; beide gebruiken `douane_tarief.py` om de douane te bevragen.

**1. Losse agent (Python + Claude API)**

```bash
cd douane-agent
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...        # of: ant auth login
python agent.py                     # chat
python agent.py "Welke TRQ geldt voor rundvlees uit Argentinië?"   # één vraag
```

**2. In Claude Code** — in deze repository staat de agent `douane-tarief`
(`.claude/agents/douane-tarief.md`). Vraag in Claude Code bijvoorbeeld:
*"Vraag de douane-tarief agent wat invoer van knoflook uit China kost."*

**Alleen de gegevens, zonder AI**

```bash
python douane_tarief.py 0207141000 --land BR             # samenvatting als JSON
python douane_tarief.py 0207141000 --land BR --ruw       # volledig antwoord van de dienst
```

## Hoe het werkt

De website van de Douane is een app boven op een openbare JSON-dienst (geen login). Dezelfde
software (ITE Tariff) draait in Luxemburg, waar de dienst bekend is:
`…/ite-tariff-public-proxy/ite-tariff-trusted-rs/v1/mcc/measures`. We gaan uit van hetzelfde
pad op `tarief.douane.nl`. Werkt dat niet, zoek dan in de browser (F12 → Netwerk) het verzoek dat
de site doet bij het opzoeken van een code, en zet het begin van die URL in `DOUANE_API_BASE`:

```bash
export DOUANE_API_BASE=https://tarief.douane.nl/<pad>/v1
```

Tariefcontingenten herkent het script aan het maatregeltype (122, 123, 143, 146, 147, 653, 654)
of aan een veld met het volgnummer. Velden die het niet kent, gaan ongewijzigd mee onder
`overig`, zodat de agent ze toch ziet.

## Beperkingen

- Het **saldo** van een contingent (hoeveel er nog over is) komt niet uit deze dienst; zie
  de TARIC-quotaconsultatie van de Europese Commissie.
- Bij **landengroepen** (bijv. SAP/GSP, handelsakkoorden) markeert het script de rij met
  `let_op`; de agent beoordeelt dan of het land lid is.
- Geen bindend advies: voor zekerheid over de indeling vraag je een BTI aan.

## Tests

```bash
python -m unittest discover -s tests
```
