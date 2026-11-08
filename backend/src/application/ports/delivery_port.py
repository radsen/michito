from abc import ABC, abstractmethod
from typing import Dict, Any

class DeliveryPort(ABC):
    @abstractmethod
    def send_delivery(self, order: Dict[str, Any]) -> bool:
        """Sends the order deliverables to the buyer."""
        pass
