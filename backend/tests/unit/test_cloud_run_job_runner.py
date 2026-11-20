import os
import pytest
from unittest.mock import MagicMock, patch

from src.entrypoints.workers.job_runner import run_batch_job
from src.adapters.jobs.cloud_run_job_adapter import CloudRunJobAdapter


def test_job_runner_missing_order():
    assert run_batch_job("") is False
    assert run_batch_job(None) is False


def test_job_runner_order_not_found():
    with patch("src.entrypoints.workers.job_runner.SqlOrderAdapter") as MockSql:
        mock_instance = MagicMock()
        mock_instance.get_order.return_value = None
        MockSql.return_value = mock_instance

        result = run_batch_job("ord_non_existent")
        assert result is False
        mock_instance.get_order.assert_called_once_with("ord_non_existent")


def test_job_runner_idempotency_already_fulfilled():
    with patch("src.entrypoints.workers.job_runner.SqlOrderAdapter") as MockSql:
        mock_instance = MagicMock()
        mock_instance.get_order.return_value = {
            "order_id": "ord_already_paid",
            "status": "paid",
            "client": {"name": "Test Client", "email": "test@example.com"},
            "delivery": {
                "delivered_at": "2026-11-18T12:00:00Z",
                "csv_path": "orders/ord_already_paid/prospects.csv",
            },
        }
        MockSql.return_value = mock_instance

        result = run_batch_job("ord_already_paid")
        assert result is True


def test_job_runner_paid_order_delivers_files():
    with patch("src.entrypoints.workers.job_runner.SqlOrderAdapter") as MockSql, \
         patch("src.entrypoints.workers.job_runner.OrderWorkerDaemon") as MockDaemon, \
         patch("src.entrypoints.workers.job_runner.DeliverOrderUseCase") as MockDeliver:

        mock_sql = MagicMock()
        mock_sql.get_order.return_value = {
            "order_id": "ord_test_flow",
            "status": "paid",
            "payment": {"status": "approved"},
            "client": {"name": "Test Client", "email": "client@test.com"},
            "delivery": {},
            "request": {"limit": 10},
        }
        MockSql.return_value = mock_sql

        mock_daemon = MagicMock()
        mock_daemon.process_order.return_value = True
        MockDaemon.return_value = mock_daemon

        mock_deliver = MagicMock()
        mock_deliver.execute.return_value = True
        MockDeliver.return_value = mock_deliver

        result = run_batch_job("ord_test_flow")
        assert result is True

        # Verify telemetry updates
        assert mock_sql.update_telemetry.call_count >= 2
        mock_daemon.process_order.assert_called_once()
        mock_deliver.execute.assert_called_once_with("ord_test_flow")


def test_job_runner_unpaid_intake_sets_ready_for_review_without_premature_delivery():
    with patch("src.entrypoints.workers.job_runner.SqlOrderAdapter") as MockSql, \
         patch("src.entrypoints.workers.job_runner.OrderWorkerDaemon") as MockDaemon, \
         patch("src.entrypoints.workers.job_runner.DeliverOrderUseCase") as MockDeliver, \
         patch("src.entrypoints.workers.job_runner.OmnichannelDeliveryAdapter") as MockDelivery:

        mock_sql = MagicMock()
        mock_sql.get_order.return_value = {
            "order_id": "ord_test_unpaid",
            "status": "intake_submitted",
            "payment": {"status": "pending"},
            "client": {"name": "Test Client", "email": "client@test.com"},
            "delivery": {},
            "request": {"limit": 10},
        }
        MockSql.return_value = mock_sql

        mock_daemon = MagicMock()
        mock_daemon.process_order.return_value = True
        MockDaemon.return_value = mock_daemon

        mock_deliver = MagicMock()
        MockDeliver.return_value = mock_deliver

        mock_delivery_inst = MagicMock()
        MockDelivery.return_value = mock_delivery_inst

        result = run_batch_job("ord_test_unpaid")
        assert result is True

        # Must process order and lock quote/teasers, but MUST NOT leak deliverables prior to payment
        mock_daemon.process_order.assert_called_once()
        mock_deliver.execute.assert_not_called()

        # Must notify buyer about review readiness
        mock_delivery_inst.send_ready_for_review_notification.assert_called_once()
        mock_sql.mark_ready_notified.assert_called_once_with("ord_test_unpaid")


def test_cloud_run_job_adapter_local_fallback():
    adapter = CloudRunJobAdapter()
    adapter.environment = "test"

    with patch("threading.Thread") as MockThread:
        mock_thread_instance = MagicMock()
        MockThread.return_value = mock_thread_instance

        res = adapter.trigger_batch_harvesting_job("ord_test_123")
        assert res is True
        MockThread.assert_called_once()
        mock_thread_instance.start.assert_called_once()
