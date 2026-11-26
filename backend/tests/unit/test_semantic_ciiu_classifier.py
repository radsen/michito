"""
Unit tests for Semantic DANE/UN ISIC Rev. 4 Classification Engine (Phase 2).
Verifies:
- Expansion of Universal ISIC catalog with 1391, 1399, 1420, 4771, 4772.
- Deterministic regex inference for textile, apparel, footwear, wholesale, and retail domains.
- BM25 confidence scoring with resolve_match_with_confidence.
- Batched Gemini 2.5 Flash classification fallback with token usage tracking.
- TaxonomyGuard sector resolution for fashion and apparel.
"""

from unittest.mock import patch, MagicMock
import pytest

from src.domain.taxonomy.isic_catalog import UNIVERSAL_ISIC_CATALOG
from src.domain.taxonomy.isic_index import get_isic_index
from src.domain.value_objects.ciiu_code import CiiuCode
from src.application.services.semantic_classification_service import SemanticClassificationService
from src.application.use_cases.generate_prospects_use_case import resolve_sector_taxonomy_rules


def test_isic_catalog_textile_and_retail_expansion():
    index = get_isic_index()

    # 1391: Knitted fabrics
    e1391 = index.get_by_code("1391")
    assert e1391 is not None
    assert e1391.division == "13"
    assert "punto" in e1391.title.lower()

    # 1399: Other textiles ncp
    e1399 = index.get_by_code("1399")
    assert e1399 is not None
    assert e1399.division == "13"

    # 1420: Fur apparel
    e1420 = index.get_by_code("1420")
    assert e1420 is not None
    assert e1420.division == "14"

    # 4771: Retail apparel
    e4771 = index.get_by_code("4771")
    assert e4771 is not None
    assert e4771.division == "47"
    assert "prendas de vestir" in e4771.title.lower()

    # 4772: Retail footwear/leather
    e4772 = index.get_by_code("4772")
    assert e4772 is not None
    assert e4772.division == "47"
    assert "calzado" in e4772.title.lower()


def test_ciiu_code_infer_from_text_textile_apparel_footwear():
    # 1410 - Apparel / Confección
    c1 = CiiuCode.infer_from_text("CONFECCIONES LEONISA S.A.S.", "ventas@leonisa.com")
    assert c1.code == "1410"
    assert "14" in c1.code

    c2 = CiiuCode.infer_from_text("TALLER DE MAQUILA TEXTIL Y COSTURA MEDELLIN")
    assert c2.code == "1410"

    # 1521 - Footwear / Calzado
    c3 = CiiuCode.infer_from_text("FABRICA DE CALZADO Y BOTAS CORONA SAS")
    assert c3.code == "1521"
    assert "15" in c3.code

    c4 = CiiuCode.infer_from_text("MARROQUINERIA Y CUEROS VELEZ")
    assert c4.code == "1521"

    # 1312 - Textile Weaving / Telas
    c5 = CiiuCode.infer_from_text("HILANDERIA Y TEJEDURIA FABRICATO DE COLOMBIA")
    assert c5.code == "1312"
    assert "13" in c5.code

    c6 = CiiuCode.infer_from_text("TEXTILES DEL ABURRA SAS", raw_desc="Producción de telas e hilados")
    assert c6.code == "1312"

    # 4641 - Wholesale Textiles & Clothing
    c7 = CiiuCode.infer_from_text("DISTRIBUIDORA Y MAYORISTA DE TELAS EL CONDOR SAS")
    assert c7.code == "4641"

    # 4771 - Retail Apparel / Boutique
    c8 = CiiuCode.infer_from_text("BOUTIQUE LAURA TIENDA DE ROPA SAS")
    assert c8.code == "4771"

    # 4772 - Retail Footwear / Zapatería
    c9 = CiiuCode.infer_from_text("ZAPATERIA Y TIENDA DE CALZADO SPRING STEP")
    assert c9.code == "4772"


def test_isic_index_resolve_match_with_confidence():
    index = get_isic_index()
    # High confidence match for explicit keyword query
    entry, score = index.resolve_match_with_confidence("hilanderia hilaza algodon hilado")
    assert entry is not None
    assert entry.code == "1311"
    assert score > 3.0

    # Ambiguous / generic text has low score or None
    entry_low, score_low = index.resolve_match_with_confidence("holding corporativo xyz 123")
    assert score_low < 3.0 or entry_low is None


def test_semantic_classification_service_local():
    svc = SemanticClassificationService(api_key="")

    ciiu_obj, conf, source = svc.classify_company("CONFECCIONES MODA Y ESTILO SAS")
    assert ciiu_obj.code == "1410"
    assert conf >= 0.90
    assert source == "regex"

    ciiu_obj2, conf2, source2 = svc.classify_company("GRUPO HOLDING CORPORATIVO XYZ 123")
    # Low confidence or fallback
    assert conf2 < 0.35


def test_semantic_classification_service_gemini_fallback():
    mock_resp_json = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": '{"classifications": [{"id": 0, "ciiu_code": "1410", "title": "Confección de prendas de vestir", "confidence": 0.92}]}'
                        }
                    ]
                }
            }
        ],
        "usageMetadata": {
            "promptTokenCount": 120,
            "candidatesTokenCount": 35,
            "totalTokenCount": 155,
        },
    }

    svc = SemanticClassificationService(api_key="mock_test_key")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_resp_json

    with patch("httpx.Client.post", return_value=mock_resp):
        candidates = [
            {"company_name": "GRUPO HOLDING CORPORATIVO XYZ 123 SAS", "email": "info@grupocorporativo.co"}
        ]
        results = svc.batch_classify_ambiguous_companies(candidates, country_code="CO")

        assert len(results) == 1
        assert results[0]["ciiu_code"] == "1410"
        assert results[0]["ciiu_source"] == "gemini_flash"
        assert results[0]["ciiu_confidence"] == 0.92
        assert "ciiu_token_usage" in results[0]
        assert results[0]["ciiu_token_usage"]["model"] == "gemini-2.5-flash"
        assert results[0]["ciiu_token_usage"]["cost_cop"] > 0


def test_taxonomy_guard_fashion_sector_resolution():
    # Test sector synonym "fashion"
    sector_id, allowed, forbidden = resolve_sector_taxonomy_rules(
        sectors=["fashion"],
        kw_include=["confecciones", "telas", "ropa"],
    )
    assert sector_id == "fashion_apparel_textiles"
    assert "13" in allowed  # Textiles
    assert "14" in allowed  # Confección
    assert "15" in allowed  # Calzado / Cuero
    assert "46" in allowed  # Mayoristas de prendas / telas
    assert "47" in allowed  # Retail de prendas / calzado

    # Test sector synonym "moda"
    sec_id_moda, allowed_moda, _ = resolve_sector_taxonomy_rules(
        sectors=["moda"],
    )
    assert sec_id_moda == "fashion_apparel_textiles"
    assert "14" in allowed_moda

    # Test by target CIIU codes
    sec_id_ciiu, allowed_ciiu, _ = resolve_sector_taxonomy_rules(
        target_ciiu_codes=["1410", "1521"],
    )
    assert sec_id_ciiu == "fashion_apparel_textiles"
    assert "14" in allowed_ciiu
    assert "15" in allowed_ciiu
