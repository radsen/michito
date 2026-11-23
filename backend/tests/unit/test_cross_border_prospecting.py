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

    def setUp(self):
        from src.adapters.storage.deduplication_ledger import DeduplicationLedger
        self.ledger_path = "/tmp/test_xb_prospecting_ledger.json"
        if os.path.exists(self.ledger_path):
            os.remove(self.ledger_path)
        self.ledger = DeduplicationLedger(ledger_path=self.ledger_path)

    def test_calculate_lead_pricing_usd(self):
        """Verify USD and COP lead pricing in cents according to Scenario B with floor and courtesy rules"""
        # 10 leads, Tier 2 USD: 10 * 155 cents = 1550 cents ($15.50 USD)
        p10 = calculate_lead_pricing(10, tier=2, currency="USD")
        self.assertEqual(p10, 1550)

        # 50 leads, Tier 2 USD with 5% discount: 155 * 0.95 = 147 cents -> 50 * 147 = 7350 cents ($73.50 USD)
        p50 = calculate_lead_pricing(50, tier=2, currency="USD")
        self.assertEqual(p50, 7350)

        # 100 leads, Tier 2 USD with 10% discount: 155 * 0.90 = 139 cents -> 100 * 139 = 13900 cents ($139.00 USD)
        p100 = calculate_lead_pricing(100, tier=2, currency="USD")
        self.assertEqual(p100, 13900)

        # 10 leads, Tier 1 USD: 10 * 38 cents = 380 cents -> enforced minimum floor 625 cents ($6.25 USD)
        p_t1 = calculate_lead_pricing(10, tier=1, currency="USD")
        self.assertEqual(p_t1, 625)

        # 10 leads, Tier 3 USD: 10 * 375 cents = 3750 cents ($37.50 USD)
        p_t3 = calculate_lead_pricing(10, tier=3, currency="USD")
        self.assertEqual(p_t3, 3750)

        # Micro-batch courtesy rule: < 3 leads returns 0 cents to prevent payment gateway fee cannibalization
        p_courtesy = calculate_lead_pricing(2, tier=2, currency="USD")
        self.assertEqual(p_courtesy, 0)

        # COP minimum floor test: 10 Tier 1 leads = 1,500,000 cents -> enforced floor 2,500,000 cents ($25.000 COP)
        p_cop_floor = calculate_lead_pricing(10, tier=1, currency="COP")
        self.assertEqual(p_cop_floor, 2500000)

        # COP 100 leads Tier 2 with 10% discount: 100 * (620.000 * 0.90) = 55.800.000 cents ($558.000 COP)
        p_cop_100 = calculate_lead_pricing(100, tier=2, currency="COP")
        self.assertEqual(p_cop_100, 55800000)

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
            ledger=self.ledger,
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
            ledger=self.ledger,
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

    @patch.dict(os.environ, {"ALLOW_STATUTORY_FALLBACK": "true"})
    def test_run_fast_radar_scan_dominican_republic(self):
        """Verify radar scan returns Dominican Republic samples with RNC and 🇩🇴 flag"""
        from src.entrypoints.api.main import run_fast_radar_scan
        samples = run_fast_radar_scan(country="DO", city="Santo Domingo", limit=3)
        self.assertTrue(len(samples) >= 1)
        first = samples[0]
        self.assertEqual(first["country"], "DO")
        self.assertEqual(first["flag"], "🇩🇴")
        self.assertTrue(first["nit"].startswith("RNC"))

    @patch.dict(os.environ, {"ALLOW_STATUTORY_FALLBACK": "true"})
    def test_run_fast_radar_scan_chile_support(self):
        """Verify radar scan returns Chilean samples with RUT and 🇨🇱 flag"""
        from src.entrypoints.api.main import run_fast_radar_scan
        samples = run_fast_radar_scan(country="CL", city="Santiago", limit=3)
        self.assertTrue(len(samples) >= 1)
        first = samples[0]
        self.assertEqual(first["country"], "CL")
        self.assertEqual(first["flag"], "🇨🇱")
        self.assertTrue(first["nit"].startswith("RUT"))

    @patch.dict(os.environ, {"ALLOW_STATUTORY_FALLBACK": "true"})
    def test_run_fast_radar_scan_ecuador_support(self):
        """Verify radar scan returns Ecuador samples with RUC and 🇪🇨 flag"""
        from src.entrypoints.api.main import run_fast_radar_scan
        samples = run_fast_radar_scan(country="EC", city="Quito", limit=3)
        self.assertTrue(len(samples) >= 1)
        first = samples[0]
        self.assertEqual(first["country"], "EC")
        self.assertEqual(first["flag"], "🇪🇨")
        self.assertTrue(first["nit"].startswith("RUC"))


if __name__ == "__main__":
    unittest.main()
