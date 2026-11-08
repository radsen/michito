from typing import Dict
from src.application.ports.lead_order_repository_port import LeadOrderRepositoryPort
from src.domain.entities.lead_order import LeadOrder

class MemoryRepositoryAdapter(LeadOrderRepositoryPort):
    def __init__(self):
        self._storage: Dict[str, LeadOrder] = {}

    def save(self, lead_order: LeadOrder) -> None:
        self._storage[lead_order.id] = lead_order

    def get_by_id(self, order_id: str) -> LeadOrder:
        if order_id not in self._storage:
            raise KeyError(f"LeadOrder {order_id} not found")
        return self._storage[order_id]
