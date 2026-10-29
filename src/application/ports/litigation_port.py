from abc import ABC, abstractmethod
from typing import List
from src.domain.entities.litigation_record import LitigationRecord

class LitigationScreeningPort(ABC):
    @abstractmethod
    def screen_litigation(self, tax_id: str) -> List[LitigationRecord]:
        """
        Fetches judicial and fiscal background for a given tax ID.
        """
        pass
