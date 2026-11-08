import pytest
from unittest.mock import MagicMock, patch
from src.adapters.delivery.omnichannel_delivery_adapter import OmnichannelDeliveryAdapter
from src.application.use_cases.deliver_order_use_case import DeliverOrderUseCase

def test_omnichannel_delivery_adapter_extracts_paths(caplog):
    import logging
    caplog.set_level(logging.INFO)
    
    adapter = OmnichannelDeliveryAdapter()
    
    order = {
        "customer_email": "test@example.com",
        "customer_phone": "1234567890",
        "delivery": {
            "csv_download_url": "/downloads/test.csv",
            "dossier_download_url": "/downloads/test.md"
        }
    }
    
    success = adapter.send_delivery(order)
    
    assert success is True
    assert "Sending to 1234567890" in caplog.text
    assert "Sending to test@example.com" in caplog.text
    assert "/downloads/test.csv" in caplog.text
    assert "/downloads/test.md" in caplog.text

def test_deliver_order_use_case_success():
    adapter_mock = MagicMock()
    adapter_mock.send_delivery.return_value = True
    
    repo_mock = MagicMock()
    repo_mock.get_order.return_value = {
        "order_id": "ord_123",
        "status": "paid",
        "delivery": {
            "csv_download_url": "url1",
            "dossier_download_url": "url2"
        }
    }
    
    use_case = DeliverOrderUseCase(adapter_mock, repo_mock)
    
    result = use_case.execute("ord_123")
    
    assert result is True
    repo_mock.get_order.assert_called_once_with("ord_123")
    adapter_mock.send_delivery.assert_called_once()

def test_deliver_order_use_case_unpaid_raises_error():
    adapter_mock = MagicMock()
    
    repo_mock = MagicMock()
    repo_mock.get_order.return_value = {
        "order_id": "ord_123",
        "status": "awaiting_payment",
    }
    
    use_case = DeliverOrderUseCase(adapter_mock, repo_mock)
    
    with pytest.raises(ValueError, match="Order not paid"):
        use_case.execute("ord_123")
        
    adapter_mock.send_delivery.assert_not_called()

def test_deliver_order_use_case_not_found():
    adapter_mock = MagicMock()
    
    repo_mock = MagicMock()
    repo_mock.get_order.return_value = None
    
    use_case = DeliverOrderUseCase(adapter_mock, repo_mock)
    
    with pytest.raises(ValueError, match="Order ord_123 not found"):
        use_case.execute("ord_123")
        
    adapter_mock.send_delivery.assert_not_called()
