"""Tests zonder netwerk; de rijen hebben de vorm uit de API-beschrijving (TaxudWeekData),
de waarden zijn verzonnen."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import haal_import as h  # noqa: E402


def rij(jaar, week, ms, partner, product, kg, eur, pref=100):
    return {"sector": "Poultry", "marketingYear": jaar, "week": week, "memberStateCode": ms,
            "memberStateName": ms, "partnerCode": partner, "partner": partner, "product": product,
            "cn8ProductCode": "02071410", "taric10ProductCode": "0207141010", "procedure": 1,
            "preference": pref, "euroValue": eur, "unitValue": None, "kg": kg,
            "kgEquivalent": kg, "coefficient": 1}


RIJEN = [
    rij("2024", 52, "NL", "BR", "Kipfilet", 1000, 3000),
    rij("2025", 1, "NL", "BR", "Kipfilet", 2000, 5000),
    rij("2025", 1, "DE", "BR", "Kipfilet", 500, 1500),
    rij("2025", 1, "NL", "UA", "Kipfilet", 800, 2000, pref=300),
    rij("2026", 1, "NL", "TH", "Bereid", 100, None),
]


class Sectoren(unittest.TestCase):
    def test_vindt_pluimvee_in_tekst_of_objecten(self):
        self.assertEqual(h.pluimveesectoren(["Beef", "Poultry", "Pigmeat"]), ["Poultry"])
        self.assertEqual(h.pluimveesectoren([{"sector": "Poultrymeat"}, {"sector": "Eggs"}]), ["Poultrymeat"])


class Overzichten(unittest.TestCase):
    def test_herkomst_telt_lidstaten_bij_elkaar(self):
        o = h.overzichten(RIJEN)
        br = [r for r in o["import_herkomst"] if r["partnerCode"] == "BR" and r["marketingYear"] == "2025"]
        self.assertEqual(len(br), 1)
        self.assertEqual(br[0]["kg"], 2500)
        self.assertEqual(br[0]["euroValue"], 6500)
        self.assertEqual(br[0]["euroPerKg"], 2.6)

    def test_lidstaat_telt_herkomstlanden_bij_elkaar(self):
        nl = [r for r in h.overzichten(RIJEN)["import_lidstaat"]
              if r["memberStateCode"] == "NL" and r["marketingYear"] == "2025"]
        self.assertEqual(nl[0]["kg"], 2800)

    def test_alleen_laatste_jaren(self):
        o = h.overzichten(RIJEN, jaren=2)
        self.assertEqual({r["marketingYear"] for r in o["import_herkomst"]}, {"2025", "2026"})

    def test_lege_waarde_telt_als_nul(self):
        th = next(r for r in h.overzichten(RIJEN)["import_herkomst"] if r["partnerCode"] == "TH")
        self.assertEqual(th["euroValue"], 0)

    def test_marktjaar_met_schuine_streep(self):
        self.assertEqual(h.marktjaar_sleutel("2025/2026"), 2025)


if __name__ == "__main__":
    unittest.main()
