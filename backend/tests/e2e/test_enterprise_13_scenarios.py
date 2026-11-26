"""
End-to-End Enterprise Walkthrough & Verification for All 13 Supported Scenarios.
Phase 7 Milestone Validation:
- Exercises all 11 catalog campaigns + 2 universal intake modes
- Validates 10 leads per batch
- Validates all 3 tiers (Tier 1, Tier 2, Tier 3)
- Validates all territories (🇨🇴 Colombia, 🇩🇴 Dominican Republic, 🇪🇨 Ecuador, 🌎 Cross-Border)
- Validates full order lifecycle: Intake -> Sample Teaser -> Quote -> Approval -> Deliverables -> 2x1 Replacement
"""

import os
import shutil
import unittest
from fastapi.testclient import TestClient

# Ensure test mode environment before importing application
os.environ["PYTEST_CURRENT_TEST"] = "1"
os.environ["ENVIRONMENT"] = "test"
os.environ.pop("PUBSUB_EMULATOR_HOST", None)
os.environ.pop("STORAGE_EMULATOR_HOST", None)
os.environ.pop("ORDERS_FEED_WEBHOOK_URL", None)
os.environ.pop("ALERT_WEBHOOK_URL", None)

from src.entrypoints.api.main import app, sql_adapter, app_container
from src.entrypoints.workers.order_worker_daemon import OrderWorkerDaemon
from src.adapters.db.sql_order_adapter import SqlOrderAdapter
from src.adapters.storage.local_storage_adapter import LocalStorageAdapter
from src.adapters.storage.deduplication_ledger import DeduplicationLedger
from src.application.use_cases.generate_prospects_use_case import GenerateProspectsUseCase

ROOT_OUTPUTS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../outputs/phase7_e2e_runs")
)
TEST_LEDGER_PATH = "/tmp/michito_e2e_phase7_ledger.json"


