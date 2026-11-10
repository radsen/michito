import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta
from src.adapters.alerts.webhook_alert_adapter import WebhookAlertAdapter
from src.adapters.db.sql_order_adapter import SqlOrderAdapter
from src.adapters.db.models import OrderModel
from src.entrypoints.workers.order_worker_daemon import OrderWorkerDaemon


class TestWebhookAlertAdapter(unittest.TestCase):
    def test_alert_without_webhook_url(self):
        adapter = WebhookAlertAdapter(webhook_url="")
        success = adapter.send_alert(
            title="Test No Webhook",
            message="No URL configured",
            level="warning"
        )
        self.assertFalse(success)

    @patch("requests.post")
    def test_discord_webhook_formatting(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_post.return_value = mock_response

        adapter = WebhookAlertAdapter(webhook_url="https://discord.com/api/webhooks/123/xyz")
        success = adapter.send_alert(
            title="Order Failed",
            message="Execution error occurred",
            level="error",
            details={
                "order_id": "ord_12345",
                "client_email": "ops@michito.co",
                "retry_count": 3,
                "error": "SECOP Gateway Timeout"
            }
        )

        self.assertTrue(success)
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        payload = call_kwargs["json"]
        self.assertEqual(payload["username"], "Michito Watchdog")
        self.assertEqual(len(payload["embeds"]), 1)
        embed = payload["embeds"][0]
        self.assertIn("Order Failed", embed["title"])
        self.assertEqual(embed["color"], 15158332)  # Red for error/critical
        field_names = [f["name"] for f in embed["fields"]]
        self.assertIn("Order ID", field_names)
        self.assertIn("Error Details", field_names)

    @patch("requests.post")
    def test_slack_webhook_formatting(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        adapter = WebhookAlertAdapter(webhook_url="https://hooks.slack.com/services/T00/B00/X00")
        success = adapter.send_alert(
            title="DLQ Exhausted",
            message="Worker retries exhausted",
            level="critical",
            details={"order_id": "ord_slack_1", "error": "Crash loop"}
        )

        self.assertTrue(success)
        mock_post.assert_called_once()
        payload = mock_post.call_args[1]["json"]
        self.assertIn("text", payload)
        self.assertIn("ord_slack_1", payload["text"])

    @patch("requests.post")
    def test_generic_webhook_formatting(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        adapter = WebhookAlertAdapter(webhook_url="https://api.michito.co/internal/webhooks/alerts")
        success = adapter.send_alert(
            title="Warning Alert",
            message="High latency",
            level="warning",
            details={"latency_ms": 2500}
        )

        self.assertTrue(success)
        mock_post.assert_called_once()
        payload = mock_post.call_args[1]["json"]
        self.assertEqual(payload["event"], "michito.watchdog.alert")
        self.assertEqual(payload["level"], "warning")
        self.assertEqual(payload["details"]["latency_ms"], 2500)

    @patch("requests.post")
    def test_network_exception_safe_failure(self, mock_post):
        mock_post.side_effect = Exception("Connection Timeout")

        adapter = WebhookAlertAdapter(webhook_url="https://discord.com/api/webhooks/broken")
        # Must fail safely without raising exception
        success = adapter.send_alert(
            title="Test Exception",
            message="Should not crash the caller"
        )
        self.assertFalse(success)


class TestOrderReliabilityAndReaper(unittest.TestCase):
    def setUp(self):
        self.adapter = SqlOrderAdapter(database_url="sqlite:///:memory:")

    def test_record_order_failure_progressive_requeue(self):
        order = self.adapter.create_order(
            client_name="Retry Test Corp",
            client_email="retry@test.com",
            campaign_id="tinkko_enterprise_offices",
            limit=5
        )
        order_id = order["order_id"]

        # Failure 1: retry_count goes from 0 -> 1, status reset to queued
        res1 = self.adapter.record_order_failure(order_id, "Temporary socket reset")
        self.assertEqual(res1["status"], "re-queued")
        self.assertEqual(res1["order"]["retry_count"], 1)
        self.assertEqual(res1["order"]["status"], "queued")

        # Failure 2: retry_count goes from 1 -> 2, status reset to queued
        res2 = self.adapter.record_order_failure(order_id, "DNS failure")
        self.assertEqual(res2["status"], "re-queued")
        self.assertEqual(res2["order"]["retry_count"], 2)

        # Failure 3: max_retries reached (3), dead-lettered to failed
        res3 = self.adapter.record_order_failure(order_id, "Persistent timeout")
        self.assertEqual(res3["status"], "dead-lettered")
        self.assertEqual(res3["order"]["status"], "failed")
        self.assertEqual(res3["order"]["retry_count"], 3)
        self.assertIn("Exceeded max retries", res3["order"]["error_message"])

    def test_zombie_order_reaper_sweeper(self):
        order1 = self.adapter.create_order(client_name="Stuck 1", client_email="s1@test.com", campaign_id="tinkko_enterprise_offices", limit=5)
        order2 = self.adapter.create_order(client_name="Stuck 2", client_email="s2@test.com", campaign_id="tinkko_enterprise_offices", limit=5)
        order3 = self.adapter.create_order(client_name="Active Normal", client_email="s3@test.com", campaign_id="tinkko_enterprise_offices", limit=5)

        # Simulate stuck state in DB
        now = datetime.now(timezone.utc)
        ten_minutes_ago = now - timedelta(minutes=10)
        two_minutes_ago = now - timedelta(minutes=2)

        with self.adapter._get_session() as session:
            # Order 1: stuck 10 mins ago, retry_count=0 -> should be re-queued
            o1 = session.get(OrderModel, order1["order_id"])
            o1.status = "processing"
            o1.started_processing_at = ten_minutes_ago
            o1.retry_count = 0
            o1.max_retries = 3

            # Order 2: stuck 10 mins ago, retry_count=3 -> should be dead-lettered to 'failed'
            o2 = session.get(OrderModel, order2["order_id"])
            o2.status = "processing"
            o2.started_processing_at = ten_minutes_ago
            o2.retry_count = 3
            o2.max_retries = 3

            # Order 3: processing recently (2 mins ago) -> should NOT be reaped
            o3 = session.get(OrderModel, order3["order_id"])
            o3.status = "processing"
            o3.started_processing_at = two_minutes_ago

            session.commit()

        # Run reaper with 5-minute threshold
        dead_lettered = self.adapter.recover_stuck_processing_orders(max_processing_minutes=5)

        # Only order 2 exhausted retries and is returned as dead-lettered
        self.assertEqual(len(dead_lettered), 1)
        self.assertEqual(dead_lettered[0]["order_id"], order2["order_id"])

        # Check order 1 was re-queued with incremented retry count
        recovered_o1 = self.adapter.get_order(order1["order_id"])
        self.assertEqual(recovered_o1["status"], "queued")
        self.assertEqual(recovered_o1["retry_count"], 1)

        # Check order 2 was dead-lettered
        dead_o2 = self.adapter.get_order(order2["order_id"])
        self.assertEqual(dead_o2["status"], "failed")

        # Check order 3 remained untouched in processing
        active_o3 = self.adapter.get_order(order3["order_id"])
        self.assertEqual(active_o3["status"], "processing")


class TestWorkerDaemonFailureAlerts(unittest.TestCase):
    def test_daemon_dispatches_alert_on_dead_letter(self):
        mock_repo = MagicMock()
        mock_use_case = MagicMock()
        mock_storage = MagicMock()
        mock_alert = MagicMock()

        # Simulate lock success
        mock_repo.mark_processing.return_value = True
        # Simulate use_case raising unrecoverable exception
        mock_use_case.execute.side_effect = RuntimeError("Chamber of Commerce Registry Unavailable")
        # Simulate repo returning dead-lettered
        mock_repo.record_order_failure.return_value = {
            "status": "dead-lettered",
            "order": {"order_id": "ord_fail_99", "retry_count": 3}
        }

        daemon = OrderWorkerDaemon(
            order_repository=mock_repo,
            order_queue=None,
            use_case=mock_use_case,
            storage_adapter=mock_storage,
            alert_dispatcher=mock_alert
        )

        test_order = {
            "order_id": "ord_fail_99",
            "client": {"name": "Test Fail", "email": "fail@test.com"},
            "request": {"campaign_id": "test", "city": "Bogotá", "limit": 5, "tier": 2}
        }

        success = daemon.process_order(test_order)
        self.assertFalse(success)
        mock_alert.send_alert.assert_called_once()
        alert_args = mock_alert.send_alert.call_args[1]
        self.assertIn("Dead-Lettered", alert_args["title"])
        self.assertEqual(alert_args["details"]["order_id"], "ord_fail_99")
