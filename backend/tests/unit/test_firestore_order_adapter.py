import unittest
from src.adapters.db.firestore_order_adapter import FirestoreOrderAdapter

class TestFirestoreOrderAdapter(unittest.TestCase):
    def setUp(self):
        # Instantiate in-memory adapter
        self.adapter = FirestoreOrderAdapter(project_id="test-michito", force_mock=True)

    def test_order_full_lifecycle(self):
        # 1. Create order
        order = self.adapter.create_order(
            client_name="Chiketto Labs",
            client_email="andres@chiketto.co",
            client_phone="+573001234567",
            campaign_id="tinkko_dr_offices",
            city="Santo Domingo",
            limit=25,
            country="DO",
            currency="DOP"
        )

        order_id = order["order_id"]
        self.assertIsNotNone(order_id)
        self.assertEqual(order["status"], "queued")
        self.assertEqual(order["client"]["name"], "Chiketto Labs")
        self.assertEqual(order["request"]["city"], "Santo Domingo")
        self.assertEqual(order["request"]["limit"], 25)

        # 2. Fetch queued orders
        queued = self.adapter.fetch_queued_orders()
        self.assertTrue(any(o["order_id"] == order_id for o in queued))

        # 3. Mark processing
        ok_lock = self.adapter.mark_processing(order_id)
        self.assertTrue(ok_lock)

        in_flight = self.adapter.get_order(order_id)
        self.assertEqual(in_flight["status"], "processing")
        self.assertIsNotNone(in_flight.get("started_processing_at"))

        # Cannot lock twice
        self.assertFalse(self.adapter.mark_processing(order_id))

        # 4. Complete order with teaser and quote
        mock_worker_result = {
            "total_qualified": 25,
            "csv_path": "/tmp/prospects.csv",
            "dossier_path": "/tmp/executive_dossier.md",
            "sample_teaser": [
                {
                    "company_name": "CaribTech, SRL",
                    "city": "Santo Domingo",
                    "decision_maker_title": "Gerente General",
                    "intent_level": "Alto"
                }
            ],
            "metrics": {
                "total_elapsed_seconds": 12.4
            }
        }
        quote_cents = 50000000 # 500.000 COP
        ok_comp = self.adapter.complete_order(order_id, mock_worker_result, amount_in_cents=quote_cents)
        self.assertTrue(ok_comp)

        completed_ord = self.adapter.get_order(order_id)
        self.assertEqual(completed_ord["status"], "awaiting_payment")
        self.assertEqual(completed_ord["delivery"]["total_qualified"], 25)
        self.assertEqual(len(completed_ord["delivery"]["sample_teaser"]), 1)
        self.assertEqual(completed_ord["payment"]["amount_in_cents"], quote_cents)

        # 5. Mark paid (Wompi webhook simulation)
        ok_paid = self.adapter.mark_order_paid(
            order_id=order_id,
            transaction_id="wompi_txn_999888",
            amount_paid=500000.0,
            currency="COP"
        )
        self.assertTrue(ok_paid)

        final_ord = self.adapter.get_order(order_id)
        self.assertEqual(final_ord["status"], "paid")
        self.assertEqual(final_ord["payment"]["status"], "approved")
        self.assertEqual(final_ord["payment"]["transaction_id"], "wompi_txn_999888")
        self.assertIsNotNone(final_ord["delivery"]["delivered_at"])

if __name__ == "__main__":
    unittest.main()

