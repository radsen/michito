"""
Michito WhatsApp Conversational Bot Integration Service.
Handles incoming WhatsApp Webhooks (Twilio / Meta Cloud API), initiates the prospecting job,
sends the processing notification, delivers the teaser preview with Wompi payment link,
and dispatches deliverables upon payment.
"""

from typing import Dict, Any, Optional
import os


class WhatsAppBotService:
    def __init__(self, api_token: Optional[str] = None):
        self.api_token = api_token or os.environ.get("WHATSAPP_API_TOKEN", "")

    def handle_incoming_message(self, from_number: str, text: str) -> Dict[str, Any]:
        """
        Parses incoming WhatsApp user message and triggers appropriate order flow.
        """
        clean_text = text.strip().lower()

        if clean_text in ("hola", "menu", "start", "empezar"):
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
                    "Responde con el número de tu opción."
                )
            }

        # Handle campaign selection
        campaign_map = {
            "1": "tinkko_enterprise_offices",
            "2": "hebi",
            "3": "chiketto",
            "4": "blueoil",
            "5": "facility_services_b2b",
            "6": "warehouse_aburra_norte",
        }

        if clean_text in campaign_map:
            campaign_id = campaign_map[clean_text]
            return {
                "action": "queue_order",
                "campaign_id": campaign_id,
                "to": from_number,
                "notification": (
                    "⚡ *Recibido.* Hemos puesto a trabajar nuestros bots de búsqueda en SECOP II y registros mercantiles.\n\n"
                    "🔍 Validando sitios web activos, teléfonos de representantes y servidores de correo corporativo...\n"
                    "Te avisaremos en *~30 segundos* con una muestra de tus cuentas listas."
                )
            }

        return {
            "action": "reply",
            "to": from_number,
            "message": "Escribe 'hola' para ver las campañas disponibles de generación de leads."
        }

