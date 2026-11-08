import pytest
from unittest.mock import Mock
from src.application.use_cases.fulfill_wompi_webhook import FulfillPaymentWebhookUseCase
from src.domain.entities.lead_order import LeadOrder
from src.domain.entities.company import Company
from src.domain.value_objects.tax_id import TaxId

def test_fulfill_webhook_valid_signature_approved():
    mock_gateway = Mock()
    mock_repository = Mock()

    mock_gateway.verify_webhook_signature.return_value = True

    company = Company(id="c1", name="Test Co", tax_id=TaxId("900123456"), industry="IT")
    order = LeadOrder(id="order-123", company=company, status="PENDING")
    
    mock_repository.get_by_id.return_value = order

    use_case = FulfillPaymentWebhookUseCase(
        payment_gateway=mock_gateway,
        repository=mock_repository
    )

    event_data = {
        "data": {
            "transaction": {
                "id": "tx-100",
                "status": "APPROVED",
                "reference": "order-123",
                "amount_in_cents": 5000000
            }
        },
        "timestamp": "123456789"
    }
    signature = "valid_hash"

    result = use_case.execute(event_data, signature)

    assert result is True
    assert order.status == "UNLOCKED"
    mock_repository.save.assert_called_once_with(order)

def test_fulfill_webhook_invalid_signature():
    mock_gateway = Mock()
    mock_repository = Mock()

    mock_gateway.verify_webhook_signature.return_value = False

    use_case = FulfillPaymentWebhookUseCase(
        payment_gateway=mock_gateway,
        repository=mock_repository
    )

    result = use_case.execute({}, "invalid_hash")
    
    assert result is False
    mock_repository.get_by_id.assert_not_called()
    mock_repository.save.assert_not_called()

def test_fulfill_webhook_declined_transaction():
    mock_gateway = Mock()
    mock_repository = Mock()

    mock_gateway.verify_webhook_signature.return_value = True

    use_case = FulfillPaymentWebhookUseCase(
        payment_gateway=mock_gateway,
        repository=mock_repository
    )

    event_data = {
        "data": {
            "transaction": {
                "id": "tx-100",
                "status": "DECLINED",
                "reference": "order-123",
                "amount_in_cents": 5000000
            }
        },
        "timestamp": "123456789"
    }

    result = use_case.execute(event_data, "valid_hash")

    assert result is True # Should return True because webhook processed without error
    mock_repository.get_by_id.assert_not_called()
    mock_repository.save.assert_not_called()
