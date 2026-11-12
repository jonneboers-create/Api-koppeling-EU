# EU-import pluimvee

Haalt de wekelijkse invoer van pluimvee in de hele EU op uit de openbare API van het
[Agri-food data portal](https://agridata.ec.europa.eu/extensions/DataPortal/API_Documentation.html)
van de Europese Commissie (gegevens van TAXUD, het directoraat douane), voor het live dashboard
**EU-import pluimvee** in claude.ai.

```bash
python haal_import.py              # schrijft uitvoer/import_herkomst.json en uitvoer/import_lidstaat.json
python haal_import.py --sectoren   # welke sectoren de API kent
```

Geen sleutel of login nodig. Per rij geeft de API onder meer: marktjaar, week, lidstaat,
herkomstland, product, GN8- en TARIC10-code, preferentie, waarde in euro en gewicht in kg.
Het script telt dat op tot:

| Bestand | Per | Waarden |
|---|---|---|
| `import_herkomst.json` | marktjaar, week, herkomstland, product, preferentie | kg, euro, euro/kg |
| `import_lidstaat.json` | marktjaar, week, lidstaat, product | kg, euro, euro/kg |

## Niet in de API

De **TRQ-toewijzingscoëfficiënten** staan alleen in het
[dashboard](https://agridata.ec.europa.eu/extensions/DashboardTaxud/TrqAllocationCoefficients.html),
niet in de API. Exporteer ze daar naar Excel, of vraag de helpdesk
(agri-ext-helpdesk@ec.europa.eu) om een bestand of API.

## Tests

```bash
python -m unittest discover -s tests
```
