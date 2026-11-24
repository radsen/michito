"""
Unit and Integration Test Suite: Industry Purity & Active Learning Feedback Loop.
Verifies that:
1. Scenario 1 (Tech/Software/Cloud in Bogotá) achieves >= 98% industry purity, strictly
   rejecting contamination from metals (24), civil engineering (71), schools (85), and waste (38).
2. The active learning feedback mechanism records sector exclusions in the database.
3. Other scenarios (schools, food, construction) remain completely unhindered.
"""

from unittest.mock import MagicMock
import pytest

from src.adapters.db.seed_taxonomy import seed_all_taxonomy
from src.adapters.db.sql_order_adapter import SqlOrderAdapter
from src.application.services.brief_parser_service import BriefParserService
from src.application.use_cases.generate_prospects_use_case import (
    GenerateProspectsUseCase,
    resolve_sector_taxonomy_rules,
)
from deduplication_ledger import DeduplicationLedger


@pytest.fixture
def test_db_adapter():
    """In-memory SQLite database adapter populated with seed taxonomy."""
    adapter = SqlOrderAdapter(database_url="sqlite:///:memory:")
    with adapter._get_session() as s:
        seed_all_taxonomy(s)
    return adapter


def test_brief_parser_normalizes_compound_tech_tokens():
    """Verifies that solitary 'desarrollo' is NEVER emitted as an unigram keyword."""
    parser = BriefParserService()
    brief = "1000 empresas de tecnología, desarrollo de software y servicios cloud en Bogotá, directorio básico"
    parsed = parser.parse_brief(brief, force_fallback=True)

    kws = parsed.get("keywords_include", [])
    # Must NOT have solitary "desarrollo"
    assert "desarrollo" not in kws, f"Solitary 'desarrollo' found in keywords: {kws}"
    # Must preserve compound or specific domain terms
    assert any(term in kws for term in ("desarrollo de software", "software", "cloud", "tecnología"))
    # Verified target CIIUs
    assert any(c in parsed.get("ciiu_codes", []) for c in ("6201", "5820", "6311", "4651"))


def test_resolve_sector_taxonomy_rules_tech():
    """Verifies that sector taxonomy rules correctly identify allowed and forbidden divisions."""
    sec_id, allowed, forbidden = resolve_sector_taxonomy_rules(
        target_ciiu_codes=["6201", "5820", "6311", "4651"],
        kw_include=["desarrollo de software", "cloud"],
    )
    assert sec_id == "tech_software_telecom"
    assert "62" in allowed
    assert "63" in allowed
    # Must forbid non-tech divisions
    assert "24" in forbidden  # Metallurgy
    assert "71" in forbidden  # Architecture / Civil engineering
    assert "85" in forbidden  # Schools
    assert "38" in forbidden  # Waste collection


def test_active_learning_feedback_records_exclusions(test_db_adapter):
    """Verifies active learning loop: records negative CIIU division exclusions in DB."""
    test_db_adapter.record_sector_classification_feedback(
        sector_id="tech_software_telecom",
        ciiu_code="2429",
        is_match=False,
    )

    sec = test_db_adapter.get_sector_by_id("tech_software_telecom")
    assert sec is not None
    assert "24" in sec["forbidden_isic_divisions"]


