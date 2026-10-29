from abc import ABC, abstractmethod
from decimal import Decimal

class PaymentGatewayPort(ABC):
    @abstractmethod
    def charge(self, amount: Decimal, currency: str, token: str) -> bool:
        """
        Handles charges via a payment gateway.
        Returns True if successful, False otherwise.
        """
        pass
