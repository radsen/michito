from abc import ABC, abstractmethod
from src.domain.entities.lead_order import LeadOrder

class LeadOrderRepositoryPort(ABC):
    @abstractmethod
    def save(self, lead_order: LeadOrder) -> None:
        """
        Persists a lead order.
        """
        pass
        
    @abstractmethod
    def get_by_id(self, order_id: str) -> LeadOrder:
        """
        Retrieves a lead order by ID.
        """
        pass
