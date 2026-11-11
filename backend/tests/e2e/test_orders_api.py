import os
import unittest
from fastapi.testclient import TestClient
from src.entrypoints.api.main import app

class TestOrdersApi(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_create_get_and_pay_order(self):
        payload = {
            "client": {
                "name": "E2E Test Client S.A.S.",
                "email": "e2e_client@test.com",
                "phone": "+573001239999",
                "channel": "web_portal"
            },
            "request": {
                "campaign_id": "tinkko_enterprise_offices",
                "country": "CO",
                "city": "Medellín",
                "limit": 10
            }
        }

        # 1. Create Order
        res_post = self.client.post("/api/v1/orders", json=payload)
        self.assertEqual(res_post.status_code, 201)
        data = res_post.json()
        self.assertEqual(data["status"], "success")
        self.assertTrue(data["order_id"].startswith("ord_"))
        self.assertEqual(data["order_status"], "queued")

        order_id = data["order_id"]

        # 2. Get Order Status
        res_get = self.client.get(f"/api/v1/orders/{order_id}")
        self.assertEqual(res_get.status_code, 200)
        order_data = res_get.json()
        self.assertEqual(order_data["order_id"], order_id)
        self.assertEqual(order_data["status"], "queued")
        self.assertEqual(order_data["client"]["email"], "e2e_client@test.com")

        # 3. Pay Order
        res_pay = self.client.post(f"/api/v1/orders/{order_id}/pay")
        self.assertEqual(res_pay.status_code, 200)
        pay_data = res_pay.json()
        self.assertEqual(pay_data["status"], "success")
        self.assertEqual(pay_data["order"]["status"], "paid")
        self.assertEqual(pay_data["order"]["payment"]["status"], "approved")

    def test_get_campaigns_endpoint(self):
        res = self.client.get("/api/v1/campaigns")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertGreaterEqual(data["total"], 1)
        campaign_ids = [c["id"] for c in data["campaigns"]]
        self.assertIn("tinkko_enterprise_offices", campaign_ids)

    def test_wompi_webhook_marks_sql_order_paid(self):
        # 1. Create order
        payload = {
            "client": {"name": "Webhook Buyer", "email": "wh_buyer@test.com"},
            "request": {"campaign_id": "hebi", "city": "Bogotá", "limit": 10}
        }
        res_post = self.client.post("/api/v1/orders", json=payload)
        self.assertEqual(res_post.status_code, 201)
        order_id = res_post.json()["order_id"]

        # 2. Simulate Wompi webhook event
        webhook_event = {
            "event": "transaction.updated",
            "data": {
                "transaction": {
                    "id": "tx_wompi_real_999",
                    "status": "APPROVED",
                    "amount_in_cents": 50000000,
                    "reference": order_id
                }
            },
            "signature": {
                "checksum": "4b113556d6bf3743bf9d98cb00d553b3a0643766d85aaad4f5b5f60680054e13"
            },
            "timestamp": 1730926250
        }
        res_wh = self.client.post("/api/v1/webhooks/wompi", json=webhook_event)
        self.assertEqual(res_wh.status_code, 200)

        # 3. Verify order in PostgreSQL transitioned to paid
        res_get = self.client.get(f"/api/v1/orders/{order_id}")
        self.assertEqual(res_get.status_code, 200)
        updated = res_get.json()
        self.assertEqual(updated["status"], "paid")
        self.assertEqual(updated["payment"]["status"], "approved")
        self.assertEqual(updated["payment"]["transaction_id"], "tx_wompi_real_999")

    def test_partner_endpoints_and_order_attribution(self):
        # 1. Query partner profile
        res_partner = self.client.get("/api/v1/partners/tinkko")
        self.assertEqual(res_partner.status_code, 200)
        p_data = res_partner.json()
        self.assertEqual(p_data["status"], "success")
        self.assertEqual(p_data["partner"]["partner_id"], "tinkko")
        self.assertEqual(p_data["partner"]["commission_rate"], 0.25)
        self.assertEqual(p_data["partner"]["discount_rate"], 0.10)
        self.assertIn("Tinkko", p_data["partner"]["name"])

        # 2. Query unknown partner (fallback to direct)
        res_unknown = self.client.get("/api/v1/partners/unknown_abc")
        self.assertEqual(res_unknown.status_code, 200)
        u_data = res_unknown.json()
        self.assertEqual(u_data["partner"]["partner_id"], "direct")

        # 3. Create order with referral_partner
        payload = {
            "client": {
                "name": "Tinkko Affiliate Buyer",
                "email": "buyer_affiliate@tinkko-startup.com",
                "phone": "+573009991122",
                "channel": "web_portal",
                "referral_partner": "tinkko"
            },
            "request": {
                "campaign_id": "tinkko_enterprise_offices",
                "country": "CO",
                "city": "Medellín",
                "limit": 10
            }
        }
        res_order = self.client.post("/api/v1/orders", json=payload)
        self.assertEqual(res_order.status_code, 201)
        o_data = res_order.json()
        order_id = o_data["order_id"]

        # 4. Check order details has partner block
        res_get = self.client.get(f"/api/v1/orders/{order_id}")
        self.assertEqual(res_get.status_code, 200)
        order_dict = res_get.json()
        self.assertEqual(order_dict["partner"]["referral_partner"], "tinkko")
        self.assertEqual(order_dict["partner"]["commission_rate"], 0.25)
        self.assertEqual(order_dict["partner"]["settlement_status"], "pending")

        # 5. Pay order and check partner statement
        res_pay = self.client.post(f"/api/v1/orders/{order_id}/pay")
        self.assertEqual(res_pay.status_code, 200)

        res_stmt = self.client.get("/api/v1/partners/tinkko/statement")
        self.assertEqual(res_stmt.status_code, 200)
        stmt_data = res_stmt.json()
        self.assertEqual(stmt_data["status"], "success")
        self.assertGreaterEqual(stmt_data["statement"]["total_orders"], 1)
        self.assertGreaterEqual(stmt_data["statement"]["total_gross_revenue_cop"], 100000)
        self.assertGreaterEqual(stmt_data["statement"]["total_commission_owed_cop"], 25000)

    def test_download_deliverable_endpoint(self):
        from src.adapters.db.sql_order_adapter import SqlOrderAdapter
        import tempfile
        sql = SqlOrderAdapter()

        # Create dummy order with a real local file and a gs path
        order = sql.create_order(
            client_name="Download Client",
            client_email="dl@test.com",
            campaign_id="tinkko_enterprise_offices"
        )
        oid = order["order_id"]

        with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as f:
            f.write("company_name,email\nAcme S.A.S.,info@acme.com\n")
            temp_path = f.name

        try:
            sql.complete_order(
                order_id=oid,
                worker_result={
                    "csv_path": temp_path,
                    "dossier_path": f"gs://michito-deliverables/orders/{oid}/executive_dossier.md",
                    "leads": []
                }
            )

            # 1. Download CSV (served as FileResponse from local path)
            res_csv = self.client.get(f"/api/v1/orders/{oid}/download/csv")
            self.assertEqual(res_csv.status_code, 200)
            self.assertIn("Acme S.A.S.", res_csv.text)

            # 2. Download MD (redirects to GCS signed URL)
            res_md = self.client.get(f"/api/v1/orders/{oid}/download/md", follow_redirects=False)
            self.assertEqual(res_md.status_code, 307)
            self.assertIn("michito-deliverables", res_md.headers["location"])
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_intent_profile_endpoint(self):
        # 1. Natural language query for software in Bogotá
        payload = {
            "query": "Vendo software ERP contable y busco empresas en Bogotá con facturación electrónica",
            "country": "CO"
        }
        res = self.client.post("/api/v1/intent/profile", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["campaign_id"], "chiketto")
        self.assertEqual(data["city"], "Bogotá")
        self.assertEqual(data["recommended_limit"], 25)
        self.assertGreater(data["estimated_matches"], 30)
        self.assertIn("sample_preview", data)
        self.assertIn("pricing", data)
        self.assertEqual(data["pricing"]["total_cop"], 750000)

        # 2. Natural language query for Dominican Republic
        payload_dr = {
            "query": "Busco oficinas corporativas en Santo Domingo para empresa fintech",
            "country": "CO"
        }
        res_dr = self.client.post("/api/v1/intent/profile", json=payload_dr)
        self.assertEqual(res_dr.status_code, 200)
        data_dr = res_dr.json()
        self.assertEqual(data_dr["campaign_id"], "tinkko_dr_offices")
        self.assertEqual(data_dr["country"], "DO")
        self.assertEqual(data_dr["city"], "Santo Domingo")

    def test_create_order_with_exclusions(self):
        payload = {
            "client": {
                "name": "Exclusion Test Client",
                "email": "excl_client@test.com",
                "phone": "+573001230000",
                "channel": "web_portal"
            },
            "request": {
                "campaign_id": "tinkko_enterprise_offices",
                "country": "CO",
                "city": "Antioquia",
                "limit": 10,
                "exclusions": ["hebisend.com", "900123456", "competitor.co"]
            }
        }
        res = self.client.post("/api/v1/orders", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["status"], "success")
        order_id = data["order_id"]

        # Verify persisted exclusions
        res_get = self.client.get(f"/api/v1/orders/{order_id}")
        self.assertEqual(res_get.status_code, 200)
        order_data = res_get.json()
        req_data = order_data["request"]
        self.assertIn("hebisend.com", req_data.get("exclusions", []))
        self.assertIn("900123456", req_data.get("exclusions", []))
        self.assertEqual(req_data.get("city"), "Antioquia")

if __name__ == "__main__":
    unittest.main()

