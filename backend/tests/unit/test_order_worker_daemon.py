import pytest
from unittest.mock import MagicMock, patch
from src.entrypoints.workers.order_worker_daemon import OrderWorkerDaemon

def test_daemon_with_queue():
    mock_repo = MagicMock()
    mock_queue = MagicMock()
    
    daemon = OrderWorkerDaemon(
        order_repository=mock_repo,
        order_queue=mock_queue,
        use_case=MagicMock(),
        storage_adapter=MagicMock()
    )
    
    # We will simulate listen_orders calling the handler with a dummy payload
    def fake_listen(handler, max_messages):
        handler({"order_id": "queue-1"})
        
    mock_queue.listen_orders.side_effect = fake_listen
    
    # Should run listen_orders and process_order
    mock_repo.get_order.return_value = {"order_id": "queue-1"}
    
    # Patch process_order to track if it was called
    with patch.object(daemon, "process_order") as mock_process:
        daemon.run_loop(run_once=True)
        mock_process.assert_called_once_with({"order_id": "queue-1"})
        
    mock_queue.listen_orders.assert_called_once()
    mock_repo.fetch_queued_orders.assert_not_called()

def test_daemon_without_queue():
    mock_repo = MagicMock()
    
    daemon = OrderWorkerDaemon(
        order_repository=mock_repo,
        order_queue=None,
        use_case=MagicMock(),
        storage_adapter=MagicMock()
    )
    
    mock_repo.fetch_queued_orders.return_value = [{"order_id": "db-1"}]
    
    with patch.object(daemon, "process_order") as mock_process:
        daemon.run_loop(run_once=True)
        mock_process.assert_called_once_with({"order_id": "db-1"})
        
    mock_repo.fetch_queued_orders.assert_called_once()

def test_process_order_zero_leads_dispatches_failure_alerts():
    mock_repo = MagicMock()
    mock_use_case = MagicMock()
    mock_alerts = MagicMock()

    mock_repo.mark_processing.return_value = True
    mock_use_case.execute.return_value = {
        "total_qualified": 0,
        "leads": [],
        "message": "Filtros demasiado estrictos",
    }

    daemon = OrderWorkerDaemon(
        order_repository=mock_repo,
        order_queue=None,
        use_case=mock_use_case,
        storage_adapter=MagicMock(),
        alert_dispatcher=mock_alerts,
    )

    dummy_order = {
        "id": "ord_zero_leads_123",
        "client": {"name": "Test Client", "email": "test@client.com"},
        "request": {"campaign_id": "b2b", "city": "Bogota", "tier": 2},
    }

    result = daemon.process_order(dummy_order)
    assert result is False
    mock_repo.mark_failed.assert_called_once_with(
        "ord_zero_leads_123", "Filtros demasiado estrictos"
    )
    mock_alerts.send_feed_event.assert_called_once()
    assert "0 Leads" in mock_alerts.send_feed_event.call_args[1]["title"]
    mock_alerts.send_alert.assert_called_once()

def test_process_order_exception_dispatches_failure_alerts():
    mock_repo = MagicMock()
    mock_use_case = MagicMock()
    mock_alerts = MagicMock()

    mock_repo.mark_processing.return_value = True
    mock_use_case.execute.side_effect = RuntimeError("SECOP database timeout")

    daemon = OrderWorkerDaemon(
        order_repository=mock_repo,
        order_queue=None,
        use_case=mock_use_case,
        storage_adapter=MagicMock(),
        alert_dispatcher=mock_alerts,
    )

    dummy_order = {
        "id": "ord_crash_456",
        "client": {"name": "Crashing Client", "email": "crash@client.com"},
        "request": {"campaign_id": "schools", "city": "Medellin", "tier": 1},
    }

    result = daemon.process_order(dummy_order)
    assert result is False
    mock_alerts.send_feed_event.assert_called_once()
    assert "Order Execution Error" in mock_alerts.send_feed_event.call_args[1]["title"]
