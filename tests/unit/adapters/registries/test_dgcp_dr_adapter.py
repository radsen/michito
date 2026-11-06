import unittest
from unittest.mock import MagicMock, patch
from src.adapters.registries.dominican_republic.dgcp_dr_adapter import DgcpDrAdapter

class TestDgcpDrAdapter(unittest.TestCase):
    def setUp(self):
        self.adapter = DgcpDrAdapter(timeout=2)

    @patch("urllib.request.urlopen")
    def test_fetch_candidates_success(self, mock_urlopen):
        mock_contracts = MagicMock()
        mock_contracts.read.return_value = b"""{
            "payload": {
                "content": [
                    {
                        "rpe": 5151,
                        "razon_social": "Transver, SRL",
                        "valor_contratado": 55224,
                        "estado_contrato": "Activo",
                        "unidad_compra": "Comite de Retiro Policia",
                        "descripcion": "Mantenimiento preventivo"
                    }
                ]
            }
        }"""
        mock_contracts.__enter__.return_value = mock_contracts

        mock_prov = MagicMock()
        mock_prov.read.return_value = b"""{
            "payload": {
                "content": [
                    {
                        "rpe": 5151,
                        "razon_social": "Transver, SRL",
                        "numero_documento": "101142162",
                        "contacto": "Pedro Santos",
                        "posicion_contacto": "Gerente",
                        "correo_contacto": "psantos@transver.com.do",
                        "telefono_contacto": "809-565-4431",
                        "provincia": "DISTRITO NACIONAL",
                        "direccion": "Av. Lope de Vega 146"
                    }
                ]
            }
        }"""
        mock_prov.__enter__.return_value = mock_prov

        mock_urlopen.side_effect = [mock_contracts, mock_prov]

        candidates = self.adapter.fetch_candidates(city="Santo Domingo", limit=1)
        self.assertEqual(len(candidates), 1)
        c = candidates[0]
        self.assertEqual(c["company_name"], "Transver, SRL")
        self.assertEqual(c["rnc"], "101142162")
        self.assertEqual(c["decision_maker_name"], "Pedro Santos")
        self.assertEqual(c["email"], "psantos@transver.com.do")
        self.assertEqual(c["city"], "Santo Domingo")
        self.assertIn("55,224", c["contract_val_display"])
        self.assertIn("linkedin.com", c["linkedin_xray_url"])

    @patch("urllib.request.urlopen")
    def test_filter_out_non_executive_roles(self, mock_urlopen):
        mock_contracts = MagicMock()
        mock_contracts.read.return_value = b"""{
            "payload": {
                "content": [
                    {
                        "rpe": 5151,
                        "razon_social": "Acme, SRL",
                        "valor_contratado": 100000,
                        "estado_contrato": "Activo",
                        "unidad_compra": "Ministerio",
                        "descripcion": "Servicios"
                    }
                ]
            }
        }"""
        mock_contracts.__enter__.return_value = mock_contracts

        mock_prov = MagicMock()
        mock_prov.read.return_value = b"""{
            "payload": {
                "content": [
                    {
                        "rpe": 5151,
                        "razon_social": "Acme, SRL",
                        "numero_documento": "101142162",
                        "contacto": "Maria Gomez",
                        "posicion_contacto": "Encargada de Contabilidad",
                        "correo_contacto": "mgomez@acme.com.do",
                        "telefono_contacto": "809-565-4431"
                    }
                ]
            }
        }"""
        mock_prov.__enter__.return_value = mock_prov
        mock_urlopen.side_effect = [mock_contracts, mock_prov]

        candidates = self.adapter.fetch_candidates(city="Santo Domingo", limit=1)
        # Should be filtered out because contact is Encargada de Contabilidad
        self.assertEqual(len(candidates), 0)

    @patch("urllib.request.urlopen")
    def test_keyword_include_and_exclude_filtering(self, mock_urlopen):
        mock_contracts = MagicMock()
        mock_contracts.read.return_value = b"""{
            "payload": {
                "content": [
                    {
                        "rpe": 101,
                        "razon_social": "Auto Reparaciones, SRL",
                        "valor_contratado": 80000,
                        "estado_contrato": "Activo",
                        "unidad_compra": "Alcaldia",
                        "descripcion": "Reparacion de vehiculo y piezas"
                    },
                    {
                        "rpe": 202,
                        "razon_social": "TechSoft Dominicana, SRL",
                        "valor_contratado": 350000,
                        "estado_contrato": "Activo",
                        "unidad_compra": "Ministerio de Hacienda",
                        "descripcion": "Desarrollo de software y consultoria en nube"
                    }
                ]
            }
        }"""
        mock_contracts.__enter__.return_value = mock_contracts

        mock_prov = MagicMock()
        mock_prov.read.return_value = b"""{
            "payload": {
                "content": [
                    {
                        "rpe": 202,
                        "razon_social": "TechSoft Dominicana, SRL",
                        "numero_documento": "131000999",
                        "contacto": "Carlos Perez",
                        "posicion_contacto": "Gerente General",
                        "correo_contacto": "cperez@techsoft.com.do",
                        "telefono_contacto": "809-555-1234",
                        "provincia": "DISTRITO NACIONAL"
                    }
                ]
            }
        }"""
        mock_prov.__enter__.return_value = mock_prov
        mock_urlopen.side_effect = [mock_contracts, mock_prov]

        candidates = self.adapter.fetch_candidates(
            city="Santo Domingo",
            limit=5,
            include_keywords=["software", "tecnolog"],
            exclude_keywords=["vehiculo", "taller"]
        )
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["company_name"], "TechSoft Dominicana, SRL")

if __name__ == "__main__":
    unittest.main()

