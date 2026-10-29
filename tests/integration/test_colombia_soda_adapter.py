import pytest
from src.adapters.registries.colombia.supersociedades_soda_adapter import SupersociedadesSodaAdapter
from src.application.dto.search_request_dto import CompanyFilterDto
from decimal import Decimal

def test_soda_adapter_fetch_companies():
    adapter = SupersociedadesSodaAdapter(use_live_api=False)
    filter_dto = CompanyFilterDto(country_code="CO", industry="facility_management", city="Bogotá", min_revenue=Decimal("10000000000"))
    companies = adapter.fetch_companies(filter_dto)
    assert len(companies) > 0
    for comp in companies:
        assert comp.industry == "facility_management"
        # tax_id does not have country_code. We just assert the ID prefix
        assert comp.id.startswith("CO-")

def test_soda_adapter_financials():
    adapter = SupersociedadesSodaAdapter(use_live_api=False)
    financials = adapter.get_financial_statements("830.076.432-1")
    assert financials.revenue == Decimal("48500000000")

    raw = adapter.fetch_raw_financials("830.076.432-1")
    assert raw["operating_revenue"] == 48500000000
    assert raw["cost_of_sales"] == 48500000000 * 0.6
