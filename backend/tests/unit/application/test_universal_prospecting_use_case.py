"""
Unit Tests for Universal Prospecting Use Case & Dynamic Engine Decoupling.
Verifies on-demand prospecting without hardcoded campaign YAMLs,
granular multi-territory quota fulfillment, dynamic 5-touch sales copy,
role-tailored LinkedIn queries, and lead quality ranking.
"""

import pytest
from unittest.mock import MagicMock
from typing import Dict, Any, List

from src.application.use_cases.generate_prospects_use_case import (
    GenerateProspectsUseCase,
    build_targeted_linkedin_xray_url,
)
from src.domain.entities.universal_prospecting_request import (
    UniversalProspectingRequest,
    LocationAllocation,
)
from src.application.services.dynamic_cadence_generator import generate_dynamic_touches


class MockHarvester:
    """Mock harvester providing simulated registered companies for testing."""

    def __init__(self, prefix: str = "Empresa"):
        self.prefix = prefix

    def fetch_candidates(self, city: str, limit: int, **kwargs) -> List[Dict[str, Any]]:
        results = []
        for i in range(1, limit + 1):
            results.append({
                "nit": f"900{i:05d}-1",
                "company_name": f"{self.prefix} {city} {i} S.A.S.",
                "city": city,
                "department": "Territorio Test",
                "email": f"contacto@empresa{city.lower()}{i}.com",
                "phone": f"30012345{i:02d}",
                "website": f"https://www.empresa{city.lower()}{i}.com",
                "decision_maker_name": f"Carlos Pérez {city} {i}",
                "decision_maker_title": "Gerente General",
                "sector": "Distribución y Comercialización",
            })
        return results


@pytest.fixture
def mock_web_auditor():
    auditor = MagicMock()
    auditor.audit.return_value = (True, "https://empresa.com", "Sitio Activo HTTP 200")
    return auditor


@pytest.fixture
def mock_contracts_adapter():
    adapter = MagicMock()
    adapter.fetch_contracts_summary.return_value = {
        "has_contracts": True,
        "contracts_count": 2,
        "total_value_cop": 150000000.0,
        "total_value_display": "$150M COP",
        "top_contract_entity": "Alcaldía de Medellín",
        "top_contract_value_cop": 100000000.0,
        "top_contract_value_display": "$100M COP",
        "top_contract_object": "Suministro y dotación empresarial",
        "intent_level": "Alto (Contratos Adjudicados)",
    }
    return adapter


def test_dynamic_cadence_generator():
    """Verifies that dynamic touches are synthesized with all required variables."""
    touches = generate_dynamic_touches(
        offer_description="Distribución mayorista de alimentos y cadena de frío",
        sectors=["food_agriculture"],
        roles=["Director de Logística", "Gerente de Compras"],
    )

    assert "touch1_linkedin_invite" in touches
    assert "touch2_email_subject" in touches
    assert "touch2_email_body" in touches
    assert "touch3_email_body" in touches
    assert "touch4_email_body" in touches
    assert "touch5_email_body" in touches

    # Check length constraint for LinkedIn invite (must be <= 300 chars)
    t1_interpolated = touches["touch1_linkedin_invite"].format(
        salutation="Hola Andrés",
        clean_name="Distribuidora Andina",
        city="Medellín",
    )
    assert len(t1_interpolated) <= 300
    assert "Distribuidora Andina" in t1_interpolated


def test_build_targeted_linkedin_xray_url_with_custom_roles():
    """Verifies that explicitly specified roles are accurately formatted in Google X-Ray."""
    import urllib.parse
    url = build_targeted_linkedin_xray_url(
        company_name="Logística Rápida S.A.S.",
        rep_name="Carlos Gómez",
        country="CO",
        target_roles=["Director de Operaciones", "Jefe de Flota", "Gerente de Logística"],
    )
    unquoted = urllib.parse.unquote_plus(url)

    assert "site:co.linkedin.com/in/" in unquoted
    assert "Logística Rápida" in unquoted
    assert "Director de Operaciones" in unquoted
    assert "Jefe de Flota" in unquoted
    assert "Gerente de Logística" in unquoted


