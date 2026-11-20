import os
import unittest
import hashlib
from fastapi.testclient import TestClient
from src.entrypoints.api.main import app, sql_adapter
from src.adapters.storage.deduplication_ledger import DeduplicationLedger

TEST_WOMPI_LEDGER = "/tmp/test_wompi_ledger.json"

class TestWompiWebhook(unittest.TestCase):
    def setUp(self):
        if os.path.exists(TEST_WOMPI_LEDGER):
            os.remove(TEST_WOMPI_LEDGER)
        self.test_ledger = DeduplicationLedger(ledger_path=TEST_WOMPI_LEDGER)
        sql_adapter.ledger = self.test_ledger
        self.client = TestClient(app)
        self.secret = "test_events_wmhM2301jwX2c9q8u4SofthtnAKUO7aK"

    def test_webhook_invalid_signature(self):
        # 1. Create order
        payload = {
            "client": {"name": "Webhook Buyer", "email": "wh_buyer_invalid@test.com"},
            "request": {"campaign_id": "tinkko_enterprise_offices", "city": "Medellín", "limit": 10}
        }
        res_post = self.client.post("/api/v1/orders", json=payload)
        self.assertEqual(res_post.status_code, 201)
        order_id = res_post.json()["order_id"]

        webhook_event = {
            "event": "transaction.updated",
            "data": {
                "transaction": {
                    "id": "tx_invalid_999",
                    "status": "APPROVED",
                    "amount_in_cents": 50000000,
                    "reference": order_id
                }
            },
            "signature": {
                "checksum": "wrong_signature_123"
            },
            "timestamp": 1730926250
        }
        res_wh = self.client.post("/api/v1/webhooks/wompi", json=webhook_event)
        self.assertEqual(res_wh.status_code, 401)
        self.assertIn("Invalid signature", res_wh.json()["detail"])

    def test_webhook_idempotency_and_delivery(self):
        # 1. Create order
        payload = {
            "client": {"name": "Webhook Buyer", "email": "wh_buyer_idemp@test.com", "phone": "555-1234"},
            "request": {"campaign_id": "tinkko_enterprise_offices", "city": "Medellín", "limit": 10}
        }
        res_post = self.client.post("/api/v1/orders", json=payload)
        self.assertEqual(res_post.status_code, 201)
        order_id = res_post.json()["order_id"]

        tx_id = "tx_idempotent_888"
        status = "APPROVED"
        amount = 100000
        timestamp = 1730926250
        raw = f"{tx_id}{status}{amount}{timestamp}{self.secret}"
        checksum = hashlib.sha256(raw.encode("utf-8")).hexdigest()

        webhook_event = {
            "event": "transaction.updated",
            "data": {
                "transaction": {
                    "id": tx_id,
                    "status": status,
                    "amount_in_cents": amount,
                    "reference": order_id
                }
            },
            "signature": {
                "checksum": checksum
            },
            "timestamp": timestamp
        }

        with self.assertLogs(level='INFO') as log:
            # First call should succeed and mark it paid, triggering delivery
            res_wh_1 = self.client.post("/api/v1/webhooks/wompi", json=webhook_event)
            self.assertEqual(res_wh_1.status_code, 200)

            # Check DB
            res_get_1 = self.client.get(f"/api/v1/orders/{order_id}")
            self.assertEqual(res_get_1.status_code, 200)
            order_data = res_get_1.json()
            self.assertEqual(order_data["payment"]["status"], "approved")
            self.assertIn(order_data["status"], ("paid", "processing"))

        # Second call with the same payload
        res_wh_2 = self.client.post("/api/v1/webhooks/wompi", json=webhook_event)
        self.assertEqual(res_wh_2.status_code, 200)

        # Should still be paid or processing
        res_get_2 = self.client.get(f"/api/v1/orders/{order_id}")
        self.assertIn(res_get_2.json()["status"], ("paid", "processing"))
        self.assertEqual(res_get_2.json()["payment"]["status"], "approved")

if __name__ == "__main__":
    unittest.main()
