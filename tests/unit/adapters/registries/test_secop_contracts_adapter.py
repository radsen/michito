import unittest
from unittest.mock import MagicMock, patch
from src.adapters.registries.colombia.secop_contracts_adapter import SecopContractsAdapter

class TestSecopContractsAdapter(unittest.TestCase):
    def setUp(self):
        self.adapter = SecopContractsAdapter(timeout=2)

    def test_empty_summary_on_invalid_nit(self):
        res = self.adapter.fetch_contracts_summary("")
        self.assertFalse(res["has_contracts"])
        self.assertEqual(res["total_value_cop"], 0.0)

    @patch("urllib.request.urlopen")
    def test_fetch_contracts_summary_success(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = b"""[
            {
                "nombre_entidad": "MINISTERIO DE TRANSPORTE",
                "valor_del_contrato": "250000000",
                "descripcion_del_proceso": "Interventoria y consultoria tecnica de obra civil"
            },
            {
                "nombre_entidad": "ALCALDIA DE MEDELLIN",
                "valor_del_contrato": "150000000",
                "descripcion_del_proceso": "Desarrollo de sistemas de informacion"
            }
        ]"""
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        res = self.adapter.fetch_contracts_summary("900123456-1")
        self.assertTrue(res["has_contracts"])
        self.assertEqual(res["contracts_count"], 2)
        self.assertEqual(res["total_value_cop"], 400_000_000.0)
        self.assertEqual(res["top_contract_entity"], "Ministerio De Transporte")
        self.assertEqual(res["top_contract_value_cop"], 250_000_000.0)
        self.assertIn("Alto", res["intent_level"])

if __name__ == "__main__":
    unittest.main()

