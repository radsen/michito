import pytest
from unittest.mock import Mock
from src.application.use_cases.create_lead_order import CreateLeadOrderUseCase, CreateLeadOrderResponse
from src.domain.entities.lead_order import LeadOrder
from src.domain.entities.company import Company
from src.domain.value_objects.tax_id import TaxId

def test_create_lead_order_success():
    mock_gateway = Mock()
    mock_repository = Mock()

    mock_gateway.generate_checkout_session.return_value = "https://checkout.wompi.co/mock"

    use_case = CreateLeadOrderUseCase(
        payment_gateway=mock_gateway,
        repository=mock_repository,
        redirect_url="https://michito.com/done"
    )

    company = Company(id="c1", name="Test Co", tax_id=TaxId("900123456"), industry="IT")
    order = LeadOrder(id="order-123", company=company, tier=2)

    response = use_case.execute(order)

    assert response.order_id == "order-123"
    assert response.checkout_url == "https://checkout.wompi.co/mock"
    
    mock_gateway.generate_checkout_session.assert_called_once_with(
        order_id="order-123",
        amount_in_cents=5000000, # Tier 2 is 50,000 COP
        currency="COP",
        redirect_url="https://michito.com/done"
    )
    mock_repository.save.assert_called_once_with(order)
