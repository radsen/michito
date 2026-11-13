"""
Tests for Bidirectional Commercial Directionality and Dynamic Custom Taxonomy Persistence.
"""

import pytest
from fastapi.testclient import TestClient

from src.domain.entities.universal_prospecting_request import (
    UniversalProspectingRequest,
    SearchDirectionality,
)
from src.application.services.dynamic_cadence_generator import generate_dynamic_touches
from src.entrypoints.api.main import app, sql_adapter


@pytest.fixture
def client():
    return TestClient(app)


def test_universal_request_directionality():
    # Outbound sales
    req_sales = UniversalProspectingRequest(
        offer_description="Software de facturación electrónica SaaS",
        directionality=SearchDirectionality.VENDOR_TO_CLIENTS,
    )
    assert req_sales.directionality == SearchDirectionality.VENDOR_TO_CLIENTS
    d_sales = req_sales.to_dict()
    assert d_sales["directionality"] == "vendor_to_clients"

    # Procurement / Sourcing
    req_proc = UniversalProspectingRequest(
        offer_description="Mantenimiento y tapicería de silletería de oficina",
        directionality=SearchDirectionality.CLIENT_TO_VENDORS,
        rfq_specifications="Cotizar 120 puestos de trabajo para entrega en enero",
    )
    assert req_proc.directionality == SearchDirectionality.CLIENT_TO_VENDORS
    d_proc = req_proc.to_dict()
    assert d_proc["directionality"] == "client_to_vendors"
    assert "120 puestos" in d_proc["rfq_specifications"]

    # Deserialization from dict
    restored = UniversalProspectingRequest.from_dict(d_proc)
    assert restored.directionality == SearchDirectionality.CLIENT_TO_VENDORS
    assert restored.rfq_specifications == "Cotizar 120 puestos de trabajo para entrega en enero"


def test_dynamic_cadence_procurement_auto_rfq():
    touches = generate_dynamic_touches(
        offer_description="Reparación y tapicería de silletería ejecutiva",
        directionality="client_to_vendors",
        rfq_specifications="Requerimos cotización para 80 sillas ergonómicas con garantía de 12 meses.",
    )

    # Touch 1 should be an invite from procurement
    assert "compras" in touches["touch1_linkedin_invite"].lower() or "cotizar" in touches["touch1_linkedin_invite"].lower()

    # Touch 2 should be a formal RFQ email
    assert "solicitud de cotización (rfq)" in touches["touch2_email_subject"].lower()
    assert "80 sillas ergonómicas" in touches["touch2_email_body"]
    assert "adquisiciones & compras" in touches["touch2_email_body"].lower()

    # Touch 3 should be follow-up on the quote
    assert "rfq" in touches["touch3_email_subject"].lower()


def test_dynamic_custom_taxonomy_api(client):
    # 1. Create a brand new custom sector
    custom_sector_payload = {
        "type": "sector",
        "name": "Restauración de Muebles & Ebanistería Corporativa",
        "country_code": "CO",
    }
    resp_sec = client.post("/api/v1/taxonomy/custom", json=custom_sector_payload)
    assert resp_sec.status_code == 200
    sec_data = resp_sec.json()
    assert sec_data["status"] == "success"
    assert sec_data["type"] == "sector"
    assert sec_data["item"]["sector_name"] == "Restauración de Muebles & Ebanistería Corporativa"
    # Verify CIIU was inferred via Universal ISIC Index! (furniture repair: 9524 or furniture: 3100)
    assert len(sec_data["item"]["ciiu_codes"]) > 0

    # 2. Verify it is immediately returned in search_sectors
    search_sec = client.get("/api/v1/taxonomy/sectors?q=Ebanistería")
    assert search_sec.status_code == 200
    sec_results = search_sec.json()["sectors"]
    assert any("Ebanistería" in s["sector_name"] for s in sec_results)

    # 3. Create a brand new custom decision maker role
    custom_role_payload = {
        "type": "role",
        "name": "Jefe de Mantenimiento Locativo y Mobiliario",
        "domain": "operations",
        "seniority": "jefe",
        "country_code": "ALL",
    }
    resp_role = client.post("/api/v1/taxonomy/custom", json=custom_role_payload)
    assert resp_role.status_code == 200
    role_data = resp_role.json()
    assert role_data["status"] == "success"
    assert role_data["type"] == "role"
    assert role_data["item"]["canonical_title"] == "Jefe de Mantenimiento Locativo y Mobiliario"

    # 4. Verify it is immediately returned in search_roles
    search_role = client.get("/api/v1/taxonomy/roles?q=Mobiliario")
    assert search_role.status_code == 200
    role_results = search_role.json()["roles"]
    assert any("Mobiliario" in r["canonical_title"] for r in role_results)

