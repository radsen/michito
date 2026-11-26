"""
Unit Test Suite for Dynamic Concentric Harvesting Engine with Strict Geo-Fencing.

Validates:
1. LocationTaxonomyService resolves geographic hierarchy and rings deterministically.
2. Geo-fencing scopes (strict_city, metro_area, regional_corridor) bound ring traversal.
3. SupersociedadesSodaAdapter candidate harvesting integrates corporate entities.
4. Hard termination guarantees and TAM exhaustion status reporting.
"""

import pytest
from unittest.mock import MagicMock

from src.application.services.location_taxonomy_service import LocationTaxonomyService, LocationHierarchy
from src.adapters.registries.colombia.supersociedades_soda_adapter import SupersociedadesSodaAdapter
from src.adapters.registries.dominican_republic.dgii_rnc_adapter import DgiiRncAdapter
from src.adapters.registries.ecuador.supercias_ecuador_adapter import SuperciasEcuadorAdapter
from src.application.use_cases.generate_prospects_use_case import GenerateProspectsUseCase


def test_location_taxonomy_service_ring_resolution():
    svc = LocationTaxonomyService()
    
    # 1. Medellín resolution
    h_med = svc.resolve_location("CO", "Medellín")
    assert h_med.country_code == "CO"
    assert "co_antioquia_medellin" in h_med.location_id
    
    # Check ring bounds
    rings_strict = h_med.get_rings_for_scope("strict_city")
    assert len(rings_strict) == 1
    assert rings_strict[0][0] == 0
    assert "Medellín" in rings_strict[0][1]
    assert "Envigado" not in rings_strict[0][1]

    rings_metro = h_med.get_rings_for_scope("metro_area")
    assert len(rings_metro) == 2
    assert rings_metro[0][0] == 0
    assert rings_metro[1][0] == 1
    assert "Envigado" in rings_metro[1][1]
    assert "Rionegro" not in rings_metro[1][1]

    rings_regional = h_med.get_rings_for_scope("regional_corridor")
    assert len(rings_regional) == 3
    assert any("Rionegro" in cities for _, cities in rings_regional)


def test_supersociedades_candidate_harvesting():
    adapter = SupersociedadesSodaAdapter(use_live_api=False)
    candidates = adapter.fetch_candidates(city="Medellín", ciiu_codes=["6201"], limit=5)
    
    assert len(candidates) >= 1
    for c in candidates:
        assert c["data_source"] == "SUPERSOCIEDADES_NIIF_REGISTRY"
        assert c["ciiu_code"].startswith("62")
        assert c["company_name"]
        assert c["nit"]
        assert c["email"]
        assert "Medellín" in c["city"] or "Envigado" in c["city"]


def test_bounded_concentric_harvesting_termination_and_tam_status(tmp_path):
    mock_auditor = MagicMock()
    mock_auditor.audit.return_value = (True, "https://www.example.com", "Active Audited Site")

    use_case = GenerateProspectsUseCase(
        web_auditor=mock_auditor,
        verify_mx_fn=lambda email: (True, "mx1.example.com"),
    )

    result = use_case.execute(
        city="Medellín",
        country="CO",
        limit=5,
        target_ciiu_codes=["6201"],
        keywords_include=["software", "desarrollo"],
        tier=1,
        geographic_scope="metro_area",
    )

    assert result["total_qualified"] > 0
    assert "territory_fulfillment" in result
    
    # Check that territory fulfillment has scope and rings scanned
    for terr_key, terr_data in result["territory_fulfillment"].items():
        assert "scope_applied" in terr_data
        assert terr_data["scope_applied"] == "metro_area"
        assert "rings_scanned" in terr_data
        assert len(terr_data["rings_scanned"]) >= 1
        assert terr_data["fulfillment_status"] in ("FULLY_FULFILLED", "TERRITORY_TAM_EXHAUSTED")


