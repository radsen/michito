from fastapi.testclient import TestClient
from src.entrypoints.api.main import app, get_container
from src.entrypoints.container import Container

client = TestClient(app)

def test_portal_loads():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

def test_search_prospects():
    response = client.post(
        "/api/v1/prospects/search",
        json={"country_code": "CO", "industry": "facility_management"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    # the fallback dataset has 2 entries
    assert len(data["results"]) >= 1

def test_verify_email():
    response = client.post(
        "/api/v1/verification/verify",
        json={"email": "test@example.com"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "status" in data

def test_create_order():
    response = client.post(
        "/api/v1/orders/create",
        json={"tier": 1, "company_id": "CO-830076432"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "order_id" in data
    assert "checkout_url" in data
    assert data["checkout_url"].startswith("http")

def test_calculate_ebitda():
    response = client.post(
        "/api/v1/orders/calculate-ebitda",
        json={
            "operating_revenue": 1000,
            "cost_of_sales": 200,
            "operating_expenses": 300,
            "depreciation": 50,
            "amortization": 50
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ebit"] == 500.0
    assert data["ebitda"] == 600.0
    assert data["ebitda_margin"] == 0.6

def test_wompi_webhook():
    response = client.post(
        "/api/v1/webhooks/wompi",
        json={
            "event": "transaction.updated",
            "data": {
                "transaction": {
                    "id": "123",
                    "status": "APPROVED",
                    "amount_in_cents": 10000,
                    "reference": "order-123"
                }
            },
            "signature": {
                "checksum": "d0862dd2186d14de65b16abbf3cdb671f57c428758b0450e21fae99e58ea308c"
            },
            "timestamp": 1234567890
        }
    )
    assert response.status_code == 200
    assert response.json()["status"] == "received"

def test_whatsapp_verify_webhook():
    response = client.get("/api/v1/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=michito_wa_token&hub.challenge=12345")
    assert response.status_code == 200
    assert response.text == "12345"

def test_whatsapp_verify_webhook_invalid():
    response = client.get("/api/v1/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=wrong_token&hub.challenge=12345")
    assert response.status_code == 403

def test_whatsapp_post_message_webhook():
    payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "from": "573001234567",
                        "text": {"body": "hola"}
                    }]
                }
            }]
        }]
    }
    response = client.post("/api/v1/webhooks/whatsapp", json=payload)
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