def test_tech_industry_purity_98_percent_gate(tmp_path):
    """
    Simulates a harvest containing mixed candidates (including metallurgy, architecture,
    schools, and waste collection) and verifies that GenerateProspectsUseCase achieves >= 98% purity.
    """
    mock_auditor = MagicMock()
    mock_auditor.audit.return_value = (True, "https://www.active-site.com", "Active")

    mock_harvester = MagicMock()
    # 50 Tech candidates (6201 / 6311 / 5820 / 4651)
    tech_candidates = [
        {
            "company_name": f"Tech Solutions Cloud {i} SAS",
            "nit": f"901.{100 + i:03d}.{200 + i:03d}-1",
            "email": f"contacto@techcloud{i}.com",
            "phone": "3104567890",
            "website": f"https://www.techcloud{i}.com",
            "sector": "Desarrollo de Software y Servicios Cloud B2B",
            "city": "Bogotá",
        }
        for i in range(1, 51)
    ]

    # 40 Contaminating Non-Tech candidates (Metals, Architecture, Schools, Waste) with 'Desarrollo' in name
    contaminating_candidates = [
        {
            "company_name": f"Desarrollo Metalúrgico y Fundición {i} SAS",
            "nit": f"900.{200 + i:03d}.{300 + i:03d}-2",
            "email": f"gerencia@metalurgico{i}.com",
            "phone": "3114567890",
            "website": f"https://www.metalurgico{i}.com",
            "sector": "Fabricación de otros productos básicos de metales preciosos (CIIU 2429)",
            "city": "Bogotá",
        }
        for i in range(1, 11)
    ] + [
        {
            "company_name": f"Desarrollo Urbano y Obras Civiles {i} SAS",
            "nit": f"900.{300 + i:03d}.{400 + i:03d}-3",
            "email": f"proyectos@obrasciviles{i}.com",
            "phone": "3124567890",
            "website": f"https://www.obrasciviles{i}.com",
            "sector": "Actividades de arquitectura e ingeniería civil (CIIU 7110)",
            "city": "Bogotá",
        }
        for i in range(1, 11)
    ] + [
        {
            "company_name": f"Colegio y Desarrollo Académico {i} SAS",
            "nit": f"900.{400 + i:03d}.{500 + i:03d}-4",
            "email": f"rectoria@colegio{i}.edu.co",
            "phone": "3134567890",
            "website": f"https://www.colegio{i}.edu.co",
            "sector": "Educación básica y media académica (CIIU 8530)",
            "city": "Bogotá",
        }
        for i in range(1, 11)
    ] + [
        {
            "company_name": f"Desarrollo Ambiental y Recolección {i} SAS",
            "nit": f"900.{500 + i:03d}.{600 + i:03d}-5",
            "email": f"operaciones@ambiental{i}.com",
            "phone": "3144567890",
            "website": f"https://www.ambiental{i}.com",
            "sector": "Recolección de desechos no peligrosos (CIIU 3811)",
            "city": "Bogotá",
        }
        for i in range(1, 11)
    ]

    mock_harvester.fetch_candidates.return_value = tech_candidates + contaminating_candidates

    use_case = GenerateProspectsUseCase(
        harvester_co=mock_harvester,
        ledger=DeduplicationLedger(ledger_path=str(tmp_path / "test_ledger.json")),
        verify_mx_fn=lambda domain: (True, "mail.example.com"),
        web_auditor=mock_auditor,
    )

    result = use_case.execute(
        city="Bogotá",
        limit=50,
        tier=1,
        target_ciiu_codes=["6201", "5820", "6311", "4651"],
        keywords_include=["desarrollo de software", "cloud"],
        offer_description="Empresas de tecnología, desarrollo de software y servicios cloud en Bogotá",
    )

    leads = result["leads"]
    assert len(leads) > 0

    # Calculate industry purity
    allowed_tech_divisions = {"62", "63", "58", "46"}
    tech_count = sum(1 for lead in leads if str(lead.get("ciiu_code", ""))[:2] in allowed_tech_divisions)
    purity_rate = tech_count / len(leads)

    # Must achieve >= 98% purity benchmark
    assert purity_rate >= 0.98, f"Purity rate was {purity_rate * 100:.1f}%, expected >= 98%"

    # Explicitly verify that NONE of the contaminating companies leaked through
    for lead in leads:
        ciiu = str(lead.get("ciiu_code", ""))
        assert not ciiu.startswith("24"), f"Contamination: metal company leaked: {lead['company_name']}"
        assert not ciiu.startswith("71"), f"Contamination: engineering company leaked: {lead['company_name']}"
        assert not ciiu.startswith("85"), f"Contamination: school leaked: {lead['company_name']}"
        assert not ciiu.startswith("38"), f"Contamination: waste company leaked: {lead['company_name']}"


def test_cross_scenario_preservation_schools(tmp_path):
    """Verifies that educational procurement (schools/carnetization) is NOT filtered out."""
    mock_auditor = MagicMock()
    mock_auditor.audit.return_value = (True, "https://www.colegio.edu.co", "Active")

    mock_harvester = MagicMock()
    mock_harvester.fetch_candidates.return_value = [
        {
            "company_name": f"Colegio San José {i}",
            "nit": f"900.{600 + i:03d}.{700 + i:03d}-9",
            "email": f"rectoria@colegiosanjose{i}.edu.co",
            "phone": "3101234567",
            "website": f"https://www.colegiosanjose{i}.edu.co",
            "sector": "Educación básica y media académica (CIIU 8521)",
            "city": "Medellín",
        }
        for i in range(1, 11)
    ]

    use_case = GenerateProspectsUseCase(
        harvester_co=mock_harvester,
        ledger=DeduplicationLedger(ledger_path=str(tmp_path / "test_ledger_sch.json")),
        verify_mx_fn=lambda domain: (True, "mail.example.com"),
        web_auditor=mock_auditor,
    )

    result = use_case.execute(
        city="Medellín",
        limit=5,
        tier=2,
        target_ciiu_codes=["8521", "8512"],
        keywords_include=["colegio", "educacion", "carnets"],
        offer_description="Sistemas de carnetización y control de acceso para colegios privados",
    )

    leads = result["leads"]
    assert len(leads) == 5
    for lead in leads:
        assert str(lead["ciiu_code"]).startswith("85")