def test_dgii_and_supercias_candidate_harvesting():
    # 1. DGII in Dominican Republic 🇩🇴
    dgii = DgiiRncAdapter(use_live_api=False)
    do_candidates = dgii.fetch_candidates(city="Santo Domingo", ciiu_codes=["6201"], limit=5)
    assert len(do_candidates) >= 1
    for c in do_candidates:
        assert c["data_source"] == "DGII_DOMINICAN_REPUBLIC_REGISTRY"
        assert c["rnc"]
        assert c["country"] == "DO"
        assert c["currency"] == "DOP"
        assert c["ciiu_code"].startswith("62")

    # 2. SuperCias in Ecuador 🇪🇨
    supercias = SuperciasEcuadorAdapter(use_live_api=False)
    ec_candidates = supercias.fetch_candidates(city="Quito", ciiu_codes=["6201"], limit=5)
    assert len(ec_candidates) >= 1
    for c in ec_candidates:
        assert c["data_source"] == "SUPERCIAS_ECUADOR_REGISTRY"
        assert c["ruc"]
        assert c["country"] == "EC"
        assert c["currency"] == "USD"
        assert c["ciiu_code"].startswith("62")


def test_multi_country_concentric_harvesting_integration():
    mock_auditor = MagicMock()
    mock_auditor.audit.return_value = (True, "https://www.example.com", "Active Audited Site")

    use_case = GenerateProspectsUseCase(
        web_auditor=mock_auditor,
        verify_mx_fn=lambda email: (True, "mx1.example.com"),
    )

    # 1. Dominican Republic order in Santo Domingo 🇩🇴
    do_result = use_case.execute(
        city="Santo Domingo",
        country="DO",
        limit=5,
        target_ciiu_codes=["6201"],
        tier=1,
        geographic_scope="metro_area",
    )
    assert do_result["total_qualified"] > 0
    assert any(l["country"] == "DO" for l in do_result["leads"])

    # 2. Ecuador order in Quito 🇪🇨
    ec_result = use_case.execute(
        city="Quito",
        country="EC",
        limit=5,
        target_ciiu_codes=["6201"],
        tier=1,
        geographic_scope="metro_area",
    )
    assert ec_result["total_qualified"] > 0
    assert any(l["country"] == "EC" for l in ec_result["leads"])


def test_scenario_2_medellin_textiles_high_recall_tier2():
    """
    Scenario 2: 🇨🇴 Medellín Textiles & Apparel - Tier 2 High Recall Validation.
    Validates that lead delivery jumps from 4 to 100+ qualified leads,
    preventing website audit dropouts via OFFLINE_STATUTORY_ACTIVE relaxation.
    """
    mock_auditor = MagicMock()
    # Simulate realistic web presence: some sites fail HTTP 200, but valid registry + MX + phone exist
    mock_auditor.audit.return_value = (False, "", "Sitio Web No Disponible")

    use_case = GenerateProspectsUseCase(
        web_auditor=mock_auditor,
        verify_mx_fn=lambda email: (True, "mail.example.com"),
    )

    result = use_case.execute(
        campaign="universal",
        offer_description="Confección y dotación de prendas de vestir textiles en Medellín",
        country="CO",
        city="Medellín",
        target_sectors=["fashion_apparel_textiles"],
        target_ciiu_codes=["1410", "1312", "1399"],
        tier=2,
        limit=100,
        geographic_scope="metro_area",
    )

    leads = result.get("leads", [])
    assert len(leads) >= 100, f"Expected 100+ leads, got {len(leads)}"

    # Validate data integrity on delivered leads
    for lead in leads:
        assert lead["nit"]
        assert lead["email"]
        assert lead["phone"]
        assert lead["decision_maker_name"]
        assert lead["decision_maker_title"]
        assert lead["website_audit_status"] in ("ONLINE_ACTIVE_HTTP200", "OFFLINE_STATUTORY_ACTIVE")
        # Ensure correct sector classification without contamination
        assert lead["ciiu_code"][:2] in ("13", "14", "15", "46", "47")


