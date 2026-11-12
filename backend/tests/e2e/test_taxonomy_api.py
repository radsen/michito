"""
End-to-End Tests for Michito Taxonomy & Universal Prospecting API Endpoints.
Verifies location coverage validation, role autocomplete, sector search,
and universal order ingestion with multi-territory allocations.
"""

from fastapi.testclient import TestClient
from src.entrypoints.api.main import app

client = TestClient(app)


def test_get_taxonomy_locations():
    """Verifies listing and searching locations across 🇨🇴, 🇩🇴, and 🇪🇨."""
    response = client.get("/api/v1/taxonomy/locations?q=Medellin")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["total"] > 0
    assert any(loc["country_code"] == "CO" for loc in data["locations"])


def test_validate_taxonomy_location():
    """Verifies location coverage validation with territory guidance."""
    # Supported city in Colombia
    res_co = client.get("/api/v1/taxonomy/locations/validate?name=Bogot%C3%A1")
    assert res_co.status_code == 200
    assert res_co.json()["is_supported"] is True
    assert res_co.json()["location"]["country_code"] == "CO"

    # Supported city in Dominican Republic
    res_do = client.get("/api/v1/taxonomy/locations/validate?name=Santiago%20de%20los%20Caballeros")
    assert res_do.status_code == 200
    assert res_do.json()["is_supported"] is True
    assert res_do.json()["location"]["country_code"] == "DO"

    # Unsupported territory
    res_unsupported = client.get("/api/v1/taxonomy/locations/validate?name=Tokyo")
    assert res_unsupported.status_code == 200
    assert res_unsupported.json()["is_supported"] is False
    assert "fuera de cobertura" in res_unsupported.json()["message"]


def test_get_taxonomy_roles_and_usage():
    """Verifies role searching with aliases and popularity updates."""
    res = client.get("/api/v1/taxonomy/roles?q=Operaciones")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["total"] > 0
    assert any("Operaciones" in r["canonical_title"] for r in data["roles"])

    # Search by alias
    res_alias = client.get("/api/v1/taxonomy/roles?q=COO")
    assert res_alias.status_code == 200
    assert any("Operaciones" in r["canonical_title"] for r in res_alias.json()["roles"])

    # Increment role popularity usage count
    res_usage = client.post("/api/v1/taxonomy/roles/usage", json={"role_title": "Director de Operaciones"})
    assert res_usage.status_code == 200
    assert res_usage.json()["status"] == "success"


def test_get_taxonomy_sectors():
    """Verifies browsing CIIU macro-sectors and keywords."""
    res = client.get("/api/v1/taxonomy/sectors?q=alimentos")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["total"] > 0
    assert any("Agroindustria" in s["sector_name"] or "Alimentos" in s["sector_name"] for s in data["sectors"])


def test_get_campaign_presets():
    """Verifies retrieving example demonstration templates."""
    res = client.get("/api/v1/campaigns/presets")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["total"] > 0
    assert all(p.get("is_preset") is True for p in data["presets"])


def test_create_universal_order_with_location_allocations():
    """Verifies ingesting an on-demand universal prospecting order with granular allocations."""
    payload = {
        "client": {
            "name": "Empresa Distribuidora Andina",
            "email": "comercial@distribuidora.co",
            "phone": "3009876543",
            "channel": "web_portal",
        },
        "request": {
            "campaign_id": "universal_prospecting",
            "offer_description": "Distribución mayorista de insumos químicos y materias primas",
            "target_roles": ["Director de Compras", "Gerente de Planta"],
            "sector": "manufacturing_chemicals",
            "location_allocations": [
                {"country": "CO", "region": "Antioquia", "city": "Medellín", "allocated_leads": 10},
                {"country": "CO", "region": "Cundinamarca", "city": "Bogotá D.C.", "allocated_leads": 10},
            ],
            "limit": 20,
            "tier": 2,
            "keywords_include": ["químicos", "materias primas"],
            "keywords_exclude": ["retail", "farmacias"],
        }
    }

    res = client.post("/api/v1/orders", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "success"
    assert "order_id" in data
    order = data["order"]
    assert order["request"]["offer_description"] == "Distribución mayorista de insumos químicos y materias primas"
    assert len(order["request"]["location_allocations"]) == 2

