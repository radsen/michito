import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Ensure backend directory and repo root are on sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
repo_root = os.path.abspath(os.path.join(backend_dir, ".."))
for p in [backend_dir, repo_root]:
    if p not in sys.path:
        sys.path.insert(0, p)

from src.application.use_cases.generate_prospects_use_case import GenerateProspectsUseCase
from src.entrypoints.workers.order_worker_daemon import calculate_lead_pricing


class TestCrossBorderProspecting(unittest.TestCase):
    """
    Test suite for Phase 3 (Cross-Border Multi-Country Quotas) and Phase 4 (Ecuador SERCOP Integration).
    """

    def test_calculate_lead_pricing_usd(self):
        """Verify USD lead pricing in cents for cross-border and Ecuador orders"""
        # 10 leads, Tier 2: 10 * 750 cents = 7500 cents ($75.00 USD)
        p10 = calculate_lead_pricing(10, tier=2, currency="USD")
        self.assertEqual(p10, 7500)

        # 50 leads, Tier 2 with 12% discount: 750 * 0.88 = 660 cents -> 50 * 660 = 33000 cents ($330.00 USD)
        p50 = calculate_lead_pricing(50, tier=2, currency="USD")
        self.assertEqual(p50, 33000)

        # 10 leads, Tier 1: 10 * 150 cents = 1500 cents ($15.00 USD)
        p_t1 = calculate_lead_pricing(10, tier=1, currency="USD")
        self.assertEqual(p_t1, 1500)

        # 10 leads, Tier 3: 10 * 1600 cents = 16000 cents ($160.00 USD)
        p_t3 = calculate_lead_pricing(10, tier=3, currency="USD")
        self.assertEqual(p_t3, 16000)

    @patch("src.application.use_cases.generate_prospects_use_case.SercopEcuadorAdapter")
    @patch("src.application.use_cases.generate_prospects_use_case.WebsiteAuditor")
    @patch("src.application.use_cases.generate_prospects_use_case.verify_mx")
    def test_ecuador_single_country_prospecting(self, mock_verify_mx, mock_auditor_cls, mock_harvester_cls):
        """Verify Ecuador-only prospecting pipeline with USD and 13-digit RUC"""
        mock_verify_mx.return_value = (True, "mail.ecuacloud.com")

        mock_auditor = MagicMock()
        mock_auditor.audit.return_value = (True, "https://www.ecuacloud.com", "Active Audited Site")
        mock_auditor_cls.return_value = mock_auditor

        mock_harvester = MagicMock()
        mock_harvester.fetch_candidates.return_value = [
            {
                "nit": "1792145890001",
                "ruc": "1792145890001",
                "company_name": "EcuaCloud Soluciones Tecnologicas C.A.",
                "city": "Quito",
                "department": "Pichincha",
                "address": "Av. Amazonas y República",
                "email": "gerencia@ecuacloud.com",
                "phone": "+593 99 876 5432",
                "decision_maker_name": "Carlos Mantilla",
                "decision_maker_title": "Gerente General",
                "sector": "Desarrollo de software y consultoría cloud",
                "tama_o_entidad": "Mediana",
                "contract_val_usd": 125000.0,
                "contract_val_display": "$125,000 USD",
                "contract_entity": "Ministerio de Telecomunicaciones",
                "contract_object": "Migración de infraestructura gubernamental",
                "linkedin_xray_url": "https://google.com/search?q=site:ec.linkedin.com",
            }
        ]
        mock_harvester_cls.return_value = mock_harvester

        use_case = GenerateProspectsUseCase(
            harvester_ec=mock_harvester,
            verify_mx_fn=mock_verify_mx,
        )

        res = use_case.execute(
            campaign="tinkko_ec_offices",
            country="EC",
            city="Quito",
            limit=1,
            dry_run=True,
            output_format="both",
        )

        self.assertEqual(res["status"], "success")
        self.assertEqual(res["country"], "EC")
        self.assertEqual(res["currency"], "USD")
        self.assertEqual(res["total_qualified"], 1)

        lead = res["leads"][0]
        self.assertEqual(lead["country"], "EC")
        self.assertEqual(lead["tax_id_type"], "RUC")
        self.assertEqual(lead["nit"], "1792145890001")
        self.assertIn("SuperCias", lead["segment_name"])
        self.assertIn("USD", lead["revenue_bracket"])

        # Check sample teaser formatting
        teaser = res["sample_teaser"][0]
        self.assertEqual(teaser["flag"], "🇪🇨")
        self.assertEqual(teaser["country"], "EC")
        self.assertTrue(teaser["phone"].startswith("+593 9"))

    @patch("src.application.use_cases.generate_prospects_use_case.SecopHarvesterAdapter")
    @patch("src.application.use_cases.generate_prospects_use_case.DgcpDrAdapter")
    @patch("src.application.use_cases.generate_prospects_use_case.SercopEcuadorAdapter")
    @patch("src.application.use_cases.generate_prospects_use_case.WebsiteAuditor")
    @patch("src.application.use_cases.generate_prospects_use_case.verify_mx")
    def test_cross_border_multi_country_allocations(
        self, mock_verify_mx, mock_auditor_cls, mock_ec_cls, mock_dr_cls, mock_co_cls
    ):
        """Verify multi-country cross-border batch with allocated quotas (50% CO, 30% DO, 20% EC)"""
        mock_verify_mx.return_value = (True, "mail.server.net")

        mock_auditor = MagicMock()
        mock_auditor.audit.return_value = (True, "https://www.corporate.com", "Active Audited Site")
        mock_auditor_cls.return_value = mock_auditor

        # Mock CO Harvester
        mock_co = MagicMock()
        mock_co.fetch_candidates.return_value = [
            {
                "nit": "900123456-1",
                "company_name": "Andina Logistica SAS",
                "city": "Medellín",
                "department": "Antioquia",
                "address": "Cra 43A # 1-50",
                "email": "contacto@andinalogistica.co",
                "phone": "+57 310 456 7890",
                "decision_maker_name": "Juan Camilo Restrepo",
                "decision_maker_title": "Representante Legal",
                "sector": "Transporte y almacenamiento",
                "tama_o_entidad": "Mediana",
            }
        ]

        # Mock DR Harvester
        mock_dr = MagicMock()
        mock_dr.fetch_candidates.return_value = [
            {
                "nit": "131888999",
                "rnc": "131888999",
                "company_name": "Caribe Tech SRL",
                "city": "Santo Domingo",
                "department": "Distrito Nacional",
                "address": "Av. Winston Churchill",
                "email": "contacto@caribetech.do",
                "phone": "+1 (809) 555-8899",
                "decision_maker_name": "Elena Tavarez",
                "decision_maker_title": "Gerente General",
                "sector": "Servicios de tecnología",
                "tama_o_entidad": "Mediana",
                "contract_val_dop": 250000.0,
                "contract_val_display": "$250,000 DOP",
                "contract_entity": "DGII",
                "contract_object": "Renovación de servidores",
            }
        ]

        # Mock EC Harvester
        mock_ec = MagicMock()
        mock_ec.fetch_candidates.return_value = [
            {
                "nit": "1791112220001",
                "ruc": "1791112220001",
                "company_name": "Pichincha Constructora C.A.",
                "city": "Quito",
                "department": "Pichincha",
                "address": "Av. 12 de Octubre",
                "email": "contacto@pichinchaconst.ec",
                "phone": "+593 98 111 2233",
                "decision_maker_name": "Diego Noboa",
                "decision_maker_title": "Presidente Ejecutivo",
                "sector": "Construcción de obras de ingeniería",
                "tama_o_entidad": "Grande",
                "contract_val_usd": 500000.0,
                "contract_val_display": "$500,000 USD",
                "contract_entity": "Municipio de Quito",
                "contract_object": "Construcción paso elevado",
            }
        ]

        use_case = GenerateProspectsUseCase(
            harvester_co=mock_co,
            harvester_dr=mock_dr,
            harvester_ec=mock_ec,
            verify_mx_fn=mock_verify_mx,
        )

        res = use_case.execute(
            campaign="eventos_ferias_b2b",
            limit=3,
            country="MULTI",
            country_allocations={"CO": 1, "DO": 1, "EC": 1},
            dry_run=True,
            output_format="both",
        )

        self.assertEqual(res["status"], "success")
        self.assertEqual(res["country"], "MULTI")
        self.assertEqual(res["currency"], "USD")
        self.assertEqual(res["total_qualified"], 3)

        countries_in_leads = [lead["country"] for lead in res["leads"]]
        self.assertIn("CO", countries_in_leads)
        self.assertIn("DO", countries_in_leads)
        self.assertIn("EC", countries_in_leads)

        # Check Teaser covers all 3 countries
        teaser_countries = [t["country"] for t in res["sample_teaser"]]
        self.assertEqual(len(teaser_countries), 3)
        self.assertIn("CO", teaser_countries)
        self.assertIn("DO", teaser_countries)
        self.assertIn("EC", teaser_countries)


if __name__ == "__main__":
    unittest.main()
