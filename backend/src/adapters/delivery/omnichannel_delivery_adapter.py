import logging
from typing import Dict, Any
from src.application.ports.delivery_port import DeliveryPort

logger = logging.getLogger(__name__)

class OmnichannelDeliveryAdapter(DeliveryPort):
    def send_delivery(self, order: Dict[str, Any]) -> bool:
        """
        Simulates omnichannel delivery (Email and WhatsApp).
        Extracts deliverable URLs or paths from the order and logs them.
        """
        client_data = order.get("client", {})
        buyer_email = client_data.get("email") or order.get("customer_email", "unknown@example.com")
        buyer_phone = client_data.get("phone") or order.get("customer_phone", "unknown")
        
        csv_url = order.get("csv_path", "")
        if not csv_url and "delivery" in order:
            csv_url = order["delivery"].get("csv_download_url", "") or order["delivery"].get("csv_path", "")
            
        md_url = order.get("dossier_path", "")
        if not md_url and "delivery" in order:
            md_url = order["delivery"].get("dossier_download_url", "") or order["delivery"].get("dossier_path", "")
            
        if not csv_url and not md_url:
            # Fallback if no specific paths exist, assume they are somewhere else or just log placeholder
            pass
            
        whatsapp_message = (
            f"[WhatsApp] Sending to {buyer_phone}: \"Payment confirmed! "
            f"Download your leads CSV: {csv_url} and Dossier: {md_url}\""
        )
        
        email_message = (
            f"[Email] Sending to {buyer_email}: \"Payment confirmed! "
            f"Download your leads CSV: {csv_url} and Dossier: {md_url}\""
        )
        
        logger.info(whatsapp_message)
        logger.info(email_message)
        
        return True
