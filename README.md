# API-koppeling-EU

Koppelingen met openbare gegevens van de EU en de Douane over invoer van voedingsmiddelen.

| Map | Wat | Status |
|---|---|---|
| [`agridata-import/`](agridata-import/README.md) | Haalt de wekelijkse EU-invoer van pluimvee (TAXUD) op uit de API van het Agri-food data portal van de Europese Commissie, voor het dashboard [EU-import pluimvee](https://claude.ai/artifact/Wn5mewCbed4e9MJ291mvpc). | Klaar. De API van de Commissie was op 12-11-2026 tijdelijk buiten werking, dus het dashboard toont nog voorbeeldcijfers. |
| [`douane-agent/`](douane-agent/README.md) | Agent die invoerkosten en tariefcontingenten (TRQ) opzoekt in het Gebruikstarief van de Douane (tarief.douane.nl). | Werkt nog niet: de server van de Douane weigert verzoeken die niet uit een browser komen. |

Voor Claude Code staat er ook een agent `douane-tarief` in `.claude/agents/`.

## Tests

```bash
python -m unittest discover -s agridata-import/tests
python -m unittest discover -s douane-agent/tests
```
