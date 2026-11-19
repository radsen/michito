import pytest
from src.application.use_cases.generate_prospects_use_case import (
    classify_phone,
    mask_teaser_phone,
    GenerateProspectsUseCase,
)
from src.adapters.registries.colombia.supersociedades_soda_adapter import SupersociedadesSodaAdapter
from src.application.use_cases.underwrite_lead_use_case import UnderwriteLeadUseCase


def test_classify_colombian_mobile_phone():
    res = classify_phone("3104567890", country="CO")
    assert res["is_mobile"] is True
    assert res["line_type"] == "Móvil Corporativo (WhatsApp)"
    assert res["formatted"] == "+57 310 456 7890"
    assert res["whatsapp_url"] == "https://wa.me/573104567890"


def test_classify_colombian_landline_pbx():
    # 601 (Bogotá) 7-digit number
    res = classify_phone("6013456789", country="CO")
    assert res["is_mobile"] is False
    assert "PBX" in res["line_type"]
    assert res["formatted"] == "+57 (601) 345 6789"
    assert res["whatsapp_url"] == ""
    assert "No aplica" in res["whatsapp_display"]


def test_classify_colombian_7digit_local():
    res = classify_phone("4441234", country="CO")
    assert res["is_mobile"] is False
    assert "PBX" in res["line_type"] or "Fija" in res["line_type"]
    assert res["whatsapp_url"] == ""


def test_classify_dominican_phone():
    res_mob = classify_phone("8295551234", country="DO")
    assert res_mob["is_mobile"] is True
    assert "WhatsApp" in res_mob["line_type"]
    assert res_mob["whatsapp_url"] == "https://wa.me/18295551234"

    res_land = classify_phone("8092223344", country="DO")
    assert res_land["is_mobile"] is True
    assert res_land["whatsapp_url"] == "https://wa.me/18092223344"


def test_classify_ecuador_phone():
    res_mob = classify_phone("0991234567", country="EC")
    assert res_mob["is_mobile"] is True
    assert "WhatsApp" in res_mob["line_type"]
    assert res_mob["whatsapp_url"] == "https://wa.me/593991234567"

    res_pbx = classify_phone("022345678", country="EC")
    assert res_pbx["is_mobile"] is False
    assert "PBX" in res_pbx["line_type"] or "Fija" in res_pbx["line_type"]
    assert res_pbx["whatsapp_url"] == ""


def test_mask_teaser_phone_landline_vs_mobile():
    mob = mask_teaser_phone("3104567890", country="CO")
    assert mob == "+57 310 ••• ••••"

    pbx = mask_teaser_phone("6013456789", country="CO")
    assert "PBX" in pbx
    assert "601" in pbx


def test_truthful_underwriting_without_hallucinated_billions():
    uw = UnderwriteLeadUseCase()
    # Lead not in top 10,000 audited entities
    lead = {
        "nit": "901.888.777-2",
        "clean_name": "Tecnología y Suministros PYME SAS",
        "segment": "Pequeña",
        "city": "Bucaramanga",
        "contracts_data": {
            "has_contracts": True,
            "total_value_display": "$180.000.000 COP",
            "top_contract_entity": "Alcaldía de Bucaramanga",
        }
    }
    result = uw.execute(lead, email_status="valid")
    # Verify no fake $25B or $85B was hallucinated
    assert result.operating_revenue == 0
    assert result.ebitda == 0
    assert result.has_audited_financials is False
    assert "sin reporte niif centralizado" in result.financial_source.lower()
    # Solvency is evaluated on verified SECOP contract history
    assert "Capacidad operativa respaldada en contratación pública" in result.solvency_summary
    assert "$180.000.000 COP" in result.solvency_summary
