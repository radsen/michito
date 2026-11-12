"""
Unit Tests for Database Taxonomy Models, Seeder, and Autocomplete Query Adapter.
Verifies Phase 1 functionality:
- Creation and seeding of locations across 🇨🇴, 🇩🇴, and 🇪🇨
- Executive decision maker role lookups and cross-country aliases
- Universal CIIU sector search
- Territory coverage validation
- Search intent query logging
"""

import pytest
from src.adapters.db.sql_order_adapter import SqlOrderAdapter
from src.adapters.db.models import (
    TaxonomyLocationModel,
    TaxonomyRoleModel,
    TaxonomySectorModel,
    SearchIntentQueryModel,
)
from src.domain.entities.universal_prospecting_request import (
    UniversalProspectingRequest,
    LocationAllocation,
)


@pytest.fixture
def memory_db_adapter():
    # Use isolated in-memory SQLite database
    adapter = SqlOrderAdapter(database_url="sqlite:///:memory:")
    return adapter


def test_taxonomy_seeding_and_counts(memory_db_adapter):
    with memory_db_adapter._get_session() as s:
        loc_count = s.query(TaxonomyLocationModel).count()
        role_count = s.query(TaxonomyRoleModel).count()
        sec_count = s.query(TaxonomySectorModel).count()

        assert loc_count >= 15, "Should seed at least 15 core locations across CO, DO, EC"
        assert role_count >= 10, "Should seed at least 10 core executive roles"
        assert sec_count >= 10, "Should seed at least 10 universal macro-sectors"


def test_search_locations_by_city_and_aliases(memory_db_adapter):
    # Test direct city match in Colombia
    med_results = memory_db_adapter.search_locations(query="Medellín", country="CO")
    assert len(med_results) > 0
    assert med_results[0]["city_name"] == "Medellín"
    assert med_results[0]["country_code"] == "CO"

    # Test alias match (Valle de Aburrá)
    alias_results = memory_db_adapter.search_locations(query="Valle de Aburrá")
    assert any("Medellín" in r["city_name"] for r in alias_results)

    # Test Dominican Republic location
    dr_results = memory_db_adapter.search_locations(query="Santo Domingo", country="DO")
    assert len(dr_results) > 0
    assert dr_results[0]["country_code"] == "DO"

    # Test Ecuador location
    ec_results = memory_db_adapter.search_locations(query="Quito", country="EC")
    assert len(ec_results) > 0
    assert ec_results[0]["country_code"] == "EC"


def test_validate_location_coverage(memory_db_adapter):
    # Supported cities in 🇨🇴, 🇩🇴, 🇪🇨
    val_med = memory_db_adapter.validate_location("Medellín")
    assert val_med["is_supported"] is True
    assert val_med["location"]["country_code"] == "CO"

    val_dr = memory_db_adapter.validate_location("Santiago de los Caballeros")
    assert val_dr["is_supported"] is True
    assert val_dr["location"]["country_code"] == "DO"

    val_ec = memory_db_adapter.validate_location("Guayaquil")
    assert val_ec["is_supported"] is True
    assert val_ec["location"]["country_code"] == "EC"

    # Unsupported global territory
    val_unsupported = memory_db_adapter.validate_location("Tokyo")
    assert val_unsupported["is_supported"] is False
    assert val_unsupported["location"] is None
    assert "fuera de cobertura" in val_unsupported["message"]


def test_search_roles_and_aliases(memory_db_adapter):
    # Search by standard title
    ops_results = memory_db_adapter.search_roles(query="Operaciones")
    assert len(ops_results) > 0
    assert any("Director de Operaciones" in r["canonical_title"] for r in ops_results)

    # Search by alias (COO)
    coo_results = memory_db_adapter.search_roles(query="COO")
    assert len(coo_results) > 0
    assert any("Director de Operaciones" in r["canonical_title"] for r in coo_results)

    # Search by procurement alias
    proc_results = memory_db_adapter.search_roles(query="Abastecimiento")
    assert len(proc_results) > 0
    assert any("Compras" in r["canonical_title"] for r in proc_results)


def test_search_sectors_and_ciiu(memory_db_adapter):
    # Search food sector
    food_res = memory_db_adapter.search_sectors(query="Alimentos")
    assert len(food_res) > 0
    assert "food_agriculture" in [s["sector_id"] for s in food_res]
    assert "C1011" in food_res[0]["ciiu_codes"]

    # Search construction sector
    const_res = memory_db_adapter.search_sectors(query="construccion")
    assert len(const_res) > 0
    assert "construction_infrastructure" in [s["sector_id"] for s in const_res]


def test_record_search_intent_query(memory_db_adapter):
    q_id = memory_db_adapter.record_search_intent_query(
        raw_prompt="Empresas de logística en Medellín buscando directores de operaciones",
        parsed_criteria={
            "sectors": ["logistics_warehousing"],
            "locations": [{"city": "Medellín", "count": 25}],
            "roles": ["Director de Operaciones"],
        },
        discovered_tokens={"new_role": "Director de Operaciones"},
    )
    assert q_id.startswith("qry_")

    with memory_db_adapter._get_session() as s:
        saved = s.get(SearchIntentQueryModel, q_id)
        assert saved is not None
        assert "logística" in saved.raw_prompt
        assert saved.parsed_criteria["sectors"] == ["logistics_warehousing"]


def test_universal_prospecting_request_dto():
    req_dict = {
        "offer_description": "Distribución de pollo y carnes congeladas",
        "sectors": ["food_agriculture"],
        "ciiu_codes": ["C1011", "C1012"],
        "locations": [
            {"country": "CO", "region": "Antioquia", "city": "Medellín", "allocated_leads": 30},
            {"country": "CO", "region": "Cundinamarca", "city": "Bogotá", "allocated_leads": 20},
        ],
        "roles": ["Director de Compras", "Chef Ejecutivo"],
        "keywords_include": ["restaurantes", "hoteles", "congelados"],
        "keywords_exclude": ["comida rapida callejera"],
        "tier": 2,
        "total_leads": 50,
    }

    req = UniversalProspectingRequest.from_dict(req_dict)
    assert req.total_leads == 50
    assert req.tier == 2
    assert len(req.locations) == 2
    assert req.locations[0].allocated_leads == 30
    assert req.locations[1].allocated_leads == 20
    assert "food_agriculture" in req.sectors
    assert "Director de Compras" in req.roles

    serialized = req.to_dict()
    assert serialized["total_leads"] == 50
    assert serialized["locations"][0]["city"] == "Medellín"
