import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import unittest
from unittest.mock import patch, MagicMock
from src.adapters.db.firestore_order_adapter import FirestoreOrderAdapter
from src.adapters.queue.memory_queue_adapter import MemoryQueueAdapter
from src.entrypoints.workers.order_worker_daemon import OrderWorkerDaemon
from order_worker import process_single_order

class TestOrderWorker(unittest.TestCase):
    def setUp(self):
        self.adapter = FirestoreOrderAdapter(force_mock=True)

    @patch("order_worker.run_prospecting_job")
    def test_process_single_order_success(self, mock_prospecting_job):
        mock_prospecting_job.return_value = {
            "status": "success",
            "total_qualified": 10,
            "csv_path": "/tmp/test.csv",
            "dossier_path": "/tmp/test.md",
            "sample_teaser": [{"company_name": "Acme"}],
            "metrics": {"total_elapsed_seconds": 5.0}
        }

        order = self.adapter.create_order(
            client_name="Test Customer",
            client_email="client@test.com",
            campaign_id="tinkko_dr_offices",
            city="Santo Domingo",
            limit=10,
            country="DO"
        )
        order_id = order["order_id"]

        success = process_single_order(self.adapter, order)
        self.assertTrue(success)

        updated_ord = self.adapter.get_order(order_id)
        self.assertEqual(updated_ord["status"], "awaiting_payment")
        self.assertEqual(updated_ord["delivery"]["total_qualified"], 10)
        self.assertGreater(updated_ord["payment"]["amount_in_cents"], 0)

    def test_daemon_with_memory_queue(self):
        queue = MemoryQueueAdapter()
        mock_use_case = MagicMock()
        mock_use_case.execute.return_value = {
            "status": "success",
            "total_qualified": 5,
            "csv_path": "/tmp/test_q.csv",
            "dossier_path": "/tmp/test_q.md",
            "sample_teaser": [],
            "metrics": {"total_elapsed_seconds": 1.2}
        }

        order = self.adapter.create_order(
            client_name="Queue Client",
            client_email="queue@test.com",
            campaign_id="hebi",
            city="Medellín",
            limit=5,
            country="CO"
        )
        order_id = order["order_id"]

        # Enqueue order into memory queue
        queue.enqueue(order)
        self.assertEqual(queue.size(), 1)

        daemon = OrderWorkerDaemon(
            order_repository=self.adapter,
            order_queue=queue,
            use_case=mock_use_case,
        )

        daemon.run_loop(poll_interval_sec=0, run_once=True)

        self.assertEqual(queue.size(), 0)
        updated_ord = self.adapter.get_order(order_id)
        self.assertEqual(updated_ord["status"], "awaiting_payment")
        self.assertEqual(updated_ord["delivery"]["total_qualified"], 5)

    def test_process_tier_3_underwriting_pricing(self):
        mock_use_case = MagicMock()
        mock_use_case.execute.return_value = {
            "status": "success",
            "tier": 3,
            "currency": "COP",
            "total_qualified": 10,
            "csv_path": "/tmp/test_tier3.csv",
            "dossier_path": "/tmp/test_tier3.md",
            "sample_teaser": [
                {
                    "company_name": "Solvente S.A.S.",
                    "underwriting_grade": "AAA - Solvente y de Máxima Confianza",
                    "solvency_tier": "AAA",
                    "litigation_risk": "CLEAN"
                }
            ],
            "metrics": {"total_elapsed_seconds": 2.5}
        }

        order = self.adapter.create_order(
            client_name="Tier 3 Buyer",
            client_email="buyer3@test.com",
            campaign_id="tinkko_enterprise_offices",
            city="Medellín",
            limit=10,
            country="CO",
            tier=3
        )
        order_id = order["order_id"]

        daemon = OrderWorkerDaemon(
            order_repository=self.adapter,
            use_case=mock_use_case
        )

        ok = daemon.process_order(order)
        self.assertTrue(ok)

        # Assert use_case called with tier=3
        mock_use_case.execute.assert_called_once_with(
            campaign="tinkko_enterprise_offices",
            city="Medellín",
            limit=10,
            segment="midmarket",
            tier=3,
            dry_run=False,
            output_format="both"
        )

        # Tier 3 unit base is $65.000 COP = 6.500.000 cents. For 10 leads, 65.000.000 cents ($650.000 COP)
        updated = self.adapter.get_order(order_id)
        self.assertEqual(updated["status"], "awaiting_payment")
        self.assertEqual(updated["payment"]["amount_in_cents"], 65000000)
        self.assertEqual(updated["delivery"]["sample_teaser"][0]["underwriting_grade"], "AAA - Solvente y de Máxima Confianza")

if __name__ == "__main__":
    unittest.main()
