import pytest
import hashlib
from src.adapters.payments.wompi_adapter import WompiPaymentGatewayAdapter

def test_generate_checkout_session():
    adapter = WompiPaymentGatewayAdapter(public_key="pub_test_123", webhook_secret="sec_test_456")
    url = adapter.generate_checkout_session(
        order_id="order-001",
        amount_in_cents=1000000, # 10,000 COP * 100
        currency="COP",
        redirect_url="https://michito.com/redirect"
    )
    assert url == "https://checkout.wompi.co/p/?public-key=pub_test_123&currency=COP&amount-in-cents=1000000&reference=order-001&redirect-url=https://michito.com/redirect"

def test_verify_webhook_signature_success():
    adapter = WompiPaymentGatewayAdapter(public_key="pub_test_123", webhook_secret="sec_test_456")
    
    event_data = {
        "data": {
            "transaction": {
                "id": "tx-100",
                "status": "APPROVED",
                "amount_in_cents": 1000000
            }
        },
        "timestamp": "1620000000"
    }
    
    # Generate signature
    concatenated = "tx-100APPROVED10000001620000000sec_test_456"
    valid_signature = hashlib.sha256(concatenated.encode('utf-8')).hexdigest()
    
    assert adapter.verify_webhook_signature(event_data, valid_signature) is True

def test_verify_webhook_signature_failure():
    adapter = WompiPaymentGatewayAdapter(public_key="pub_test_123", webhook_secret="sec_test_456")
    
    event_data = {
        "data": {
            "transaction": {
                "id": "tx-100",
                "status": "APPROVED",
                "amount_in_cents": 1000000
            }
        },
        "timestamp": "1620000000"
    }
    
    invalid_signature = "invalid_hash"
    assert adapter.verify_webhook_signature(event_data, invalid_signature) is False
