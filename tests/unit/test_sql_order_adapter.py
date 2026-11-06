import unittest
from src.adapters.db.sql_order_adapter import SqlOrderAdapter

class TestSqlOrderAdapter(unittest.TestCase):
    def setUp(self):
        # Isolated SQLite in-memory database for ultra-fast unit tests
        self.adapter = SqlOrderAdapter(database_url="sqlite:///:memory:")

    def test_client_auto_creation_and_order_flow(self):
        # 1. Create Order (client should be auto-created)
        order = self.adapter.create_order(
            client_name="Tinkko Corporate",
            client_email="growth@tinkko.com",
            client_phone="+57 300 999 8888",
            campaign_id="tinkko_enterprise_offices",
            city="Medellín",
            limit=25,
            referral_partner="tinkko",
        )

        self.assertIsNotNone(order)
        self.assertTrue(order["order_id"].startswith("ord_"))
        self.assertEqual(order["status"], "queued")
        self.assertEqual(order["client"]["name"], "Tinkko Corporate")
        self.assertIsNotNone(order["client"]["client_id"])

        # 2. Complete order with structured leads
        order_id = order["order_id"]
        self.adapter.mark_processing(order_id)

        mock_leads = [
            {
                "country": "CO",
                "nit": "900.123.456",
                "company_name": "Inversiones Digitales S.A.S.",
                "clean_name": "Inversiones Digitales",
                "city": "Medellín",
                "decision_maker_name": "Laura Restrepo",
                "decision_maker_title": "Gerente General",
                "email": "laura@inversionesdigitales.co",
                "phone": "+573001234567",
                "mx_host": "mail.inversionesdigitales.co",
                "touch1_copy": "Hola Laura, me encantaría conectar...",
                "touch2_sub": "Inversiones Digitales — Espacios corporativos",
                "touch2_body": "Estimada Laura, felicitaciones por su crecimiento...",
            }
        ]

        worker_result = {
            "total_qualified": 1,
            "leads": mock_leads,
            "sample_teaser": [{"company_name": "Inversiones Digitales"}],
            "csv_path": "gs://michito/prospects.csv",
            "dossier_path": "gs://michito/dossier.md",
        }

        ok = self.adapter.complete_order(order_id, worker_result, amount_in_cents=2000000)
        self.assertTrue(ok)

        # 3. Check Order Manifest (Products by Order)
        manifest = self.adapter.get_order_manifest(order_id)
        self.assertEqual(len(manifest), 1)
        self.assertEqual(manifest[0]["company_name"], "Inversiones Digitales S.A.S.")
        self.assertEqual(manifest[0]["touches"]["touch1_linkedin"], "Hola Laura, me encantaría conectar...")

        # 4. Check Lead Inventory Cache
        client_id = order["client"]["client_id"]

        # Client 1 (Tinkko) already received this lead -> should NOT get it again in cache
        cached_for_tinkko = self.adapter.get_cached_fresh_leads(
            city="Medellín",
            country="CO",
            client_id=client_id,
        )
        self.assertEqual(len(cached_for_tinkko), 0)

        # Client 2 (Hebisend) has NOT received this lead -> CAN get it from inventory cache!
        cached_for_hebi = self.adapter.get_cached_fresh_leads(
            city="Medellín",
            country="CO",
            client_id="cli_different_customer",
        )
        self.assertEqual(len(cached_for_hebi), 1)
        self.assertEqual(cached_for_hebi[0]["company_name"], "Inversiones Digitales S.A.S.")
        self.assertEqual(cached_for_hebi[0]["email"], "laura@inversionesdigitales.co")

    def test_mark_order_paid(self):
        order = self.adapter.create_order(
            client_name="Test Buyer",
            client_email="buyer@test.com",
            campaign_id="chiketto",
            limit=10,
        )
        order_id = order["order_id"]
        self.adapter.complete_order(order_id, {"leads": [], "total_qualified": 0}, amount_in_cents=20000000)

        ok_paid = self.adapter.mark_order_paid(
            order_id=order_id,
            transaction_id="tx_wompi_abc123",
            amount_in_cents=20000000,
        )
        self.assertTrue(ok_paid)

        updated = self.adapter.get_order(order_id)
        self.assertEqual(updated["status"], "paid")
        self.assertEqual(updated["payment"]["status"], "approved")
        self.assertEqual(updated["payment"]["transaction_id"], "tx_wompi_abc123")


if __name__ == "__main__":
    unittest.main()