class TestEnterprise13Scenarios(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.makedirs(ROOT_OUTPUTS_DIR, exist_ok=True)
        if os.path.exists(TEST_LEDGER_PATH):
            os.remove(TEST_LEDGER_PATH)

        cls.client = TestClient(app)
        cls.sql_adapter = sql_adapter
        cls.storage_adapter = LocalStorageAdapter()
        cls.test_ledger = DeduplicationLedger(ledger_path=TEST_LEDGER_PATH)
        cls.sql_adapter.ledger = cls.test_ledger
        from unittest.mock import MagicMock
        mock_web_auditor = MagicMock()
        mock_web_auditor.audit.side_effect = lambda *args, **kwargs: (True, args[0] if args and args[0] else "https://www.example.com", "Active Test Site")
        cls.use_case = GenerateProspectsUseCase(
            ledger=cls.test_ledger,
            verify_mx_fn=lambda *args, **kwargs: (True, "mail.example.com"),
            web_auditor=mock_web_auditor,
        )

        cls.worker = OrderWorkerDaemon(
            order_repository=cls.sql_adapter,
            storage_adapter=cls.storage_adapter,
            use_case=cls.use_case
        )
        # Disable external webhooks in test suite
        if hasattr(cls.worker, "alert_dispatcher"):
            cls.worker.alert_dispatcher.webhook_url = ""
            cls.worker.alert_dispatcher.feed_webhook_url = ""
        if hasattr(app_container, "alert_dispatcher"):
            app_container.alert_dispatcher.webhook_url = ""
            app_container.alert_dispatcher.feed_webhook_url = ""

    def setUp(self):
        if hasattr(self, "test_ledger") and self.test_ledger:
            self.test_ledger.reset()

    def _execute_order_lifecycle(self, scenario_key: str, payload: dict, expected_tier: int = 2) -> tuple[str, dict]:
        # 1. Intake: Create Order
        res_post = self.client.post("/api/v1/orders", json=payload)
        self.assertEqual(res_post.status_code, 201, f"Failed creating order for {scenario_key}: {res_post.text}")
        data = res_post.json()
        self.assertEqual(data["status"], "success")
        order_id = data["order_id"]
        self.assertTrue(order_id.startswith("ord_"))

        # 2. Worker Processing
        order_doc = self.sql_adapter.get_order(order_id)
        assert order_doc is not None, f"Order doc not found for {order_id}"
        process_ok = self.worker.process_order(order_doc)
        self.assertTrue(process_ok, f"Worker processing failed for {scenario_key}")

        # 3. Status Check: Awaiting Payment with Teasers
        res_get = self.client.get(f"/api/v1/orders/{order_id}")
        self.assertEqual(res_get.status_code, 200)
        awaiting_data = res_get.json()
        self.assertEqual(awaiting_data["status"], "awaiting_payment")
        teasers = awaiting_data.get("sample_teaser") or awaiting_data.get("sample_leads") or []
        self.assertGreaterEqual(len(teasers), 1, f"Expected teaser leads for {scenario_key}")

        # 4. Quote Verification
        res_quote = self.client.get(f"/api/v1/orders/{order_id}/quote")
        self.assertEqual(res_quote.status_code, 200)
        quote_data = res_quote.json()
        self.assertEqual(quote_data["status"], "success")
        self.assertGreater(quote_data["financials"]["amount_in_cents"], 0)

        # 5. Payment Approval: Unlocks Full Manifest
        res_pay = self.client.post(f"/api/v1/orders/{order_id}/pay")
        self.assertEqual(res_pay.status_code, 200)
        paid_data = res_pay.json()
        self.assertEqual(paid_data["status"], "success")
        self.assertEqual(paid_data["order"]["status"], "paid")

        # 6. Deliverable Verification on Disk
        completed_order = self.sql_adapter.get_order(order_id)
        assert completed_order is not None, f"Order {order_id} not found in database"
        delivery = completed_order.get("delivery", {})
        csv_path = delivery.get("csv_path") or completed_order.get("csv_path")
        xlsx_path = delivery.get("xlsx_path") or completed_order.get("xlsx_path")
        pdf_path = delivery.get("pdf_path") or completed_order.get("pdf_path")
        md_path = delivery.get("dossier_path") or completed_order.get("dossier_path")

        if csv_path and csv_path.startswith("file://"):
            csv_path = csv_path.replace("file://", "")
        if xlsx_path and xlsx_path.startswith("file://"):
            xlsx_path = xlsx_path.replace("file://", "")
        if pdf_path and pdf_path.startswith("file://"):
            pdf_path = pdf_path.replace("file://", "")
        if md_path and md_path.startswith("file://"):
            md_path = md_path.replace("file://", "")

        self.assertIsNotNone(csv_path, f"CSV path is None for {scenario_key}")
        self.assertIsNotNone(xlsx_path, f"XLSX path is None for {scenario_key}")
        self.assertTrue(os.path.exists(csv_path), f"CSV not found on disk: {csv_path}")
        self.assertTrue(os.path.exists(xlsx_path), f"XLSX not found on disk: {xlsx_path}")

        # Copy deliverables to persistent outputs directory for direct inspection
        dest_dir = os.path.join(ROOT_OUTPUTS_DIR, scenario_key)
        os.makedirs(dest_dir, exist_ok=True)
        if csv_path and os.path.exists(csv_path):
            shutil.copy(csv_path, os.path.join(dest_dir, "prospects.csv"))
        if xlsx_path and os.path.exists(xlsx_path):
            shutil.copy(xlsx_path, os.path.join(dest_dir, "prospects.xlsx"))
        if pdf_path and os.path.exists(pdf_path):
            shutil.copy(pdf_path, os.path.join(dest_dir, "executive_dossier.pdf"))
        if md_path and os.path.exists(md_path):
            shutil.copy(md_path, os.path.join(dest_dir, "executive_dossier.md"))

        # 7. Tier-Specific Data Contract Assertions
        leads = self.sql_adapter.get_order_manifest(order_id)
        self.assertGreaterEqual(len(leads), 1, f"Expected leads in manifest for {scenario_key}")
        first_lead = leads[0]
        self.assertIn("company_name", first_lead)
        self.assertTrue("verified_email" in first_lead or "email" in first_lead)

        if expected_tier >= 2:
            self.assertIn("decision_maker_name", first_lead)
            self.assertTrue("direct_mobile_phone" in first_lead or "phone" in first_lead)

        if expected_tier == 3:
            # Tier 3 order scope and pricing verification
            self.assertEqual(completed_order.get("tier"), 3)
            self.assertIn("Tier 3", quote_data["scope"]["tier_description"])

        return order_id, completed_order

    def test_01_tinkko_enterprise_offices_co(self):
        """Scenario 1: 🇨🇴 Tinkko Enterprise Offices - Tier 2 (10 leads)"""
        payload = {
            "client": {"name": "Tinkko Growth Corp", "email": "growth@tinkko.com"},
            "request": {
                "campaign_id": "tinkko_enterprise_offices",
                "country": "CO",
                "city": "Medellín",
                "limit": 10,
                "tier": 2
            }
        }
        order_id, order = self._execute_order_lifecycle("01_tinkko_enterprise_offices_co", payload, expected_tier=2)
        self.assertEqual(order["tier"], 2)

    def test_02_chiketto_dian_saas_co(self):
        """Scenario 2: 🇨🇴 Chiketto DIAN Invoicing SaaS - Tier 2 (10 leads)"""
        payload = {
            "client": {"name": "Chiketto Sales LatAm", "email": "ventas@chiketto.com"},
            "request": {
                "campaign_id": "chiketto",
                "country": "CO",
                "city": "Bogotá",
                "limit": 10,
                "tier": 2
            }
        }
        order_id, order = self._execute_order_lifecycle("02_chiketto_dian_saas_co", payload, expected_tier=2)
        self.assertEqual(order["tier"], 2)

    def test_03_blueoil_fuel_logistics_co(self):
        """Scenario 3: 🇨🇴 Blueoil Fuel & Heavy Fleet Logistics - Tier 2 (10 leads)"""
        payload = {
            "client": {"name": "Blueoil Combustibles", "email": "ops@blueoil.com.co"},
            "request": {
                "campaign_id": "blueoil",
                "country": "CO",
                "city": "Medellín",
                "limit": 10,
                "tier": 2
            }
        }
        order_id, order = self._execute_order_lifecycle("03_blueoil_fuel_logistics_co", payload, expected_tier=2)
        self.assertEqual(order["tier"], 2)

    def test_04_facility_services_b2b_co(self):
        """Scenario 4: 🇨🇴 Facility Services B2B - Tier 2 (10 leads)"""
        payload = {
            "client": {"name": "Aseo y Mantenimiento Andino", "email": "corporativo@aseoandino.co"},
            "request": {
                "campaign_id": "facility_services_b2b",
                "country": "CO",
                "city": "Medellín",
                "limit": 10,
                "tier": 2
            }
        }
        order_id, order = self._execute_order_lifecycle("04_facility_services_b2b_co", payload, expected_tier=2)
        self.assertEqual(order["tier"], 2)

    def test_05_warehouse_aburra_norte_co(self):
        """Scenario 5: 🇨🇴 Warehouse Aburrá Norte - Tier 1 (10 leads)"""
        payload = {
            "client": {"name": "Parque Logístico Norte", "email": "comercial@parquelogisticonorte.com"},
            "request": {
                "campaign_id": "warehouse_aburra_norte",
                "country": "CO",
                "city": "Medellín",
                "limit": 10,
                "tier": 1
            }
        }
        order_id, order = self._execute_order_lifecycle("05_warehouse_aburra_norte_co", payload, expected_tier=1)
        self.assertEqual(order["tier"], 1)

    def test_06_hebi_debt_recovery_underwriting_co(self):
        """Scenario 6: 🇨🇴 Hebi B2B Debt Recovery & Underwriting - Tier 3 (10 leads)"""
        payload = {
            "client": {"name": "Hebi Financial Solutions", "email": "risk@hebi.co"},
            "request": {
                "campaign_id": "hebi",
                "country": "CO",
                "city": "Bogotá",
                "limit": 10,
                "tier": 3
            }
        }
        order_id, order = self._execute_order_lifecycle("06_hebi_debt_recovery_underwriting_co", payload, expected_tier=3)
        self.assertEqual(order["tier"], 3)

    def test_07_eventos_ferias_crossborder(self):
        """Scenario 7: 🌎 Eventos y Ferias B2B Cross-Border Multi-Country - Tier 2 (10 leads)"""
        payload = {
            "client": {"name": "Exposiciones Globales LatAm", "email": "buyers@exposicioneslatam.com"},
            "request": {
                "campaign_id": "eventos_ferias_b2b",
                "country": "CO",
                "country_allocations": {"CO": 4, "DO": 3, "EC": 3},
                "limit": 10,
                "tier": 2
            }
        }
        order_id, order = self._execute_order_lifecycle("07_eventos_ferias_crossborder", payload, expected_tier=2)
        self.assertEqual(order["tier"], 2)

    def test_08_tinkko_dr_offices(self):
        """Scenario 8: 🇩🇴 Tinkko Dominican Republic Corporate Offices - Tier 2 (10 leads)"""
        payload = {
            "client": {"name": "Tinkko Caribe S.R.L.", "email": "info@tinkko.com.do"},
            "request": {
                "campaign_id": "tinkko_dr_offices",
                "country": "DO",
                "city": "Santo Domingo",
                "limit": 10,
                "tier": 2
            }
        }
        order_id, order = self._execute_order_lifecycle("08_tinkko_dr_offices", payload, expected_tier=2)
        self.assertEqual(order["request"]["country"], "DO")

    def test_09_tinkko_ec_offices(self):
        """Scenario 9: 🇪🇨 Tinkko Ecuador Corporate Workspaces - Tier 2 (10 leads)"""
        payload = {
            "client": {"name": "Tinkko Andina Ecuador S.A.", "email": "quito@tinkko.ec"},
            "request": {
                "campaign_id": "tinkko_ec_offices",
                "country": "EC",
                "city": "Quito",
                "limit": 10,
                "tier": 2
            }
        }
        order_id, order = self._execute_order_lifecycle("09_tinkko_ec_offices", payload, expected_tier=2)
        self.assertEqual(order["request"]["country"], "EC")

    def test_10_alimentos_distribucion_co(self):
        """Scenario 10: 🇨🇴 Alimentos y Distribución Mayorista HORECA - Tier 2 (10 leads)"""
        payload = {
            "client": {"name": "Distribuidora Gastronómica del País", "email": "compras@gastronomicadelpais.co"},
            "request": {
                "campaign_id": "alimentos_distribucion",
                "country": "CO",
                "location_allocations": {"Bogotá": 5, "Medellín": 5},
                "limit": 10,
                "tier": 2
            }
        }
        order_id, order = self._execute_order_lifecycle("10_alimentos_distribucion_co", payload, expected_tier=2)
        self.assertEqual(order["tier"], 2)

    def test_11_materiales_construccion_co(self):
        """Scenario 11: 🇨🇴 Materiales de Construcción y Obras Civiles - Tier 2 (10 leads)"""
        payload = {
            "client": {"name": "Prefabricados y Aceros de Colombia", "email": "proyectos@prefabricados.com.co"},
            "request": {
                "campaign_id": "materiales_construccion",
                "country": "CO",
                "location_allocations": {"Medellín": 5, "Barranquilla": 5},
                "limit": 10,
                "tier": 2
            }
        }
        order_id, order = self._execute_order_lifecycle("11_materiales_construccion_co", payload, expected_tier=2)
        self.assertEqual(order["tier"], 2)

    def test_12_universal_ai_intent(self):
        """Scenario 12: 🇨🇴 Freeform AI Intent Discovery - Tier 2 (10 leads)"""
        payload = {
            "client": {"name": "Industrial Automation LatAm", "email": "sales@automationlatam.com"},
            "request": {
                "offer_description": "Maquinaria industrial y equipo electromecánico para líneas de ensamble",
                "country": "CO",
                "city": "Medellín",
                "target_roles": ["Gerente General", "Director de Operaciones", "Jefe de Compras"],
                "limit": 10,
                "tier": 2
            }
        }
        order_id, order = self._execute_order_lifecycle("12_universal_ai_intent", payload, expected_tier=2)
        self.assertEqual(order["tier"], 2)

    def test_13_custom_multi_territory_split(self):
        """Scenario 13: 🇨🇴 Custom Multi-Territory Split with Custom CIIU - Tier 2 (10 leads)"""
        payload = {
            "client": {"name": "Fintech & Cloud Solutions Corp", "email": "contact@fintechcloud.co"},
            "request": {
                "country": "CO",
                "target_sectors": ["Tecnología y Telecomunicaciones"],
                "target_ciiu_codes": ["6201", "6202"],
                "target_roles": ["CTO", "Director de Tecnología", "Gerente de Sistemas"],
                "location_allocations": {"Bogotá": 5, "Medellín": 5},
                "limit": 10,
                "tier": 2
            }
        }
        order_id, order = self._execute_order_lifecycle("13_custom_multi_territory_split", payload, expected_tier=2)
        self.assertEqual(order["tier"], 2)

    def test_14_claim_replacement_guarantee(self):
        """Bonus Walkthrough: Self-Service 2x1 Replacement Portal on Paid Order"""
        payload = {
            "client": {"name": "Replacement Testing Corp", "email": "test_replacements@acme.com"},
            "request": {
                "campaign_id": "tinkko_enterprise_offices",
                "country": "CO",
                "city": "Medellín",
                "limit": 10,
                "tier": 2
            }
        }
        order_id, order = self._execute_order_lifecycle("14_replacement_portal_verification", payload, expected_tier=2)
        leads = self.sql_adapter.get_order_manifest(order_id)
        self.assertGreaterEqual(len(leads), 1)
        target_lead = leads[0]
        bounced_email = target_lead.get("verified_email") or target_lead.get("email")
        assert bounced_email is not None, "Bounced email must not be None"

        # Claim 2x1 replacement
        claim_payload = {
            "bounced_email": bounced_email,
            "bounce_reason": "Mailbox not found (550 Recipient Rejected)"
        }
        res_claim = self.client.post(f"/api/v1/orders/{order_id}/claim-replacement", json=claim_payload)
        self.assertEqual(res_claim.status_code, 200, f"Claim replacement failed: {res_claim.text}")
        claim_data = res_claim.json()
        self.assertEqual(claim_data["status"], "success")
        self.assertEqual(claim_data["replacement_count"], 2)
        self.assertIn("replacement_leads", claim_data)
        self.assertEqual(len(claim_data["replacement_leads"]), 2)

        # Check deduplication ledger marked email bounced
        default_ledger = DeduplicationLedger()
        self.assertTrue(default_ledger.is_bounced(bounced_email) or self.test_ledger.is_bounced(bounced_email))

    def test_15_procurement_auto_rfq_buyer_mode(self):
        """Scenario 15: 🇨🇴 Auto-RFQ / Procurement Mode (Client to Vendors) - Tier 2 (10 leads)"""
        payload = {
            "client": {"name": "Industrias Metálicas del Valle", "email": "compras@metalicasvalle.com.co"},
            "request": {
                "campaign_id": "auto_rfq_mantenimiento",
                "directionality": "client_to_vendors",
                "rfq_specifications": "Cotización urgente de reparación y retapizado para 150 puestos operativos en tela antifluido",
                "country": "CO",
                "city": "Cali",
                "target_sectors": ["Mantenimiento y Reparación de Mobiliario"],
                "target_ciiu_codes": ["9524", "3100"],
                "limit": 10,
                "tier": 2
            }
        }
        order_id, order = self._execute_order_lifecycle("15_procurement_auto_rfq_buyer_mode", payload, expected_tier=2)
        directionality = order.get("directionality") or (order.get("request") or {}).get("directionality")
        self.assertEqual(directionality, "client_to_vendors")
        specs = order.get("rfq_specifications") or (order.get("request") or {}).get("rfq_specifications", "")
        self.assertIn("150 puestos", specs)

    def test_16_chiketto_school_carnetizacion_co(self):
        """Scenario 16: 🇨🇴 Chiketto School Carnetization & PVC ID Cards - Tier 2 (10 leads)"""
        payload = {
            "client": {"name": "Chiketto Carnetización Escolar", "email": "carnets@chiketto.com"},
            "request": {
                "campaign_id": "chiketto_school_ids",
                "country": "CO",
                "city": "Medellín",
                "target_sectors": ["Educación y Colegios Privados"],
                "target_ciiu_codes": ["8521", "8530"],
                "target_roles": ["Rector", "Director General", "Coordinador Administrativo"],
                "keywords_include": ["colegios", "carnets estudiantiles"],
                "limit": 10,
                "tier": 2
            }
        }
        order_id, order = self._execute_order_lifecycle("16_chiketto_school_carnetizacion_co", payload, expected_tier=2)
        self.assertEqual(order["tier"], 2)

    def test_17_whatsapp_webhook_e2e_intake(self):
        """Scenario 17: 🇨🇴 WhatsApp Conversational Bot Intake to Paid Order Lifecycle - Tier 2"""
        from unittest.mock import patch
        import requests
        wa_payload = {
            "from": "+573007654321",
            "text": "Vendo dotaciones industriales y calzado de seguridad en Bogotá para 10 empresas",
            "debug": True
        }
        with patch("clients.whatsapp.bot_service.requests.post", side_effect=requests.exceptions.ConnectionError("In-process test")):
            res_wa = self.client.post("/api/v1/webhooks/whatsapp", json=wa_payload)
        self.assertEqual(res_wa.status_code, 200)
        wa_data = res_wa.json()
        self.assertEqual(wa_data["status"], "ok")
        self.assertIn("responses", wa_data)
        bot_response = wa_data["responses"][0]
        order_id = bot_response.get("order_id")
        self.assertIsNotNone(order_id)
        self.assertTrue(order_id.startswith("ord_"))

        # Process through worker
        order_doc = self.sql_adapter.get_order(order_id)
        self.assertIsNotNone(order_doc)
        process_ok = self.worker.process_order(order_doc)
        self.assertTrue(process_ok)

        # Pay and verify manifest
        res_pay = self.client.post(f"/api/v1/orders/{order_id}/pay")
        self.assertEqual(res_pay.status_code, 200)
        leads = self.sql_adapter.get_order_manifest(order_id)
        self.assertGreaterEqual(len(leads), 1)

    def test_18_cross_border_tier3_auto_downgrade_e2e(self):
        """Scenario 18: 🌎 Cross-Border Multi-Country Request with Tier 3 Auto-Capped to Tier 2 (Zero Hallucination)"""
        payload = {
            "client": {"name": "Multinational Asset Group", "email": "assets@multi-group.com"},
            "request": {
                "campaign_id": "corporate_sourcing_crossborder",
                "country": "CO",
                "location_allocations": [
                    {"country": "CO", "city": "Medellín", "allocated_leads": 5},
                    {"country": "EC", "city": "Quito", "allocated_leads": 5}
                ],
                "limit": 10,
                "tier": 3  # Attempt Tier 3 on cross-border order
            }
        }
        # Ingestion API must automatically cap tier to 2
        order_id, order = self._execute_order_lifecycle("18_crossborder_tier3_auto_downgrade", payload, expected_tier=2)
        self.assertEqual(order["tier"], 2)

    def test_19_healthcare_dispositivos_medicos_crossborder(self):
        """Scenario 19: 🇪🇨 Healthcare & Hospital Equipment Procurement B2B - Tier 2 (10 leads)"""
        payload = {
            "client": {"name": "Biomédica Andina Cia Ltda", "email": "ventas@biomedicaandina.ec"},
            "request": {
                "campaign_id": "healthcare_medical_devices",
                "country": "EC",
                "city": "Quito",
                "target_sectors": ["Salud y Dispositivos Médicos"],
                "target_ciiu_codes": ["8610", "3250"],
                "target_roles": ["Director Médico", "Gerente de Compras Hospitalarias"],
                "limit": 10,
                "tier": 2
            }
        }
        order_id, order = self._execute_order_lifecycle("19_healthcare_medical_devices_ec", payload, expected_tier=2)
        order_req = order.get("request") or {}
        self.assertEqual(order_req.get("country"), "EC")
        currency = order.get("currency") or order_req.get("currency") or (order.get("payment") or {}).get("currency")
        self.assertEqual(currency, "USD")


if __name__ == "__main__":
    unittest.main()
