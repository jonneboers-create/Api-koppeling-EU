# AI-ideeënfunnel

Overzicht van alle AI-ideeën binnen Luiten Food: in welke fase een idee zit, wie het oppakt en hoe het scoort op impact en inspanning.

**Live (gedeeld):** https://claude.ai/artifact/BXTKunuiyL1WPjLKtLJDFX

## Fasen

| Fase | Betekenis |
|---|---|
| Ingediend | Idee is geopperd en vastgelegd |
| Beoordeling | Waarde, haalbaarheid, data en AVG worden bekeken |
| Geprioriteerd | Goedgekeurd, wacht op capaciteit om te starten |
| Pilot | Proef met een kleine groep gebruikers |
| Implementatie | Uitrol, training en borging in het werkproces |
| In gebruik | Draait in de praktijk, resultaat wordt gemeten |
| Geparkeerd | Gestopt of on hold, met reden (zijspoor) |

## Prioriteit

Per idee worden **impact** (1 minimaal – 5 zeer groot) en **inspanning** (1 uren – 5 kwartalen) ingeschat.

- **Score** = impact × (6 − inspanning), van 1 tot 25
- **Quick win**: impact ≥ 4 en inspanning ≤ 2
- **Strategisch project**: impact ≥ 4 en inspanning ≥ 3
- **Kleine verbetering**: impact ≤ 3 en inspanning ≤ 2
- **Heroverwegen**: impact ≤ 3 en inspanning ≥ 3

Ideeën die langer dan 45 dagen in dezelfde fase staan (behalve In gebruik en Geparkeerd) worden oranje gemarkeerd.

## Weergaven

- **Funnel-bord**: kolom per fase, kaarten verschuiven met ‹ ›
- **Prioriteitenlijst**: open ideeën gerangschikt op score, te kopiëren naar Excel
- **Impact × inspanning**: 5×5-matrix met quick wins linksboven

## Techniek

Eén bestand: `index.html` (geen build, geen libraries). Binnen claude.ai slaat de pagina ideeën op in de gedeelde database van het artifact (collectie `ideas`), live bijgewerkt voor alle kijkers. Lokaal geopend valt hij terug op opslag in de browser.
