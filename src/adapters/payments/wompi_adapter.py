import hashlib
from src.application.ports.payment_gateway_port import PaymentGatewayPort

class WompiPaymentGatewayAdapter(PaymentGatewayPort):
    def __init__(self, public_key: str, webhook_secret: str, api_url: str = "https://checkout.wompi.co/p/"):
        self.public_key = public_key
        self.webhook_secret = webhook_secret
        self.api_url = api_url

    def generate_checkout_session(self, order_id: str, amount_in_cents: int, currency: str, redirect_url: str) -> str:
        # Generate Wompi checkout URL
        # Format typically: https://checkout.wompi.co/p/?public-key=...&currency=...&amount-in-cents=...&reference=...&redirect-url=...
        url = (
            f"{self.api_url}?public-key={self.public_key}"
            f"&currency={currency}"
            f"&amount-in-cents={amount_in_cents}"
            f"&reference={order_id}"
            f"&redirect-url={redirect_url}"
        )
        return url

    def verify_webhook_signature(self, event_data: dict, signature: str) -> bool:
        # Wompi webhook signature validation
        # According to documentation, the signature is often generated as:
        # SHA256(transaction.id + transaction.status + transaction.amount_in_cents + timestamp + secret)
        # We will extract these from event_data
        try:
            data = event_data.get("data", {})
            transaction = data.get("transaction", {})
            
            tx_id = transaction.get("id", "")
            status = transaction.get("status", "")
            amount = transaction.get("amount_in_cents", "")
            timestamp = event_data.get("timestamp", "")
            
            concatenated = f"{tx_id}{status}{amount}{timestamp}{self.webhook_secret}"
            expected_signature = hashlib.sha256(concatenated.encode('utf-8')).hexdigest()
            return expected_signature == signature
        except Exception:
            return False
