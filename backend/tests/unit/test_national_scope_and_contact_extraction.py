import pytest
from src.application.services.brief_parser_service import BriefParserService
from src.application.services.location_taxonomy_service import LocationTaxonomyService


def test_brief_parser_national_scope_and_volume_extraction():
    parser = BriefParserService()
    prompt = (
        "Dame 1000 clientes del mercado diseño, pinturas regalos corpotarivos, brandid "
        "Que tengan whatsapp y correo, donde pueda contactarme con la person, quiero que sean de toda colombia"
    )
    result = parser.parse_brief(prompt, force_fallback=True)

    assert result["limit"] == 1000
    assert result["geographic_scope"] == "national"
    assert result["tier"] == 2
    assert len(result["locations"]) >= 1
    assert result["locations"][0]["country"] == "CO"
    assert result["locations"][0]["city"] in ("Colombia", "Nacional")
    # Verify CIIU codes or keywords were extracted
    assert len(result["ciiu_codes"]) > 0 or len(result["keywords_include"]) > 0


def test_location_taxonomy_service_national_resolution():
    loc_service = LocationTaxonomyService()

    # 1. Direct national aliases
    hier_colombia = loc_service.resolve_location("CO", "Colombia")
    assert hier_colombia.location_id == "co_nacional"
    assert hier_colombia.country_code == "CO"

    hier_nacional = loc_service.resolve_location("CO", "Nacional")
    assert hier_nacional.location_id == "co_nacional"

    hier_all = loc_service.resolve_location("CO", "all")
    assert hier_all.location_id == "co_nacional"

    rings_nacional = hier_nacional.get_rings_for_scope("national")
    flat_cities = [c for _, cities in rings_nacional for c in cities]
    assert "Bogotá" in flat_cities
    assert "Medellín" in flat_cities
    assert "Cali" in flat_cities

    # 2. Dynamic national expansion from a specific city
    hier_bogota = loc_service.resolve_location("CO", "Bogotá")
    assert hier_bogota.location_id == "co_bogota_dc"

    rings_metro = hier_bogota.get_rings_for_scope("metro_area")
    metro_cities = [c for _, cities in rings_metro for c in cities]
    assert "Bogotá" in metro_cities
    assert "Medellín" not in metro_cities  # Stays localized

    rings_national = hier_bogota.get_rings_for_scope("national")
    nat_cities = [c for _, cities in rings_national for c in cities]
    assert "Bogotá" in nat_cities
    assert "Medellín" in nat_cities  # Expands to national hubs
    assert "Cali" in nat_cities
