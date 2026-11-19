import hashlib
import hmac
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from src.entrypoints.api.main import app
from src.adapters.db.sql_order_adapter import SqlOrderAdapter


@pytest.fixture(autouse=True)
def mock_cloud_run_job_adapter():
    """Prevents background worker threads from fighting over SQLite during unit tests."""
    with patch("src.adapters.jobs.cloud_run_job_adapter.CloudRunJobAdapter.trigger_batch_harvesting_job") as mock_trigger:
        mock_trigger.return_value = True
        yield mock_trigger


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sql_adapter():
    return SqlOrderAdapter()


def generate_wompi_event(
    tx_id: str,
    reference: str,
    status: str,
    amount_in_cents: int,
    secret: str,
    status_message: str = "",
    payment_method_type: str = "CARD",
    timestamp: int = 1795046200,
):
    raw_str = f"{tx_id}{status}{amount_in_cents}{timestamp}{secret}"
    checksum = hashlib.sha256(raw_str.encode("utf-8")).hexdigest()
    return {
        "event": "transaction.updated",
        "data": {
            "transaction": {
                "id": tx_id,
                "status": status,
                "status_message": status_message,
                "amount_in_cents": amount_in_cents,
                "reference": reference,
                "currency": "COP",
                "payment_method_type": payment_method_type,
            }
        },
        "timestamp": timestamp,
        "signature": {
            "checksum": checksum,
            "properties": ["transaction.id", "transaction.status", "transaction.amount_in_cents"],
        },
    }


def test_wompi_card_approved_4242(client, sql_adapter):
    """Scenario 1: Visa/Mastercard Approved (4242 4242 4242 4242)"""
    secret = "test_events_wmhM2301jwX2c9q8u4SofthtnAKUO7aK"
    order = sql_adapter.create_order(
        client_name="Approved Buyer",
        client_email="buyer.approved@example.com",
        campaign_id="tinkko_enterprise_offices",
        payment_amount_in_cents=65000000,
    )
    oid = order["order_id"]

    event = generate_wompi_event(
        tx_id="tx_approved_4242",
        reference=oid,
        status="APPROVED",
        amount_in_cents=65000000,
        secret=secret,
        payment_method_type="CARD",
    )

    res = client.post("/api/v1/webhooks/wompi", json=event)
    assert res.status_code == 200
    assert res.json() == {"status": "received"}

    updated = sql_adapter.get_order(oid)
    assert updated["payment"]["status"] == "approved"
    assert updated["payment"]["transaction_id"] == "tx_approved_4242"
    assert updated["status"] in ("paid", "processing")


def test_wompi_card_declined_4241(client, sql_adapter):
    """Scenario 2: Visa/Mastercard Declined (4242 4242 4242 4241)"""
    secret = "test_events_wmhM2301jwX2c9q8u4SofthtnAKUO7aK"
    order = sql_adapter.create_order(
        client_name="Declined Buyer",
        client_email="buyer.declined@example.com",
        campaign_id="tinkko_enterprise_offices",
        payment_amount_in_cents=65000000,
        status="awaiting_payment",
    )
    oid = order["order_id"]

    event = generate_wompi_event(
        tx_id="tx_declined_4241",
        reference=oid,
        status="DECLINED",
        amount_in_cents=65000000,
        secret=secret,
        status_message="Fondos insuficientes o rechazo bancario",
        payment_method_type="CARD",
    )

    res = client.post("/api/v1/webhooks/wompi", json=event)
    assert res.status_code == 200

    updated = sql_adapter.get_order(oid)
    assert updated["payment"]["status"] == "declined"
    # Order MUST remain in awaiting_payment so customer can retry
    assert updated["status"] == "awaiting_payment"
    # Deliverables MUST NOT be unlocked
    assert not updated["delivery"].get("csv_path")


def test_wompi_card_insufficient_funds_4002(client, sql_adapter):
    """Scenario 3: Visa/Mastercard Insufficient Funds (4000 0000 0000 0002)"""
    secret = "test_events_wmhM2301jwX2c9q8u4SofthtnAKUO7aK"
    order = sql_adapter.create_order(
        client_name="Insufficient Funds Buyer",
        client_email="buyer.nofunds@example.com",
        campaign_id="tinkko_enterprise_offices",
        payment_amount_in_cents=65000000,
        status="awaiting_payment",
    )
    oid = order["order_id"]

    event = generate_wompi_event(
        tx_id="tx_insufficient_4002",
        reference=oid,
        status="DECLINED",
        amount_in_cents=65000000,
        secret=secret,
        status_message="INSUFFICIENT_FUNDS",
        payment_method_type="CARD",
    )

    res = client.post("/api/v1/webhooks/wompi", json=event)
    assert res.status_code == 200

    updated = sql_adapter.get_order(oid)
    assert updated["payment"]["status"] == "declined"
    assert "INSUFFICIENT_FUNDS" in (updated.get("error_message") or "")
    assert updated["status"] == "awaiting_payment"


