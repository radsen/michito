"""
Stage 4 AI Conversational Agents & Natural Language Brief Parsing Unit Tests.
Verifies BriefParserService (Gemini Flash & sub-millisecond local BM25 fallback),
bidirectional intent parsing (Sales vs Procurement), multi-country geography (CO, DO, EC),
and the WhatsApp conversational webhook.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from src.application.services.brief_parser_service import BriefParserService
from src.entrypoints.api.main import app
from clients.whatsapp.bot_service import WhatsAppBotService


@pytest.fixture
def client():
    return TestClient(app)


def test_brief_parser_buyer_procurement_directionality():
    """
    Tests that a buyer / procurement prompt correctly infers 'client_to_vendors',
    extracts furniture/maintenance CIIU codes, splits quotas across Medellín and Bogotá,
    and assigns vendor-facing sales roles.
    """
    parser = BriefParserService()
    brief = "Necesito comprar muebles y escritorios para remodelar 3 sedes de Tinkko en Medellín y Bogotá, buscamos talleres o fabricantes"
    result = parser.parse_brief(brief, force_fallback=True)

    assert result["directionality"] == "client_to_vendors"
    assert "3110" in result["ciiu_codes"] or "9524" in result["ciiu_codes"]
    assert any("Gerente Comercial" in r or "Director de Ventas" in r for r in result["roles"])
    
    # Check locations
    cities = [loc["city"] for loc in result["locations"]]
    assert "Medellín" in cities
    assert "Bogotá" in cities
    assert result["rfq_specifications"] is not None
    assert "Tinkko" in result["rfq_specifications"]


def test_brief_parser_cross_border_sales_schools():
    """
    Tests that a sales prompt across Dominican Republic and Ecuador correctly infers 'vendor_to_clients',
    matches school CIIU codes (8530/8521), allocates quotas between DO and EC,
    and assigns school rector roles.
    """
    parser = BriefParserService()
    brief = "Vendo software de facturación electrónica y gestión académica para colegios privados en Santo Domingo y Quito, 50 prospectos"
    result = parser.parse_brief(brief, force_fallback=True)

    assert result["directionality"] == "vendor_to_clients"
    assert "8530" in result["ciiu_codes"] or "8521" in result["ciiu_codes"]
    assert result["limit"] == 50
    assert result["tier"] == 2

    # Check multi-country allocation
    countries = {loc["country"] for loc in result["locations"]}
    assert "DO" in countries
    assert "EC" in countries
    assert any("Rector" in r for r in result["roles"])


def test_brief_parser_tier3_solvency_and_ebitda():
    """
    Tests that audit/solvency/EBITDA terminology automatically promotes the request to Tier 3.
    """
    parser = BriefParserService()
    brief = "Búscame 25 empresas de transporte de carga en Cali con balance auditado y EBITDA superior al 12%"
    result = parser.parse_brief(brief, force_fallback=True)

    assert result["tier"] == 3
    assert result["limit"] == 25
    cities = [loc["city"] for loc in result["locations"]]
    assert "Cali" in cities


def test_brief_parser_gemini_flash_mock():
    """
    Tests that if Gemini Flash responds with structured JSON, BriefParserService parses it cleanly.
    """
    mock_gemini_response = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": (
                                '{"directionality": "client_to_vendors", '
                                '"sectors": ["industrial_machinery"], '
                                '"ciiu_codes": ["2811", "3110"], '
                                '"roles": ["Director de Planta", "Gerente Comercial"], '
                                '"locations": [{"country": "CO", "city": "Medellín", "allocated_leads": 20}], '
                                '"limit": 20, "tier": 2, "rfq_specifications": "Calderas industriales", '
                                '"keywords_include": ["calderas", "vapor"], "keywords_exclude": [], '
                                '"confidence_score": 0.98}'
                            )
                        }
                    ]
                }
            }
        ]
    }

    with patch("httpx.Client.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_gemini_response
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp

        parser = BriefParserService(gemini_api_key="mock_key_xyz")
        res = parser.parse_brief("Cotizar calderas industriales en Medellín para 20 proveedores")

        assert res["directionality"] == "client_to_vendors"
        assert res["source"] == "gemini-flash"
        assert "3110" in res["ciiu_codes"] or "2811" in res["ciiu_codes"]


def test_api_parse_brief_endpoint(client):
    """
    Tests POST /api/v1/prospecting/parse-brief.
    """
    payload = {
        "prompt": "Vendo servicios de debida diligencia legal y cobranzas a empresas en Bogotá y Bucaramanga, 30 cuentas",
        "force_fallback": True
    }
    response = client.post("/api/v1/prospecting/parse-brief", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    parsed = data["data"]
    assert parsed["directionality"] == "vendor_to_clients"
    assert parsed["limit"] == 30
    assert "query_id" in parsed
    cities = [loc["city"] for loc in parsed["locations"]]
    assert "Bogotá" in cities
    assert "Bucaramanga" in cities


def test_whatsapp_webhook_verification(client):
    """
    Tests GET /api/v1/webhooks/whatsapp verification handshake.
    """
    with patch.dict("os.environ", {"WHATSAPP_VERIFY_TOKEN": "secret_test_token"}):
        # Valid token
        res = client.get("/api/v1/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=secret_test_token&hub.challenge=test_challenge_123")
        assert res.status_code == 200
        assert res.text == "test_challenge_123"

        # Invalid token
        res_invalid = client.get("/api/v1/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=wrong_token&hub.challenge=test_challenge_123")
        assert res_invalid.status_code == 403


def test_whatsapp_webhook_incoming_message_meta_format(client):
    """
    Tests POST /api/v1/webhooks/whatsapp with Meta Cloud API JSON payload.
    """
    meta_payload = {
        "object": "whatsapp_business_account",
        "echo_responses": True,
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "from": "+573009876543",
                                    "text": {"body": "Necesitamos cotizar servicio de carpintería y muebles en Medellín"}
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }

    with patch("clients.whatsapp.bot_service.requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"order_id": "ord_wa_998877"}
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp

        res = client.post("/api/v1/webhooks/whatsapp", json=meta_payload)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert len(data["responses"]) == 1
        resp_obj = data["responses"][0]
        assert resp_obj["action"] == "reply"
        assert resp_obj["to"] == "+573009876543"
        assert "ord_wa_998877" in resp_obj["message"]


def test_whatsapp_bot_order_status_inquiry():
    """
    Tests that typing 'estado ord_20261113_xyz' fetches and replies with order status.
    """
    bot = WhatsAppBotService(api_base_url="http://test")

    with patch("clients.whatsapp.bot_service.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "order": {
                "order_id": "ord_20261113_abc123",
                "status": "awaiting_payment",
                "leads": [{"company_name": "Test Co 1"}, {"company_name": "Test Co 2"}]
            }
        }
        mock_get.return_value = mock_resp

        reply = bot.handle_incoming_message("+573100000000", "Consultar estado ord_20261113_abc123")
        assert reply["action"] == "reply"
        assert "AWAITING_PAYMENT" in reply["message"]
        assert "Prospectos Validados: *2*" in reply["message"]
        assert "ord_20261113_abc123" in reply["message"]


def test_brief_parser_cross_border_tier_cap():
    """
    Tests that a mixed brief with Colombia and Ecuador automatically caps Tier 3 to Tier 2
    and attaches an informational notice explaining statutory NIIF availability.
    """
    parser = BriefParserService()
    brief = "Búscame 30 empresas de logística en Medellín y Quito con balance auditado y EBITDA"
    res = parser.parse_brief(brief, force_fallback=True)

    # Must be capped at Tier 2 because Quito is outside Colombia
    assert res["tier"] == 2
    assert res["tier_notice"] is not None
    assert "exclusivamente para entidades registradas en Colombia" in res["tier_notice"]
    countries = {loc["country"] for loc in res["locations"]}
    assert "CO" in countries
    assert "EC" in countries


def test_brief_parser_colombia_tier3_preserved():
    """
    Tests that a 100% Colombian brief asking for audited financial statements retains Tier 3.
    """
    parser = BriefParserService()
    brief = "Búscame 20 empresas de transporte en Cali y Bogotá con balance auditado y EBITDA"
    res = parser.parse_brief(brief, force_fallback=True)

    assert res["tier"] == 3
    assert res.get("tier_notice") is None
    countries = {loc["country"] for loc in res["locations"]}
    assert countries == {"CO"}


def test_brief_parser_city_disambiguation():
    """
    Tests that multi-word city names like 'Santiago de Cali' resolve to CO/Cali,
    while 'Santiago de los Caballeros' resolves to DO/Santiago.
    """
    parser = BriefParserService()

    cali_res = parser.parse_brief("15 proveedores en Santiago de Cali para transporte", force_fallback=True)
    cali_cities = [(loc["country"], loc["city"]) for loc in cali_res["locations"]]
    assert ("CO", "Cali") in cali_cities

    dr_res = parser.parse_brief("15 proveedores en Santiago de los Caballeros para colegios", force_fallback=True)
    dr_cities = [(loc["country"], loc["city"]) for loc in dr_res["locations"]]
    assert ("DO", "Santiago") in dr_cities


def test_profile_intent_use_case_no_synthetic_multiplier():
    """
    Tests that ProfileB2BIntentUseCase does NOT multiply the requested batch size by 4x,
    maintains exact truth in advertising, and respects Dominican Republic DOP currency.
    """
    from src.application.use_cases.profile_b2b_intent_use_case import ProfileB2BIntentUseCase
    use_case = ProfileB2BIntentUseCase()

    res = use_case.execute("Busco clientes para espacios de oficinas en coworkings en República Dominicana, 100 de auditoría completa")
    assert res["status"] == "success"
    assert res["country"] == "DO"
    assert res["recommended_limit"] == 100
    # Must NOT multiply by 4 to invent 400
    assert res["estimated_matches"] == 100
    assert "400" not in res["summary_message"]
    assert "Configuramos tu lote en 100 decisores" in res["summary_message"]
    # Honors Tier 3 for auditoria
    assert res["recommended_tier"] == 3
    # Pricing in DOP
    assert res["pricing"]["currency"] == "DOP"
    assert res["campaign_id"] == "tinkko_dr_offices"


def test_locales_no_competitor_mentions():
    """
    Tests that landing page localization files do not mention Apollo or ZoomInfo.
    """
    import json
    import os
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    locales_dir = os.path.join(repo_root, "clients", "web", "src", "locales")

    for fname in ["es_CO.json", "en_US.json"]:
        fpath = os.path.join(locales_dir, fname)
        if os.path.exists(fpath):
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
                assert "Apollo" not in content, f"Found 'Apollo' mention in {fname}"
                assert "ZoomInfo" not in content, f"Found 'ZoomInfo' mention in {fname}"


def test_custom_dynamic_intent_construction_republica_dominicana():
    """
    Tests that a 100% custom brief ('Busca constructoras comprando sanitarios en República Dominicana')
    matches genuine construction entities with Zero-Knowledge protection and does NOT
    force into unrelated presets or fake mock templates.
    """
    from src.application.use_cases.profile_b2b_intent_use_case import ProfileB2BIntentUseCase
    use_case = ProfileB2BIntentUseCase()

    query = "Busca constructoras comprando sanitarios para casas u oficinas en República Dominicana, lote de 50"
    res = use_case.execute(query)

    assert res["status"] == "success"
    assert res["country"] == "DO"
    assert res["city"] in ("Santo Domingo", "Santiago")
    assert res["recommended_limit"] == 50
    assert res["pricing"]["currency"] == "DOP"

    # Must find matching construction lead with Zero-Knowledge masking
    assert res["sample_preview"] is not None
    assert "C••••" in res["sample_preview"]["company_name"]
    assert res["sample_preview"]["statutory_badge"] == "✓ RNC Vigente en DGII / Cámara de Comercio"
    assert res["sample_preview"]["flag"] == "🇩🇴"
    # Never expose raw phone or email
    assert "••••" in res["sample_preview"]["email"]
    assert "•••" in res["sample_preview"]["phone"]


def test_unmatched_intent_truthful_zero_result():
    """
    Tests that when no authentic entities match an outlandish or unavailable niche,
    the engine reports 0 matches and sample_preview is None rather than inventing fake data.
    """
    from src.application.use_cases.profile_b2b_intent_use_case import ProfileB2BIntentUseCase
    use_case = ProfileB2BIntentUseCase()

    query = "Busco plantas de enriquecimiento de uranio y reactores nucleares en Santiago de los Caballeros, 25 empresas"
    res = use_case.execute(query)

    assert res["status"] == "success"
    assert res["country"] == "DO"
    assert res["estimated_matches"] == 0
    assert res["sample_preview"] is None
    assert "No fue posible encontrar la información solicitada" in res["summary_message"]
