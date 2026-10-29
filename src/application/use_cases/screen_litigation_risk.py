from typing import List
from src.application.ports.litigation_port import LitigationScreeningPort
from src.domain.entities.litigation_record import LitigationRecord

class ScreenLitigationRiskUseCase:
    def __init__(self, adapters: List[LitigationScreeningPort]):
        self.adapters = adapters

    def execute(self, tax_id: str) -> List[LitigationRecord]:
        aggregated_records = []
        for adapter in self.adapters:
            records = adapter.screen_litigation(tax_id)
            if records:
                aggregated_records.extend(records)
        return aggregated_records
