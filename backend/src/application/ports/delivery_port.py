from abc import ABC, abstractmethod
from typing import Dict, Any

class DeliveryPort(ABC):
    @abstractmethod
    def send_delivery(self, order: Dict[str, Any]) -> bool:
        """Sends the order deliverables to the buyer."""
        pass

    def send_ready_for_review_notification(self, order: Dict[str, Any]) -> bool:
        """Sends review notification (teaser + quote link) when batch auditing finishes."""
        return True