def test_universal_prospecting_without_yaml_campaign(
    mock_web_auditor, mock_contracts_adapter
):
    """
    Verifies that the engine executes an on-demand prospecting job without needing
    any preset YAML file, using custom offer_description and dynamic parameters.
    """
    harvester = MockHarvester("Distribuidora")
    use_case = GenerateProspectsUseCase(
        harvester_co=harvester,
        web_auditor=mock_web_auditor,
        contracts_adapter=mock_contracts_adapter,
        verify_mx_fn=lambda email: (True, "mail.empresa.com"),
    )

    req = UniversalProspectingRequest(
        offer_description="Empaques biodegradables y suministros sostenibles para restaurantes",
        sectors=["food_agriculture", "manufacturing_industrial"],
        locations=[
            LocationAllocation(country="CO", region="Antioquia", city="Medellín", allocated_leads=2),
            LocationAllocation(country="CO", region="Cundinamarca", city="Bogotá D.C.", allocated_leads=2),
        ],
        roles=["Director de Compras", "Gerente de Sostenibilidad"],
        keywords_include=["alimentos", "restaurante"],
        keywords_exclude=["licores"],
        total_leads=4,
        tier=2,
    )

    result = use_case.execute(
        campaign="custom",
        universal_request=req,
        dry_run=True,
    )

    assert result["status"] == "success"
    assert result["total_qualified"] == 4
    assert len(result["leads"]) == 4

    # Verify territory fulfillment
    fulfillment = result["territory_fulfillment"]
    assert any("Medellín" in k for k in fulfillment)
    assert any("Bogotá" in k for k in fulfillment)

    # Verify custom campaign name derived from offer
    assert "Empaques Biodegradables" in result["campaign_name"]

    # Verify cadence touches were generated dynamically
    first_lead = result["leads"][0]
    assert "email" in first_lead
    assert "linkedin_xray_url" in first_lead


def test_multi_territory_quota_allocation(mock_web_auditor, mock_contracts_adapter):
    """
    Verifies that exact sub-quotas per territory are strictly tracked and fulfilled.
    """
    harvester = MockHarvester("TechCorp")
    use_case = GenerateProspectsUseCase(
        harvester_co=harvester,
        web_auditor=mock_web_auditor,
        contracts_adapter=mock_contracts_adapter,
        verify_mx_fn=lambda email: (True, "mail.empresa.com"),
    )

    location_allocations = [
        {"country": "CO", "region": "Antioquia", "city": "Medellín", "allocated_leads": 3},
        {"country": "CO", "region": "Valle del Cauca", "city": "Cali", "allocated_leads": 2},
    ]

    result = use_case.execute(
        offer_description="Servicios de ciberseguridad gestionada y SOC 24/7",
        location_allocations=location_allocations,
        limit=5,
        tier=2,
        dry_run=True,
    )

    assert result["status"] == "success"
    assert result["total_qualified"] == 5

    # Check exact delivery per territory
    fulfillment = result["territory_fulfillment"]
    med_key = [k for k in fulfillment if "Medellín" in k][0]
    cali_key = [k for k in fulfillment if "Cali" in k][0]

    assert fulfillment[med_key]["requested_quota"] == 3
    assert fulfillment[med_key]["delivered_count"] == 3

    assert fulfillment[cali_key]["requested_quota"] == 2
    assert fulfillment[cali_key]["delivered_count"] == 2


def test_food_distribution_sector_scenario(mock_web_auditor, mock_contracts_adapter):
    """
    Scenario A: Food & Hospitality Distribution
    Sells frozen foods and catering supplies to hospitality in Medellín and Bogotá.
    """
    harvester = MockHarvester("AgroAlimentos")
    use_case = GenerateProspectsUseCase(
        harvester_co=harvester,
        web_auditor=mock_web_auditor,
        contracts_adapter=mock_contracts_adapter,
        verify_mx_fn=lambda email: (True, "mail.empresa.com"),
    )

    req = UniversalProspectingRequest(
        offer_description="Distribución mayorista de cárnicos congelados y cadena de frío para hoteles y catering",
        sectors=["food_agriculture"],
        locations=[
            LocationAllocation(country="CO", region="Antioquia", city="Medellín", allocated_leads=2),
            LocationAllocation(country="CO", region="Bogotá D.C.", city="Bogotá D.C.", allocated_leads=2),
        ],
        roles=["Director de Compras", "Chef Ejecutivo", "Gerente de Alimentos y Bebidas"],
        keywords_include=["alimentos", "restaurantes"],
        total_leads=4,
        tier=2,
    )

    result = use_case.execute(universal_request=req, dry_run=True)
    assert result["status"] == "success"
    assert result["total_qualified"] == 4
    # Ensure custom roles are included in lead outreach
    import urllib.parse
    lead = result["leads"][0]
    unquoted = urllib.parse.unquote_plus(lead["linkedin_xray_url"])
    assert "Director de Compras" in unquoted or "Chef Ejecutivo" in unquoted


