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
