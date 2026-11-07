import re
import os
import requests
from typing import Dict, Any, Optional

class WhatsAppBotService:
    def __init__(self, api_token: Optional[str] = None, api_base_url: Optional[str] = None):
        self.api_token = api_token or os.environ.get("WHATSAPP_API_TOKEN", "")
        self.api_base_url = api_base_url or os.environ.get("API_BASE_URL", "http://localhost:8000/api/v1")

    def _parse_message(self, text: str) -> Dict[str, Any]:
        """Parses natural language text to extract order parameters."""
        clean_text = text.lower()
        
        # 1. Campaign Intent
        campaign_map = {
            "tinkko": "tinkko_enterprise_offices",
            "hebi": "hebi",
            "chiketto": "chiketto",
            "blueoil": "blueoil",
            "facility": "facility_services_b2b",
            "aburra": "warehouse_aburra_norte",
            "warehouse": "warehouse_aburra_norte",
            "1": "tinkko_enterprise_offices",
            "2": "hebi",
            "3": "chiketto",
            "4": "blueoil",
            "5": "facility_services_b2b",
            "6": "warehouse_aburra_norte"
        }
        
        campaign_id = "tinkko_enterprise_offices" # default
        
        # First check full words, then check if the entire message is just a number
        is_just_number = clean_text.strip() in [str(i) for i in range(1, 7)]
        if is_just_number:
            campaign_id = campaign_map[clean_text.strip()]
        else:
            for kw, camp_id in campaign_map.items():
                # We skip single digits when checking substrings unless it's isolated
                if len(kw) == 1:
                    continue
                if kw in clean_text:
                    campaign_id = camp_id
                    break
                
        # 2. City
        cities = ["medellin", "bogota", "cali", "barranquilla", "cartagena"]
        city = "Medellin" # default
        for c in cities:
            if c in clean_text:
                city = c.capitalize()
                break
                
        # 3. Tier
        tier_match = re.search(r'tier\s*([1-3])', clean_text)
        tier = int(tier_match.group(1)) if tier_match else 1
        
        # 4. Limit (Volume)
        # Find all numbers
        numbers = re.findall(r'\b\d+\b', clean_text)
        limit = 10 # default
        for num in numbers:
            val = int(num)
            # If it's a valid campaign number and the message was just a number, limit is 10
            if is_just_number:
                break
            # Ignore the tier number
            if tier_match and num == tier_match.group(1):
                continue
            if val >= 5:
                limit = val
                break
                
        return {
            "campaign_id": campaign_id,
            "city": city,
            "limit": limit,
            "tier": tier
        }

    def handle_incoming_message(self, from_number: str, text: str) -> Dict[str, Any]:
        """
        Parses incoming WhatsApp user message and triggers appropriate order flow.
        """
        clean_text = text.strip().lower()

        if clean_text in ("hola", "menu", "start", "empezar", "hi"):
            return {
                "action": "send_menu",
                "to": from_number,
                "message": (
                    "👋 ¡Hola! Bienvenido al motor de Inteligencia B2B de *Michito*.\n"
                    "¿Qué tipo de empresas necesitas prospectar hoy?\n\n"
                    "1️⃣ Oficinas Corporativas / Coworking (Tinkko)\n"
                    "2️⃣ Logística & Envíos E-Commerce (Hebisend)\n"
                    "3️⃣ Desarrollo de Software & Apps (Chiketto)\n"
                    "4️⃣ Combustible & Lubricantes para Flotas (Blue Oil)\n"
                    "5️⃣ Aseo & Mantenimiento Corporativo (Facility Services)\n"
                    "6️⃣ Bodegas & Parques Industriales (Aburrá Norte)\n\n"
                    "O simplemente dime qué necesitas, ej: 'Quiero 25 prospectos de tinkko en medellin tier 2'"
                )
            }
            
        # Parse text
        parsed_params = self._parse_message(clean_text)
        
        # Prepare payload
        payload = {
            "client": {
                "name": "WhatsApp User",
                "email": "whatsapp@example.com",
                "phone": from_number,
                "channel": "whatsapp",
                "referral_partner": "direct"
            },
            "request": {
                "campaign_id": parsed_params["campaign_id"],
                "country": "CO",
                "city": parsed_params["city"],
                "limit": parsed_params["limit"],
                "tier": parsed_params["tier"]
            }
        }
        
        # Send to API
        try:
            response = requests.post(f"{self.api_base_url}/orders", json=payload, timeout=5.0)
            response.raise_for_status()
            data = response.json()
            order_id = data.get("order_id", "desconocida")
        except Exception as e:
            # Fallback or error
            order_id = "desconocida"
            
        return {
            "action": "reply",
            "to": from_number,
            "message": f"⚡ Estamos escaneando registros oficiales y validando buzones. Tu orden {order_id} está en proceso.",
            "order_id": order_id
        }

    def notify_awaiting_payment(self, to_number: str, order_id: str, teaser_summary: str, checkout_url: str) -> Dict[str, Any]:
        """
        Callback to be invoked when an order transitions to 'awaiting_payment'.
        Sends the sample teaser and checkout link.
        """
        message = (
            f"✅ ¡Tu orden {order_id} está lista!\n\n"
            f"📊 *Resumen de la muestra:*\n{teaser_summary}\n\n"
            f"Para desbloquear el lote completo, realiza tu pago seguro con Wompi aquí:\n{checkout_url}"
        )
        return {
            "action": "reply",
            "to": to_number,
            "message": message
        }
