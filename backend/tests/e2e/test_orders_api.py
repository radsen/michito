import os
import unittest
from fastapi.testclient import TestClient
from src.entrypoints.api.main import app, sql_adapter
from src.adapters.storage.deduplication_ledger import DeduplicationLedger

TEST_ORDERS_LEDGER = "/tmp/test_orders_ledger.json"

class TestOrdersApi(unittest.TestCase):
    def setUp(self):
        if os.path.exists(TEST_ORDERS_LEDGER):
            os.remove(TEST_ORDERS_LEDGER)
        self.test_ledger = DeduplicationLedger(ledger_path=TEST_ORDERS_LEDGER)
        sql_adapter.ledger = self.test_ledger
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
        self.assertIn(data["order_status"], ("intake_submitted", "awaiting_payment", "ready_for_review"))

        order_id = data["order_id"]

        # 2. Get Order Status
        res_get = self.client.get(f"/api/v1/orders/{order_id}")
        self.assertEqual(res_get.status_code, 200)
        order_data = res_get.json()
        self.assertEqual(order_data["order_id"], order_id)
        self.assertIn(order_data["status"], ("intake_submitted", "awaiting_payment", "ready_for_review", "processing"))
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

        # 3. Verify order in PostgreSQL transitioned to paid or processing
        res_get = self.client.get(f"/api/v1/orders/{order_id}")
        self.assertEqual(res_get.status_code, 200)
        updated = res_get.json()
        self.assertIn(updated["status"], ("paid", "processing"))
        self.assertEqual(updated["payment"]["status"], "approved")
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
            # 1. Complete order with an amount requiring payment
            sql.complete_order(
                order_id=oid,
                amount_in_cents=9000000,
                worker_result={
                    "csv_path": temp_path,
                    "xlsx_path": temp_path,
                    "dossier_path": temp_path,
                    "pdf_path": temp_path,
                    "leads": []
                }
            )

            # 2. Security Check: Unpaid order must return 402 Payment Required
            res_blocked = self.client.get(f"/api/v1/orders/{oid}/download/csv")
            self.assertEqual(res_blocked.status_code, 402)
            self.assertIn("Payment required", res_blocked.json()["detail"])

            # 3. Simulate Payment Approval
            sql.mark_order_paid(oid, transaction_id="tx_sec_test_123", amount_in_cents=9000000)

            # 4. Download CSV (served as FileResponse from local path)
            res_csv = self.client.get(f"/api/v1/orders/{oid}/download/csv")
            self.assertEqual(res_csv.status_code, 200)
            self.assertIn("Acme S.A.S.", res_csv.text)

            # 5. Download XLSX (served as FileResponse from local path)
            res_xlsx = self.client.get(f"/api/v1/orders/{oid}/download/xlsx")
            self.assertEqual(res_xlsx.status_code, 200)

            # 6. Download MD (served as FileResponse from local path)
            res_md = self.client.get(f"/api/v1/orders/{oid}/download/md")
            self.assertEqual(res_md.status_code, 200)

            # 7. Download PDF (served as FileResponse from local path)
            res_pdf = self.client.get(f"/api/v1/orders/{oid}/download/pdf")
            self.assertEqual(res_pdf.status_code, 200)
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
        self.assertGreaterEqual(data["estimated_matches"], 20)
        self.assertIn("sample_preview", data)
        self.assertIn("pricing", data)
        self.assertEqual(data["pricing"]["total_cop"], 705000)

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

    def test_create_cross_border_order_with_allocations(self):
        payload = {
            "client": {
                "name": "Trade Fair Global Buyer",
                "email": "buyer@fairglobal.com",
                "phone": "+13055551234",
                "channel": "web_portal"
            },
            "request": {
                "campaign_id": "eventos_ferias_b2b",
                "country": "MULTI",
                "city": "Medellín, Santo Domingo, Quito",
                "limit": 20,
                "country_allocations": {"CO": 10, "DO": 6, "EC": 4}
            }
        }
        res = self.client.post("/api/v1/orders", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["order"]["payment"]["currency"], "USD")
        order_id = data["order_id"]

        res_get = self.client.get(f"/api/v1/orders/{order_id}")
        self.assertEqual(res_get.status_code, 200)
        order_data = res_get.json()
        req_data = order_data["request"]
        self.assertEqual(req_data["country"], "MULTI")
        self.assertEqual(req_data["country_allocations"], {"CO": 10, "DO": 6, "EC": 4})
        self.assertEqual(order_data["payment"]["currency"], "USD")

    def test_create_ecuador_order(self):
        payload = {
            "client": {
                "name": "Ecuadorian Tech Firm",
                "email": "carlos@ecuatech.com",
                "phone": "+593998765432",
                "channel": "web_portal"
            },
            "request": {
                "campaign_id": "tinkko_ec_offices",
                "country": "EC",
                "city": "Quito",
                "limit": 15
            }
        }
        res = self.client.post("/api/v1/orders", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["order"]["payment"]["currency"], "USD")
        order_id = data["order_id"]

        res_get = self.client.get(f"/api/v1/orders/{order_id}")
        self.assertEqual(res_get.status_code, 200)
        order_data = res_get.json()
        self.assertEqual(order_data["request"]["country"], "EC")
        self.assertEqual(order_data["payment"]["currency"], "USD")

    def test_create_universal_prospecting_order(self):
        payload = {
            "client": {
                "name": "Universal B2B Logistics Corp",
                "email": "logistica@universalfleet.com",
                "phone": "+573105551234",
                "channel": "web_portal"
            },
            "request": {
                "campaign_id": "universal_prospecting",
                "country": "MULTI",
                "city": "Medellín, Santo Domingo, Quito",
                "limit": 40,
                "tier": 2,
                "offer_description": "Distribución mayorista de lubricantes y combustible para flotas de carga pesada",
                "target_roles": ["Gerente de Logística", "Director de Operaciones", "Jefe de Compras"],
                "sector": "energy_fuel, logistics_transport",
                "location_allocations": [
                    {"country": "CO", "region": "Antioquia", "city": "Medellín", "allocated_leads": 20},
                    {"country": "CO", "region": "Bogotá D.C.", "city": "Bogotá", "allocated_leads": 10},
                    {"country": "DO", "region": "Distrito Nacional", "city": "Santo Domingo", "allocated_leads": 10}
                ],
                "keywords_include": ["carga pesada", "flotas", "combustible"],
                "keywords_exclude": ["competidor1.com", "900999888"]
            }
        }
        res = self.client.post("/api/v1/orders", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["status"], "success")
        order_id = data["order_id"]

        res_get = self.client.get(f"/api/v1/orders/{order_id}")
        self.assertEqual(res_get.status_code, 200)
        order = res_get.json()
        req = order["request"]
        self.assertEqual(req["campaign_id"], "universal_prospecting")
        self.assertEqual(req["offer_description"], "Distribución mayorista de lubricantes y combustible para flotas de carga pesada")
        self.assertEqual(req["target_roles"], ["Gerente de Logística", "Director de Operaciones", "Jefe de Compras"])
        self.assertEqual(len(req["location_allocations"]), 3)
        self.assertEqual(req["location_allocations"][0]["city"], "Medellín")
        self.assertEqual(req["keywords_include"], ["carga pesada", "flotas", "combustible"])
        self.assertIn("competidor1.com", req["keywords_exclude"])

    def test_claim_2x1_replacement_api_flow(self):
        # 1. Create order
        payload = {
            "client": {"name": "Guarantee E2E Buyer", "email": "guarantee_e2e@buyer.com"},
            "request": {
                "campaign_id": "universal_prospecting",
                "offer_description": "Soluciones de empaques biodegradables para cadenas de alimentos",
                "city": "Bogotá",
                "limit": 10,
            }
        }
        res_post = self.client.post("/api/v1/orders", json=payload)
        self.assertEqual(res_post.status_code, 201)
        order_id = res_post.json()["order_id"]

        # 2. Verify claiming before payment is rejected (HTTP 400)
        res_claim_unpaid = self.client.post(
            f"/api/v1/orders/{order_id}/claim-replacement",
            json={"bounced_email": "bounce_premature@badmail.com", "reason": "hard_bounce"}
        )
        self.assertEqual(res_claim_unpaid.status_code, 400)
        self.assertIn("completed/paid", res_claim_unpaid.json()["detail"])

        # 3. Pay order
        res_pay = self.client.post(f"/api/v1/orders/{order_id}/pay")
        self.assertEqual(res_pay.status_code, 200)

        # 4. Successfully claim 2x1 replacement
        claim_payload = {
            "bounced_email": "bounced.ceo@foodchain.com",
            "company_name": "Food Chain Latin Corp",
            "reason": "hard_bounce",
        }
        res_claim = self.client.post(
            f"/api/v1/orders/{order_id}/claim-replacement",
            json=claim_payload,
        )
        self.assertEqual(res_claim.status_code, 200)
        claim_data = res_claim.json()
        self.assertEqual(claim_data["status"], "success")
        self.assertEqual(claim_data["bounced_email"], "bounced.ceo@foodchain.com")
        self.assertEqual(len(claim_data["replacement_leads"]), 2)
        self.assertTrue(claim_data["claim_id"].startswith("claim_"))
        self.assertTrue(all(l.get("is_guarantee_replacement") for l in claim_data["replacement_leads"]))

        # 5. Verify order poll reflects replacements and claim history
        res_get = self.client.get(f"/api/v1/orders/{order_id}")
        self.assertEqual(res_get.status_code, 200)
        updated_order = res_get.json()
        self.assertGreaterEqual(len(updated_order.get("replacement_claims", [])), 1)
        self.assertTrue(any(l.get("is_guarantee_replacement") for l in updated_order.get("sample_leads", [])))

        # 6. Verify duplicate claim with same email is rejected (HTTP 400)
        res_claim_dup = self.client.post(
            f"/api/v1/orders/{order_id}/claim-replacement",
            json=claim_payload,
        )
        self.assertEqual(res_claim_dup.status_code, 400)
        self.assertIn("already claimed", res_claim_dup.json()["detail"])

    def test_order_quote_summary_and_approval_link(self):
        # 1. Create order
        payload = {
            "client": {"name": "Quote Requester", "email": "quote_req@empresa.com", "phone": "+573005556677"},
            "request": {
                "campaign_id": "alimentos_distribucion",
                "offer_description": "Distribución de abarrotes mayoristas para hoteles",
                "city": "Bogotá",
                "limit": 25,
                "tier": 2,
            }
        }
        res_post = self.client.post("/api/v1/orders", json=payload)
        self.assertEqual(res_post.status_code, 201)
        order_id = res_post.json()["order_id"]

        # 2. Query quote summary for approval
        res_quote = self.client.get(f"/api/v1/orders/{order_id}/quote")
        self.assertEqual(res_quote.status_code, 200)
        quote = res_quote.json()

        self.assertEqual(quote["status"], "success")
        self.assertEqual(quote["order_id"], order_id)
        self.assertEqual(quote["shareable_url"], f"/rastrear?order_id={order_id}")
        self.assertEqual(quote["client"]["name"], "Quote Requester")
        self.assertEqual(quote["scope"]["total_leads"], 25)
        self.assertEqual(quote["scope"]["tier"], 2)
        self.assertIn("Garantía Técnica 2x1", quote["financials"]["guarantee"])
        self.assertFalse(quote["is_approved_and_paid"])

        # 3. Pay order and verify approval status updates
        res_pay = self.client.post(f"/api/v1/orders/{order_id}/pay")
        self.assertEqual(res_pay.status_code, 200)

        res_quote_paid = self.client.get(f"/api/v1/orders/{order_id}/quote")
        self.assertEqual(res_quote_paid.status_code, 200)
        self.assertTrue(res_quote_paid.json()["is_approved_and_paid"])

    def test_get_campaign_presets_expanded(self):
        res = self.client.get("/api/v1/campaigns/presets")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        preset_ids = [p["id"] for p in data["presets"]]
        self.assertIn("alimentos_distribucion", preset_ids)
        self.assertIn("materiales_construccion", preset_ids)
        self.assertIn("tinkko_enterprise_offices", preset_ids)

    def test_slack_command_rerun(self):
        # 1. Create Order
        payload = {
            "client": {"name": "Slack Rerun User", "email": "slack@rerun.com"},
            "request": {"campaign_id": "universal_prospecting", "city": "Medellín", "limit": 10}
        }
        res_post = self.client.post("/api/v1/orders", json=payload)
        self.assertEqual(res_post.status_code, 201)
        order_id = res_post.json()["order_id"]

        # 2. Trigger Slack rerun command
        res_slack = self.client.post(
            "/api/v1/integrations/slack/command",
            data={"text": f"rerun {order_id}", "user_name": "andres", "command": "/michito"}
        )
        self.assertEqual(res_slack.status_code, 200)
        data = res_slack.json()
        self.assertEqual(data["response_type"], "in_channel")
        self.assertIn(order_id, data["text"])

if __name__ == "__main__":
    unittest.main()

