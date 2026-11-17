import pytest
import json
from unittest.mock import patch, MagicMock
from decimal import Decimal
from src.adapters.registries.colombia.supersociedades_soda_adapter import SupersociedadesSodaAdapter
from src.application.dto.search_request_dto import CompanyFilterDto

def test_soda_adapter_fetch_companies():
    adapter = SupersociedadesSodaAdapter(use_live_api=False)
    filter_dto = CompanyFilterDto(country_code="CO", industry="facility_management", city="Bogotá", min_revenue=Decimal("10000000000"))
    companies = adapter.fetch_companies(filter_dto)
    assert len(companies) > 0
    for comp in companies:
        assert comp.industry == "facility_management"
        assert comp.id.startswith("CO-")

def test_soda_adapter_curated_financials():
    adapter = SupersociedadesSodaAdapter(use_live_api=False)
    financials = adapter.get_financial_statements("830.076.432-1")
    assert financials.revenue == Decimal("48500000000")

    raw = adapter.fetch_raw_financials("830.076.432-1")
    assert raw["has_audited_financials"] is True
    assert raw["operating_revenue"] == 48500000000
    assert raw["cost_of_sales"] == 48500000000 * 0.6

def test_soda_adapter_factual_fallback_for_unknown():
    adapter = SupersociedadesSodaAdapter(use_live_api=False)
    raw = adapter.fetch_raw_financials("999.999.999-9")
    assert raw["has_audited_financials"] is False
    assert raw["operating_revenue"] == 0
    assert "sin reporte NIIF" in raw["financial_source"]

    fin = adapter.get_financial_statements("999.999.999-9")
    assert fin.revenue == Decimal("0")
    assert fin.ebitda == Decimal("0")

def test_soda_adapter_fetch_niif_pyme_live_or_mocked():
    adapter = SupersociedadesSodaAdapter(use_live_api=True)
    # Mocking urllib.request.urlopen to verify SoQL parsing for Grupo 2 PYME
    mock_pyme_records = [
        {"fecha_corte": "2023-12-31T00:00:00.000", "punto_entrada": "40 NIIF Pymes - Individuales", "concepto": "Ingresos de actividades ordinarias", "valor": "249500"},
        {"fecha_corte": "2023-12-31T00:00:00.000", "punto_entrada": "40 NIIF Pymes - Individuales", "concepto": "Costo de ventas", "valor": "186800"},
        {"fecha_corte": "2023-12-31T00:00:00.000", "punto_entrada": "40 NIIF Pymes - Individuales", "concepto": "Gastos de administración", "valor": "50000"},
        {"fecha_corte": "2023-12-31T00:00:00.000", "punto_entrada": "40 NIIF Pymes - Individuales", "concepto": "Gastos de ventas", "valor": "12200"}
    ]
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(mock_pyme_records).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response

        res = adapter._fetch_from_soda_niif("900152104")
        assert res is not None
        assert res["has_audited_financials"] is True
        assert "PYMES" in res["financial_source"]
        # 249500 miles = 249,500,000 COP
        assert res["operating_revenue"] == 249500000.0
        assert res["cost_of_sales"] == 186800000.0
        assert res["operating_expenses"] == 62200000.0

def test_soda_adapter_fetch_top10k_mocked():
    adapter = SupersociedadesSodaAdapter(use_live_api=True)
    mock_top10k_records = [
        {
            "nit": 899999068,
            "razon_social": "ECOPETROL S.A.",
            "a_o_de_corte": "2023.0",
            "ingresos_operacionales": "$ 143.1",
            "ganancia_p_rdida": "$ 19.1"
        }
    ]
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(mock_top10k_records).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response

        res = adapter._fetch_from_soda_top10k("899999068")
        assert res is not None
        assert res["has_audited_financials"] is True
        assert "10.000 Empresas" in res["financial_source"]
        assert res["operating_revenue"] == 143.1 * 1_000_000_000_000.0

def test_soda_adapter_screen_litigation_insolvency():
    adapter = SupersociedadesSodaAdapter(use_live_api=True)
    mock_caratula = [
        {
            "nit": 900123456,
            "fecha_corte": "2023-12-31T00:00:00.000",
            "concepto": "Estado actual de la sociedad",
            "valor": "EN ACUERDO DE REORGANIZACION - LEY 1116"
        }
    ]
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(mock_caratula).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response

        records = adapter.screen_litigation("900.123.456-1")
        assert len(records) == 1
        assert records[0].id == "LIT-SODA-900123456"
        assert records[0].company_id == "CO-900123456"
        assert "Ley 1116" in records[0].case_number
        assert records[0].status == "CRITICAL"


def test_soda_adapter_live_never_uses_hardcoded_registry():
    """
    Guarantees that in live production mode (use_live_api=True), the adapter NEVER
    falls back to hardcoded test fixtures when SODA does not contain a company.
    It must report factual non-presence (zero hallucination).
    """
    adapter = SupersociedadesSodaAdapter(use_live_api=True)
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_response = MagicMock()
        # SODA returns empty list (company not in live SODA)
        mock_response.read.return_value = json.dumps([]).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # Even though 830.076.432-1 exists in TEST_FIXTURE_COLOMBIAN_REGISTRY,
        # in live mode it must NOT return the fixture!
        raw = adapter.fetch_raw_financials("830.076.432-1")
        assert raw["has_audited_financials"] is False
        assert raw["operating_revenue"] == 0
        assert "sin reporte NIIF centralizado" in raw["financial_source"]
