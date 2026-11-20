"""
Unit tests for TRM Currency Exchange Service, FX API endpoints,
and Strict Order Creation Integrity (Zero-Lead / 403 Rejection).
"""

import pytest
from fastapi.testclient import TestClient
from src.domain.services.trm_service import TrmExchangeRateService
from src.entrypoints.api.main import app


@pytest.fixture
def api_client():
    return TestClient(app)


def test_trm_service_direct_conversion():
    service = TrmExchangeRateService.get_instance()
    rates = service.get_rates()
    assert rates["status"] == "success"
    assert "USD" in rates["rates_to_cop"]
    assert "DOP" in rates["rates_to_cop"]
    assert rates["trm_usd"] > 1000

    # Test DOP to COP conversion
    res_dop = service.convert(amount=28000.0, from_currency="DOP", to_currency="COP")
    assert res_dop["status"] == "success"
    assert res_dop["amount_in_cop"] > 1000000  # 28,000 DOP is roughly 1.9M COP, never 28,000 COP!
    assert res_dop["to_currency"] == "COP"

    # Test USD to COP conversion
    res_usd = service.convert(amount=50.0, from_currency="USD", to_currency="COP")
    assert res_usd["status"] == "success"
    assert res_usd["amount_in_cop"] > 150000


def test_fx_trm_endpoint(api_client):
    response = api_client.get("/api/v1/fx/trm")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "rates_to_cop" in data
    assert data["rates_to_cop"]["COP"] == 1.0


def test_fx_convert_endpoints(api_client):
    # GET query
    response_get = api_client.get("/api/v1/fx/convert?amount=100&from=DOP&to=COP")
    assert response_get.status_code == 200
    data_get = response_get.json()
    assert data_get["status"] == "success"
    assert data_get["amount_in_cop"] > 5000

    # POST body
    response_post = api_client.post(
        "/api/v1/fx/convert",
        json={"amount": 100, "from_currency": "USD", "to_currency": "COP"},
    )
    assert response_post.status_code == 200
    data_post = response_post.json()
    assert data_post["status"] == "success"
    assert data_post["amount_in_cop"] >= 400000


def test_order_creation_rejects_unfulfillable_request(api_client, monkeypatch):
    """
    Ensures that when 0 authentic leads can be verified (due to 403 or 0 matches),
    the API rejects order creation with HTTP 422 to prevent charging for info we don't have.
    """
    # Force radar scan to return 0 leads
    monkeypatch.setattr("src.entrypoints.api.main.run_fast_radar_scan", lambda **kwargs: [])

    payload = {
        "client": {
            "name": "Empresa Constructora Test",
            "email": "compras@constructoratest.com",
            "phone": "+18095550199",
        },
        "request": {
            "city": "Santo Domingo",
            "country": "DO",
            "limit": 10,
            "currency": "DOP",
            "sector": "Construcción",
        },
    }

    response = api_client.post("/api/v1/orders", json=payload)
    assert response.status_code == 422
    assert "No fue posible encontrar la información solicitada" in response.json()["detail"]
