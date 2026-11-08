import pytest
from decimal import Decimal
from src.application.use_cases.underwrite_lead_use_case import UnderwriteLeadUseCase, UnderwritingResult
from src.domain.value_objects.ebitda_margin import SolvencyTier


def test_underwrite_lead_clean_healthy():
    use_case = UnderwriteLeadUseCase()
    lead = {
        "nit": "830.076.432-1",
        "clean_name": "MTS Administración e Inversiones",
        "segment": "Grande",
        "city": "Bogotá"
    }

    result = use_case.execute(lead, email_status="valid")
    assert isinstance(result, UnderwritingResult)
    assert result.tax_id == "830076432"
    assert result.operating_revenue == Decimal("48500000000")
    assert result.ebitda == Decimal("14550000000.0")
    assert result.solvency_tier == SolvencyTier.AAA
    assert result.litigation_risk_status == "CLEAN"
    assert len(result.litigation_records) == 0
    assert result.composite_score >= 70.0
    assert "AA" in result.underwriting_grade or "AAA" in result.underwriting_grade
    assert "Aprobado" in result.credit_recommendation


def test_underwrite_lead_executory_debt_and_fiscal_sanction():
    use_case = UnderwriteLeadUseCase()
    # 900123456 has a Proceso Ejecutivo in Rama Judicial AND a Fiscal Debt Sanction in Contraloría
    lead = {
        "nit": "900.123.456-7",
        "clean_name": "Compañía Deudora Morosa",
        "segment": "Mediana",
        "city": "Medellín"
    }

    result = use_case.execute(lead, email_status="valid")
    assert result.litigation_risk_status == "CRITICAL"
    assert len(result.litigation_records) == 2
    assert "CRÍTICA" in result.litigation_summary
    assert result.litigation_score == 0.0
    assert "D - Alerta de Iliquidez" in result.underwriting_grade
    assert "No otorgar crédito comercial" in result.credit_recommendation


def test_underwrite_lead_insolvency_law_1116():
    use_case = UnderwriteLeadUseCase()
    # 900111222 has Ley 1116 Insolvency in Rama Judicial
    lead = {
        "nit": "900.111.222-3",
        "clean_name": "Constructora en Reorganización",
        "segment": "Grande",
        "city": "Bogotá"
    }

    result = use_case.execute(lead, email_status="valid")
    assert result.litigation_risk_status == "CRITICAL"
    assert any("1116" in r.status for r in result.litigation_records)
    assert result.litigation_score == 0.0
    assert "D - Alerta de Iliquidez" in result.underwriting_grade


def test_underwrite_lead_labor_litigation_warning():
    use_case = UnderwriteLeadUseCase()
    # 900654321 has a Proceso Laboral Ordinario in Rama Judicial
    lead = {
        "nit": "900.654.321-0",
        "clean_name": "Servicios Industriales Andinos",
        "segment": "Pequeña",
        "city": "Cali"
    }

    result = use_case.execute(lead, email_status="valid")
    assert result.litigation_risk_status == "WARNING"
    assert len(result.litigation_records) == 1
    assert result.litigation_score == 65.0
    assert "Moderado" in result.credit_recommendation


def test_underwrite_lead_to_dict_serialization():
    use_case = UnderwriteLeadUseCase()
    lead = {
        "nit": "901.999.888-1",
        "clean_name": "Empresa Serializada",
        "segment": "Mediana"
    }

    result = use_case.execute(lead, email_status="valid")
    d = result.to_dict()
    assert d["tax_id"] == "901999888"
    assert "ebitda" in d
    assert "ebitda_margin_percent" in d
    assert "composite_score" in d
    assert "underwriting_grade" in d
    assert "credit_recommendation" in d
