from abc import ABC, abstractmethod

class PaymentGatewayPort(ABC):
    @abstractmethod
    def generate_checkout_session(self, order_id: str, amount_in_cents: int, currency: str, redirect_url: str) -> str:
        """
        Generates a checkout session URL for the given order and amount.
        """
        pass

    @abstractmethod
    def verify_webhook_signature(self, event_data: dict, signature: str) -> bool:
        """
        Verifies the webhook signature from the payment gateway.
        """
        pass
