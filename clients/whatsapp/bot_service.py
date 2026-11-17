import re
import os
import requests
from typing import Dict, Any, Optional

try:
    from src.application.services.brief_parser_service import BriefParserService
except ImportError:
    try:
        from backend.src.application.services.brief_parser_service import BriefParserService
    except ImportError:
        BriefParserService = None


class WhatsAppBotService:
    def __init__(
        self,
        api_token: Optional[str] = None,
        api_base_url: Optional[str] = None,
        brief_parser: Optional[Any] = None,
    ):
        self.api_token = api_token or os.environ.get("WHATSAPP_API_TOKEN", "")
        self.api_base_url = api_base_url or os.environ.get("API_BASE_URL", "http://localhost:8000/api/v1")
        if brief_parser is not None:
            self.brief_parser = brief_parser
        elif BriefParserService is not None:
            self.brief_parser = BriefParserService()
        else:
            self.brief_parser = None

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
        
        campaign_id = "tinkko_enterprise_offices"  # default
        
        # First check full words, then check if the entire message is just a number
        is_just_number = clean_text.strip() in [str(i) for i in range(1, 7)]
        if is_just_number:
            campaign_id = campaign_map[clean_text.strip()]
        else:
            for kw, camp_id in campaign_map.items():
                if len(kw) == 1:
                    continue
                if kw in clean_text:
                    campaign_id = camp_id
                    break
                
        # 2. City
        cities = ["medellin", "bogota", "cali", "barranquilla", "cartagena", "santo domingo", "quito"]
        city = "Medellin"  # default
        for c in cities:
            if c in clean_text:
                city = c.capitalize()
                break
                
        # 3. Tier
        tier_match = re.search(r'tier\s*([1-3])', clean_text)
        tier = int(tier_match.group(1)) if tier_match else 1
        if tier == 3 and city.lower() in ("santo domingo", "quito"):
            tier = 2
        
        # 4. Limit (Volume)
        numbers = re.findall(r'\b\d+\b', clean_text)
        limit = 10  # default
        for num in numbers:
            val = int(num)
            if is_just_number:
                break
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
        Supports both legacy presets and intelligent universal briefing (Sales vs Procurement).
        """
        clean_text = text.strip().lower()

        # 1. Greetings and Menu
        if clean_text in ("hola", "menu", "start", "empezar", "hi", "ayuda", "help"):
            return {
                "action": "send_menu",
                "to": from_number,
                "message": (
                    "¡Hola! Bienvenido al motor de Inteligencia B2B de *Michito* 🇨🇴 🇩🇴 🇪🇨.\n\n"
                    "🎯 *¿Cómo deseas operar hoy?*\n\n"
                    "1️⃣ *Quiero Vender (Prospección Outbound)*\n"
                    "   _Ejemplo: 'Vendo software de facturación para colegios privados en Medellín y Quito'_\n\n"
                    "2️⃣ *Quiero Comprar / Cotizar (Auto-RFQ)*\n"
                    "   _Ejemplo: 'Necesito comprar muebles y escritorios para remodelar oficinas en Bogotá'_\n\n"
                    "📦 *O elige una de nuestras campañas preconfiguradas:*\n"
                    "1. Oficinas Corporativas (Tinkko)\n"
                    "2. Logística & Envíos (Hebi)\n"
                    "3. Software & ERP DIAN (Chiketto)\n"
                    "4. Combustible para Flotas (Blue Oil)\n"
                    "5. Aseo & Mantenimiento (Facility Services)\n"
                    "6. Bodegas Industriales (Aburrá Norte)\n\n"
                    "También puedes escribir: *'estado ord_20261113_...' para consultar tu pedido.*"
                )
            }

        # 2. Check Order Status
        status_match = re.search(r'(?:estado|status|consultar)\s+(ord_\w+)', clean_text)
        if status_match:
            order_id = status_match.group(1)
            try:
                resp = requests.get(f"{self.api_base_url}/orders/{order_id}", timeout=5.0)
                if resp.status_code == 200:
                    order_data = resp.json().get("order", {})
                    state = order_data.get("status", "en_proceso")
                    leads = len(order_data.get("leads", []))
                    tracking_url = f"http://localhost:3000/rastrear?order_id={order_id}"
                    return {
                        "action": "reply",
                        "to": from_number,
                        "message": (
                            f"📋 *Estado de tu Orden {order_id}*\n"
                            f"• Estado: *{state.upper()}*\n"
                            f"• Prospectos Validados: *{leads}*\n"
                            f"• Ver Detalles y Descargas: {tracking_url}"
                        ),
                        "order_id": order_id
                    }
            except Exception as e:
                pass

        # 3. Determine if using legacy presets or intelligent BriefParserService
        preset_keywords = ["tinkko", "hebi", "chiketto", "blueoil", "facility", "aburra", "warehouse"]
        is_preset = any(kw in clean_text for kw in preset_keywords) or clean_text.strip() in [str(i) for i in range(1, 7)]

        if is_preset or not self.brief_parser:
            parsed_params = self._parse_message(clean_text)
            payload = {
                "client": {
                    "name": "WhatsApp User",
                    "email": f"wa_{from_number.replace('+', '')}@whatsapp.michito.co",
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
        else:
            # Intelligent Universal Briefing
            parsed_brief = self.brief_parser.parse_brief(text)
            primary_location = parsed_brief["locations"][0] if parsed_brief.get("locations") else {"city": "Medellín", "country": "CO"}
            
            payload = {
                "client": {
                    "name": "WhatsApp Business User",
                    "email": f"wa_{from_number.replace('+', '')}@whatsapp.michito.co",
                    "phone": from_number,
                    "channel": "whatsapp",
                    "referral_partner": "direct"
                },
                "request": {
                    "campaign_id": "universal_prospecting",
                    "country": primary_location.get("country", "CO"),
                    "city": primary_location.get("city", "Medellín"),
                    "limit": parsed_brief.get("limit", 25),
                    "tier": parsed_brief.get("tier", 2),
                    "sector": parsed_brief.get("sectors", ["general"])[0] if parsed_brief.get("sectors") else "general",
                    "offer_description": text.strip(),
                    "target_roles": parsed_brief.get("roles"),
                    "target_ciiu_codes": parsed_brief.get("ciiu_codes"),
                    "location_allocations": parsed_brief.get("locations"),
                    "directionality": parsed_brief.get("directionality", "vendor_to_clients"),
                    "rfq_specifications": parsed_brief.get("rfq_specifications"),
                    "keywords_include": parsed_brief.get("keywords_include"),
                    "keywords_exclude": parsed_brief.get("keywords_exclude")
                }
            }

        # Send to API
        try:
            response = requests.post(f"{self.api_base_url}/orders", json=payload, timeout=5.0)
            response.raise_for_status()
            data = response.json()
            order_id = data.get("order_id", "desconocida")
        except Exception as e:
            order_id = "desconocida"

        mode_desc = "📋 *Solicitud de Cotización (Auto-RFQ)*" if payload["request"].get("directionality") == "client_to_vendors" else "🎯 *Prospección Comercial B2B*"

        notice_line = f"\n\n_{parsed_brief['tier_notice']}_" if not is_preset and parsed_brief.get("tier_notice") else ""

        return {
            "action": "reply",
            "to": from_number,
            "message": (
                f"{mode_desc}\n"
                f"⚡ Estamos escaneando registros oficiales y validando buzones. Tu orden {order_id} está en proceso.{notice_line}\n"
                f"Rastrea tu pedido en vivo: http://localhost:3000/rastrear?order_id={order_id}"
            ),
            "order_id": order_id
        }

    def notify_awaiting_payment(self, to_number: str, order_id: str, teaser_summary: str, checkout_url: str) -> Dict[str, Any]:
        """
        Callback to be invoked when an order transitions to 'awaiting_payment'.
        Sends the sample teaser and checkout link.
        """
        message = (
            f"¡Tu orden {order_id} está lista!\n\n"
            f"*Resumen de la muestra:*\n{teaser_summary}\n\n"
            f"Para desbloquear el lote completo, realiza tu pago seguro con Wompi aquí:\n{checkout_url}"
        )
        return {
            "action": "reply",
            "to": to_number,
            "message": message
        }
