import unittest
from unittest.mock import MagicMock, patch
from src.adapters.registries.ecuador.sercop_ecuador_adapter import SercopEcuadorAdapter


class TestSercopEcuadorAdapter(unittest.TestCase):
    def setUp(self):
        self.adapter = SercopEcuadorAdapter(timeout=2)

    def test_clean_phone_ecuador(self):
        # 0991234567 -> +593 99 123 4567
        self.assertEqual(self.adapter._clean_phone("0991234567"), "+593 99 123 4567")
        self.assertEqual(self.adapter._clean_phone("+593 98 765 4321"), "+593 98 765 4321")
        self.assertEqual(self.adapter._clean_phone("593981234567"), "+593 98 123 4567")
        self.assertEqual(self.adapter._clean_phone("No Provisto"), "")

    def test_role_determination(self):
        self.assertEqual(
            self.adapter._determine_representative_role("Carlos Lopez - Gerente General"),
            "Representante Legal / Gerencia"
        )
        self.assertEqual(
            self.adapter._determine_representative_role("Dr. Juan Perez - Apoderado Especial"),
            "Apoderado / Representación Legal"
        )
        self.assertEqual(
            self.adapter._determine_representative_role("Maria Gomez - Suplente"),
            "Representante Legal Suplente"
        )
        self.assertEqual(
            self.adapter._determine_representative_role("Elena Torres"),
            "Representante Legal (Firmante Estatutario)"
        )

    def test_bankrupt_and_placeholder_filtering(self):
        self.assertTrue(self.adapter._is_invalid_or_bankrupt("LIQUIDADOR: CARLOS LOPEZ"))
        self.assertTrue(self.adapter._is_invalid_or_bankrupt("REVISOR FISCAL"))
        self.assertTrue(self.adapter._is_invalid_or_bankrupt("No Registra"))
        self.assertFalse(self.adapter._is_invalid_or_bankrupt("Patricio Xavier Alarcon"))

    @patch("urllib.request.urlopen")
    def test_fetch_candidates_mocked_ocds(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"""{
            "data": [
                {
                    "supplier_name": "Soluciones Andinas S.A.",
                    "ruc": "1792998877001",
                    "representative_name": "Patricio Alarcon",
                    "email": "palarcon@solucionesandinas.ec",
                    "phone": "0994567890",
                    "contract_amount": 150000.0,
                    "procuring_entity": "Ministerio de Salud Publica",
                    "tender_title": "Adquisicion de Equipos Informaticos"
                }
            ]
        }"""
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        candidates = self.adapter.fetch_candidates(city="Quito", limit=1)
        self.assertEqual(len(candidates), 1)
        c = candidates[0]
        self.assertEqual(c["company_name"], "Soluciones Andinas S.A.")
        self.assertEqual(c["ruc"], "1792998877001")
        self.assertEqual(c["country"], "EC")
        self.assertEqual(c["currency"], "USD")
        self.assertEqual(c["contract_val_usd"], 150000.0)
        self.assertIn("$150,000 USD", c["contract_val_display"])
        self.assertEqual(c["phone"], "+593 99 456 7890")
        self.assertIn("ec.linkedin.com", c["linkedin_xray_url"])

    def test_fallback_candidates_seeds(self):
        candidates = self.adapter._get_fallback_candidates(city="Guayaquil")
        self.assertGreaterEqual(len(candidates), 3)
        self.assertEqual(candidates[0]["country"], "EC")
        self.assertEqual(candidates[0]["currency"], "USD")
        self.assertTrue(candidates[0]["ruc"].startswith("17") or candidates[0]["ruc"].startswith("09") or candidates[0]["ruc"].startswith("01"))
        self.assertTrue(candidates[0]["ruc"].endswith("001"))


if __name__ == "__main__":
    unittest.main()
