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

if __name__ == "__main__":
    unittest.main()
