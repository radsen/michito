"""
Unit tests for STAGE 2: Multi-Country Adaptive Harvester Broadening.
Verifies SODA query ladder (Colombia 🇨🇴), DGCP Rubro mapping (Dominican Republic 🇩🇴),
and SERCOP CPC mapping (Ecuador 🇪🇨) across all economic verticals.
"""

import pytest
from backend.src.adapters.registries.colombia.secop_harvester_adapter import SecopHarvesterAdapter
from backend.src.adapters.registries.dominican_republic.dgcp_dr_adapter import DgcpDrAdapter
from backend.src.adapters.registries.ecuador.sercop_ecuador_adapter import SercopEcuadorAdapter
from backend.src.application.use_cases.generate_prospects_use_case import GenerateProspectsUseCase
from backend.src.adapters.storage.deduplication_ledger import DeduplicationLedger
from backend.src.domain.entities.universal_prospecting_request import (
    UniversalProspectingRequest,
    SearchDirectionality,
    LocationAllocation,
)


def test_colombia_soda_ladder_furniture_maintenance():
    adapter = SecopHarvesterAdapter(timeout=5)
    # Search for office furniture repair (Tinkko January use case)
    candidates = adapter.fetch_candidates(
        city="Medellín",
        limit=5,
        include_keywords=["reparación de muebles", "silletería"],
        ciiu_codes=["9524", "3100"],
    )
    assert len(candidates) > 0
    assert any("mueble" in c["sector"].lower() or "silleter" in c["sector"].lower() or "mantenimiento" in c["sector"].lower() for c in candidates)
    # Verify valid mobile/phone and email
    for c in candidates:
        assert "@" in c["email"]
        assert len(c["phone"]) >= 7


def test_dominican_republic_dgcp_rubro_mapping():
    adapter = DgcpDrAdapter(timeout=5)
    # Search with CIIU 8530 (Education)
    candidates_edu = adapter.fetch_candidates(
        city="Santo Domingo",
        limit=2,
        ciiu_codes=["8530"],
    )
    assert len(candidates_edu) > 0
    assert any("educaci" in c["sector"].lower() or "colegio" in c["company_name"].lower() or "school" in c["company_name"].lower() for c in candidates_edu)

    # Search with CIIU 3100 / 9524 (Furniture)
    candidates_furn = adapter.fetch_candidates(
        city="Santo Domingo",
        limit=2,
        ciiu_codes=["3100", "9524"],
    )
    assert len(candidates_furn) > 0
    assert any("mueble" in c["sector"].lower() or "siller" in c["sector"].lower() for c in candidates_furn)


def test_ecuador_sercop_cpc_mapping():
    adapter = SercopEcuadorAdapter(timeout=5)
    # Search with CIIU 8530 (Education)
    candidates_edu = adapter.fetch_candidates(
        city="Quito",
        limit=2,
        ciiu_codes=["8530"],
    )
    assert len(candidates_edu) > 0
    assert any("educaci" in c["sector"].lower() or "colegio" in c["company_name"].lower() or "school" in c["company_name"].lower() for c in candidates_edu)

    # Search with CIIU 3100 (Furniture)
    candidates_furn = adapter.fetch_candidates(
        city="Quito",
        limit=2,
        ciiu_codes=["3100"],
    )
    assert len(candidates_furn) > 0
    assert any("mueble" in c["sector"].lower() or "siller" in c["sector"].lower() for c in candidates_furn)


def test_multi_country_procurement_auto_rfq_e2e(tmp_path):
    use_case = GenerateProspectsUseCase(
        ledger=DeduplicationLedger(ledger_path=str(tmp_path / "test_ledger.json")),
        verify_mx_fn=lambda domain: (True, "mail.example.com")
    )
    req = UniversalProspectingRequest(
        offer_description="Mantenimiento y reparación de silletería y puestos de trabajo",
        preset_id="procurement_auto_rfq_test",
        directionality=SearchDirectionality.CLIENT_TO_VENDORS,
        rfq_specifications="Requerimos cotización formal para 50 sillas ergonómicas con garantía de 12 meses.",
        ciiu_codes=["9524", "3100"],
        locations=[
            LocationAllocation(country="CO", region="Antioquia", city="Medellín", allocated_leads=5),
            LocationAllocation(country="DO", region="Distrito Nacional", city="Santo Domingo", allocated_leads=2),
            LocationAllocation(country="EC", region="Pichincha", city="Quito", allocated_leads=2),
        ],
        total_leads=9,
        tier=2,
    )
    res = use_case.execute(universal_request=req)
    assert res["status"] == "success"
    assert res["total_qualified"] >= 8
    # Verify that cadences are Auto-RFQ procurement touches
    cadences = res["playbook_cadences"]
    assert len(cadences) > 0
    # Leads should have sales/commercial direct roles
    assert any("comercial" in c["decision_maker_title"].lower() or "director" in c["decision_maker_title"].lower() or "gerente" in c["decision_maker_title"].lower() for c in cadences)