def test_construction_materials_sector_scenario(mock_web_auditor, mock_contracts_adapter):
    """
    Scenario B: Construction & Civil Engineering Supplies
    Sells structural steel and pre-cast concrete to general contractors in Cali.
    """
    harvester = MockHarvester("Constructora")
    use_case = GenerateProspectsUseCase(
        harvester_co=harvester,
        web_auditor=mock_web_auditor,
        contracts_adapter=mock_contracts_adapter,
        verify_mx_fn=lambda email: (True, "mail.empresa.com"),
    )

    req = UniversalProspectingRequest(
        offer_description="Suministro de acero estructural y tuberías de alta resistencia para obras civiles",
        sectors=["construction_infrastructure"],
        locations=[
            LocationAllocation(country="CO", region="Valle del Cauca", city="Cali", allocated_leads=3),
        ],
        roles=["Director de Obra", "Gerente de Proyectos", "Director de Compras"],
        keywords_include=["acero", "construcción"],
        total_leads=3,
        tier=3,
    )

    result = use_case.execute(universal_request=req, dry_run=True)
    assert result["status"] == "success"
    assert result["total_qualified"] == 3
    assert result["tier"] == 3


def test_education_schools_scenario_without_ciiu_code(mock_web_auditor, mock_contracts_adapter):
    """
    Scenario C: Education & School IDs (Chiketto) - Without CIIU code
    Sells PVC student IDs, credentialing and school accessories to schools in Medellín.
    The user did NOT specify a CIIU code.
    Verifies that the engine infers Education CIIU 8530, qualifies schools, and never fails.
    """
    from src.adapters.registries.colombia.secop_harvester_adapter import SecopHarvesterAdapter

    harvester = SecopHarvesterAdapter()
    use_case = GenerateProspectsUseCase(
        harvester_co=harvester,
        web_auditor=mock_web_auditor,
        contracts_adapter=mock_contracts_adapter,
        verify_mx_fn=lambda email: (True, "mail.sanignacio.edu.co"),
    )

    req = UniversalProspectingRequest(
        offer_description="Suministro de carnets estudiantiles en PVC de alta durabilidad y credenciales escolares",
        sectors=["education_schools"],
        ciiu_codes=[],  # Explicitly NO CIIU code supplied by the user
        locations=[
            LocationAllocation(country="CO", region="Antioquia", city="Medellín", allocated_leads=10),
        ],
        roles=["Rector / Rectora", "Coordinador Administrativo", "Director de Colegio"],
        keywords_include=["colegios", "carnets estudiantiles"],
        total_leads=10,
        tier=2,
    )

    result = use_case.execute(universal_request=req, dry_run=True)
    assert result["status"] == "success"
    assert result["total_qualified"] >= 10
    leads = result["leads"]
    assert len(leads) >= 10

    # Verify that CIIU code is properly inferred as Education (85XX)
    for lead in leads[:5]:
        ciiu = lead["ciiu"]
        assert ciiu.code.startswith("85")
        assert "Colegios" in ciiu.sector_macro or "Educación" in ciiu.sector_macro
        assert lead["is_mobile"] is True or lead["phone"].startswith("+57 3") or lead["phone"].startswith("3")
        assert "@" in lead["email"]
        assert ".edu.co" in lead["email"] or ".co" in lead["email"]


def test_schools_high_volume_100_leads_fulfillment(mock_web_auditor, mock_contracts_adapter):
    """
    Verifies high-volume fulfillment of 100 leads of Schools in Medellín
    without crashing, timing out, or dropping out to 0 qualified leads.
    """
    from src.adapters.registries.colombia.secop_harvester_adapter import SecopHarvesterAdapter

    harvester = SecopHarvesterAdapter()
    use_case = GenerateProspectsUseCase(
        harvester_co=harvester,
        web_auditor=mock_web_auditor,
        contracts_adapter=mock_contracts_adapter,
        verify_mx_fn=lambda email: (True, f"mail.{email.split('@')[1]}"),
    )

    req = UniversalProspectingRequest(
        offer_description="Impresión y carnetización en PVC de carnets estudiantiles",
        sectors=["education_schools"],
        ciiu_codes=[],  # No CIIU code supplied
        locations=[
            LocationAllocation(country="CO", region="Antioquia", city="Medellín", allocated_leads=100),
        ],
        keywords_include=["colegio"],
        total_leads=100,
        tier=1,
    )

    result = use_case.execute(universal_request=req, dry_run=True)
    assert result["status"] == "success"
    assert result["total_qualified"] == 100
    assert len(result["leads"]) == 100

    # Ensure all NITs are unique
    seen_nits = {lead["nit"] for lead in result["leads"]}
    assert len(seen_nits) == 100


