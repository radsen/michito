import pytest
from unittest.mock import patch, Mock
from clients.whatsapp.bot_service import WhatsAppBotService

def test_parse_message_campaigns():
    bot = WhatsAppBotService()
    
    msg1 = "Quiero 50 prospectos de hebi en bogota tier 2"
    parsed1 = bot._parse_message(msg1)
    assert parsed1["campaign_id"] == "hebi"
    assert parsed1["city"] == "Bogota"
    assert parsed1["tier"] == 2
    assert parsed1["limit"] == 50
    
    msg2 = "Necesito de tinkko en cali 15 empresas"
    parsed2 = bot._parse_message(msg2)
    assert parsed2["campaign_id"] == "tinkko_enterprise_offices"
    assert parsed2["city"] == "Cali"
    assert parsed2["limit"] == 15
    # Tier defaults to 1 if not found
    assert parsed2["tier"] == 1

def test_parse_message_single_digit():
    bot = WhatsAppBotService()
    
    msg = "2"
    parsed = bot._parse_message(msg)
    assert parsed["campaign_id"] == "hebi"
    assert parsed["limit"] == 10
    
    msg = "6"
    parsed = bot._parse_message(msg)
    assert parsed["campaign_id"] == "warehouse_aburra_norte"
    assert parsed["limit"] == 10
    assert parsed["tier"] == 1

def test_handle_incoming_message_menu():
    bot = WhatsAppBotService()
    response = bot.handle_incoming_message("+573001234567", "hola")
    assert response["action"] == "send_menu"
    assert "Bienvenido al motor" in response["message"]

@patch("clients.whatsapp.bot_service.requests.post")
def test_handle_incoming_message_order(mock_post):
    # Setup mock response
    mock_resp = Mock()
    mock_resp.json.return_value = {"order_id": "ord_test_123"}
    mock_resp.raise_for_status.return_value = None
    mock_post.return_value = mock_resp
    
    bot = WhatsAppBotService(api_base_url="http://test")
    response = bot.handle_incoming_message("+573001234567", "Quiero de blueoil 20 tier 3 en barranquilla")
    
    # Check if requests.post was called with right args
    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert args[0] == "http://test/orders"
    
    payload = kwargs["json"]
    assert payload["client"]["phone"] == "+573001234567"
    assert payload["client"]["channel"] == "whatsapp"
    assert payload["request"]["campaign_id"] == "blueoil"
    assert payload["request"]["city"] == "Barranquilla"
    assert payload["request"]["limit"] == 20
    assert payload["request"]["tier"] == 3
    
    # Check response from bot
    assert response["action"] == "reply"
    assert response["to"] == "+573001234567"
    assert "ord_test_123 está en proceso" in response["message"]

def test_notify_awaiting_payment():
    bot = WhatsAppBotService()
    response = bot.notify_awaiting_payment(
        to_number="+573001234567", 
        order_id="ord_999", 
        teaser_summary="- Company A\n- Company B", 
        checkout_url="http://checkout.local"
    )
    
    assert response["action"] == "reply"
    assert response["to"] == "+573001234567"
    assert "tu orden ord_999 está lista" in response["message"].lower()
    assert "- Company A" in response["message"]
    assert "http://checkout.local" in response["message"]
