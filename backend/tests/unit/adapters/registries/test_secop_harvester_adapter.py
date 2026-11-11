import unittest
from unittest.mock import patch, MagicMock
from src.adapters.registries.colombia.secop_harvester_adapter import SecopHarvesterAdapter

class TestSecopHarvesterAdapter(unittest.TestCase):
    def setUp(self):
        self.adapter = SecopHarvesterAdapter(timeout=5)

    def test_clean_phone(self):
        self.assertEqual(self.adapter._clean_phone("+57 300 123 4567"), "3001234567")
        self.assertEqual(self.adapter._clean_phone("573001234567"), "3001234567")
        self.assertEqual(self.adapter._clean_phone("300-123-4567"), "3001234567")
        self.assertEqual(self.adapter._clean_phone("No Provisto"), "")
        self.assertEqual(self.adapter._clean_phone(""), "")

    def test_is_valid_email(self):
        self.assertTrue(self.adapter._is_valid_email("gerencia@empresa.com.co"))
        self.assertTrue(self.adapter._is_valid_email("carlos.gomez@gmail.com"))
        self.assertFalse(self.adapter._is_valid_email("No Provisto"))
        self.assertFalse(self.adapter._is_valid_email("invalid-email"))
        self.assertFalse(self.adapter._is_valid_email(""))

    @patch("urllib.request.urlopen")
    def test_fetch_candidates_mocked(self, mock_urlopen):
        sample_response = [
            {
                "nombre": "EMPRESA ALPHA S.A.S.",
                "nit": "900.123.456-1",
                "nombre_representante_legal": "JUAN PEREZ",
                "correo_representante_legal": "juan.perez@alpha.com",
                "telefono_representante_legal": "3001234567",
                "municipio": "Medellín",
                "departamento": "Antioquia",
                "direccion": "Calle 10 # 40-20",
                "sitio_web": "www.alpha.com",
                "tipo_empresa": "Sociedad por acciones simplificada",
                "descripcion_categoria_principal": "Servicios de Tecnología",
            },
            {
                # Should be filtered out: representative name is identical to company name
                "nombre": "EMPRESA BETA S.A.S.",
                "nit": "900.654.321-2",
                "nombre_representante_legal": "EMPRESA BETA S.A.S.",
                "correo_representante_legal": "beta@beta.com",
                "municipio": "Medellín",
            },
            {
                # Should be filtered out: invalid email
                "nombre": "EMPRESA GAMMA S.A.S.",
                "nit": "900.999.888-3",
                "nombre_representante_legal": "MARIA GOMEZ",
                "correo_representante_legal": "No Provisto",
                "municipio": "Medellín",
            }
        ]

        mock_resp = MagicMock()
        mock_resp.read.return_value = str(sample_response).replace("'", '"').encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        candidates = self.adapter.fetch_candidates(city="Medellín", limit=10)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["company_name"], "EMPRESA ALPHA S.A.S.")
        self.assertEqual(candidates[0]["decision_maker_name"], "Juan Perez")
        self.assertEqual(candidates[0]["email"], "juan.perez@alpha.com")
        self.assertEqual(candidates[0]["phone"], "3001234567")
        self.assertEqual(candidates[0]["company_id"], "CO-900123456")

    @patch("urllib.request.urlopen")
    def test_fetch_candidates_department_and_nationwide_routing(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"[]"
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        # Test Department Routing
        self.adapter.fetch_candidates(city="Antioquia", limit=5)
        req_antioquia = mock_urlopen.call_args[0][0]
        self.assertIn("departamento=Antioquia", req_antioquia.full_url)
        self.assertNotIn("municipio", req_antioquia.full_url)

        # Test Nationwide Routing (e.g. "🇨🇴 Toda Colombia")
        self.adapter.fetch_candidates(city="🇨🇴 Toda Colombia", limit=5)
        req_nationwide = mock_urlopen.call_args[0][0]
        self.assertNotIn("departamento", req_nationwide.full_url)
        self.assertNotIn("municipio", req_nationwide.full_url)

    def test_fallback_candidates_department_assignment(self):
        fallbacks = self.adapter._get_fallback_candidates(city="Valle del Cauca")
        self.assertGreater(len(fallbacks), 0)
        self.assertEqual(fallbacks[0]["departamento"], "Valle del Cauca")

if __name__ == "__main__":
    unittest.main()

