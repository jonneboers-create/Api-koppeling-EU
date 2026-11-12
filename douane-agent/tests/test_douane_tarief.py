"""Tests zonder netwerk. Het voorbeeldantwoord heeft de vorm van de ITE-dienst (zoals die in
Luxemburg is waargenomen); de waarden zijn verzonnen voor de test, geen echte tarieven."""

import json
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import douane_tarief as dt  # noqa: E402


def maatregel(type_id, omschr, area_id, area_omschr, heffing, **extra):
    return {
        "sid": 1, "national": False, "regulation": {"id": "R0001/00", "national": False},
        "commodityCode": "0207141000",
        "measureType": {"id": type_id, "descriptions": {"nl": omschr, "en": omschr}},
        "footnotes": [], "geographicalArea": {"id": area_id, "type": "G", "descriptions": {"nl": area_omschr}},
        "excludedCountryIds": [], "dutyExpressions": {"nl": heffing}, "conditions": False,
        "startDate": "2020-01-01", "certificates": [], "unreleased": False, **extra,
    }


ANTWOORD = {
    "count": 5,
    "items": [
        maatregel("103", "Recht derde landen", "1011", "ERGA OMNES", "102.4 EUR / 100 kg"),
        maatregel("143", "Preferentieel tariefcontingent", "BR", "Brazilië", "0.0000%", quotaOrderNumber="094213"),
        maatregel("122", "Niet-preferentieel tariefcontingent", "1011", "ERGA OMNES", "0.0000%",
                  excludedCountryIds=["UA"], orderNumber={"id": "094070"}),
        maatregel("142", "Tariefpreferentie", "2005", "SAP", "0.0000%"),
        maatregel("142", "Tariefpreferentie", "UA", "Oekraïne", "0.0000%"),
        maatregel("VAT", "Btw", "1010", "Europese Unie", "9.0000%", national=True),
    ],
    "additionalCodes": [],
}


class Normaliseer(unittest.TestCase):
    def test_punten_en_spaties_weg_en_aanvullen(self):
        self.assertEqual(dt.normaliseer_code("0207 14 10"), "0207141000")
        self.assertEqual(dt.normaliseer_code("0207.14.10.00"), "0207141000")

    def test_te_lang_of_leeg(self):
        with self.assertRaises(ValueError):
            dt.normaliseer_code("02071410001")
        with self.assertRaises(ValueError):
            dt.normaliseer_code("kip")


class Samenvatting(unittest.TestCase):
    def test_brazilie_krijgt_erga_omnes_en_eigen_contingent(self):
        s = dt.vat_samen(ANTWOORD, "BR")
        landen = [r["land_of_groep"] for r in s["maatregelen"]]
        self.assertIn("1011 ERGA OMNES", landen)
        self.assertIn("BR Brazilië", landen)
        self.assertNotIn("UA Oekraïne", landen)
        nummers = {r["tariefcontingent"]["volgnummer"] for r in s["tariefcontingenten"]}
        self.assertEqual(nummers, {"094213", "094070"})

    def test_uitgezonderd_land_valt_af(self):
        s = dt.vat_samen(ANTWOORD, "UA")
        nummers = {r["tariefcontingent"]["volgnummer"] for r in s["tariefcontingenten"]}
        self.assertNotIn("094070", nummers)

    def test_landengroep_wordt_gemarkeerd(self):
        s = dt.vat_samen(ANTWOORD, "BR")
        sap = next(r for r in s["maatregelen"] if r["land_of_groep"].startswith("2005"))
        self.assertIn("BR", sap["let_op"])

    def test_zonder_land_alles(self):
        self.assertEqual(dt.vat_samen(ANTWOORD)["aantal_maatregelen"], 6)

    def test_btw_op_eu_blijft_staan(self):
        s = dt.vat_samen(ANTWOORD, "BR")
        self.assertIn("9.0000%", [r["heffing"] for r in s["maatregelen"] if r["type"] == "VAT"])

    def test_dubbele_btw_rij_eu_en_erga_omnes_wordt_een(self):
        dubbel = dict(ANTWOORD, items=ANTWOORD["items"] + [
            maatregel("VAT", "Btw", "1011", "ERGA OMNES", "9.0000%", national=True)])
        btw = [r for r in dt.vat_samen(dubbel, "BR")["maatregelen"] if r["type"] == "VAT"]
        self.assertEqual(len(btw), 1)
        self.assertTrue(btw[0]["land_of_groep"].startswith("1011"))

    def test_onbekende_velden_blijven_bewaard(self):
        s = dt.vat_samen(ANTWOORD, "BR")
        br = next(r for r in s["maatregelen"] if r["land_of_groep"].startswith("BR"))
        self.assertEqual(br["overig"], {"quotaOrderNumber": "094213"})

    def test_geweigerde_code(self):
        s = dt.vat_samen({"fout": 400, "melding": "not declarable"}, "BR")
        self.assertIn("aangeefbare", s["fout"])


class Zoek(unittest.TestCase):
    def test_vraagt_juiste_url_en_geeft_bronlink(self):
        gezien = {}

        class Antw:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self, *a):
                return json.dumps(ANTWOORD).encode()

        def urlopen(req, timeout):
            gezien["url"] = req.full_url
            return Antw()

        with mock.patch.object(dt.urllib.request, "urlopen", urlopen):
            r = dt.zoek("0207.14.10", "br", "2026-11-11")
        self.assertIn("/mcc/measures?", gezien["url"])
        self.assertIn("commoditycode=0207141000", gezien["url"])
        self.assertIn("simulationdate=2026-11-11", gezien["url"])
        self.assertIn("tradedirection=I", gezien["url"])
        self.assertEqual(r["land"], "BR")
        self.assertIn("cc=0207141000", r["bron"])

    def test_foute_invoer(self):
        with self.assertRaises(ValueError):
            dt.zoek("0207141000", "Brazilië")
        with self.assertRaises(ValueError):
            dt.zoek("0207141000", "BR", "11-11-2026")


if __name__ == "__main__":
    unittest.main()