def test_wompi_card_high_risk_fraud_4005(client, sql_adapter):
    """Scenario 4: High Risk / Fraud Error (4000 0000 0000 0005)"""
    secret = "test_events_wmhM2301jwX2c9q8u4SofthtnAKUO7aK"
    order = sql_adapter.create_order(
        client_name="Fraud Risk Buyer",
        client_email="buyer.fraud@example.com",
        campaign_id="tinkko_enterprise_offices",
        payment_amount_in_cents=65000000,
        status="awaiting_payment",
    )
    oid = order["order_id"]

    event = generate_wompi_event(
        tx_id="tx_fraud_4005",
        reference=oid,
        status="ERROR",
        amount_in_cents=65000000,
        secret=secret,
        status_message="HIGH_RISK_FRAUD_DETECTED",
        payment_method_type="CARD",
    )

    res = client.post("/api/v1/webhooks/wompi", json=event)
    assert res.status_code == 200

    updated = sql_adapter.get_order(oid)
    assert updated["payment"]["status"] == "error"
    assert "HIGH_RISK" in (updated.get("error_message") or "")
    assert updated["status"] == "awaiting_payment"


def test_wompi_pse_bank_transfer_approved(client, sql_adapter):
    """Scenario 5: PSE Bank Transfer Approved (Banco Unión Colombiano)"""
    secret = "test_events_wmhM2301jwX2c9q8u4SofthtnAKUO7aK"
    order = sql_adapter.create_order(
        client_name="PSE Transfer Buyer",
        client_email="buyer.pse@example.com",
        campaign_id="tinkko_enterprise_offices",
        payment_amount_in_cents=30000000,
    )
    oid = order["order_id"]

    event = generate_wompi_event(
        tx_id="tx_pse_banco_union_999",
        reference=oid,
        status="APPROVED",
        amount_in_cents=30000000,
        secret=secret,
        payment_method_type="PSE",
    )

    res = client.post("/api/v1/webhooks/wompi", json=event)
    assert res.status_code == 200

    updated = sql_adapter.get_order(oid)
    assert updated["payment"]["status"] == "approved"
    assert updated["status"] in ("paid", "processing")


def test_wompi_nequi_approved(client, sql_adapter):
    """Scenario 6: Nequi Sandbox Approved (3991111111)"""
    secret = "test_events_wmhM2301jwX2c9q8u4SofthtnAKUO7aK"
    order = sql_adapter.create_order(
        client_name="Nequi Buyer",
        client_email="buyer.nequi@example.com",
        campaign_id="tinkko_enterprise_offices",
        payment_amount_in_cents=5000000,
    )
    oid = order["order_id"]

    event = generate_wompi_event(
        tx_id="tx_nequi_3991111111",
        reference=oid,
        status="APPROVED",
        amount_in_cents=5000000,
        secret=secret,
        payment_method_type="NEQUI",
    )

    res = client.post("/api/v1/webhooks/wompi", json=event)
    assert res.status_code == 200

    updated = sql_adapter.get_order(oid)
    assert updated["payment"]["status"] == "approved"
    assert updated["status"] in ("paid", "processing")


def test_wompi_signature_tampering_rejected(client, sql_adapter):
    """Scenario 7: Webhook Checksum Tampering Rejection (Security Check)"""
    order = sql_adapter.create_order(
        client_name="Tampering Target",
        client_email="target@example.com",
        campaign_id="tinkko_enterprise_offices",
        payment_amount_in_cents=65000000,
        status="awaiting_payment",
    )
    oid = order["order_id"]

    event = {
        "event": "transaction.updated",
        "data": {
            "transaction": {
                "id": "tx_hacked_123",
                "status": "APPROVED",
                "amount_in_cents": 65000000,
                "reference": oid,
            }
        },
        "timestamp": 1795046200,
        "signature": {
            "checksum": "forged_checksum_deadbeef",
            "properties": ["transaction.id", "transaction.status", "transaction.amount_in_cents"],
        },
    }

    res = client.post("/api/v1/webhooks/wompi", json=event)
    assert res.status_code == 401
    assert "Invalid signature" in res.json()["detail"]

    # Ensure database was NOT touched
    unmodified = sql_adapter.get_order(oid)
    assert unmodified["payment"]["status"] == "pending"
    assert unmodified["status"] == "awaiting_payment"
