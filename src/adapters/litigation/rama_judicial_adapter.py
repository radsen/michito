import uuid
from datetime import date
from typing import List
from src.application.ports.litigation_port import LitigationScreeningPort
from src.domain.entities.litigation_record import LitigationRecord

class RamaJudicialAdapter(LitigationScreeningPort):
    def screen_litigation(self, tax_id: str) -> List[LitigationRecord]:
        records = []
        if tax_id == "900123456":
            records.append(
                LitigationRecord(
                    id=str(uuid.uuid4()),
                    company_id=tax_id,
                    case_number="RJ-2023-0001",
                    status="Proceso Ejecutivo de Cobro",
                    filing_date=date.today()
                )
            )
        elif tax_id == "900654321":
            records.append(
                LitigationRecord(
                    id=str(uuid.uuid4()),
                    company_id=tax_id,
                    case_number="RJ-2022-0042",
                    status="Proceso Laboral Ordinario",
                    filing_date=date.today()
                )
            )
        elif tax_id == "900111222":
            records.append(
                LitigationRecord(
                    id=str(uuid.uuid4()),
                    company_id=tax_id,
                    case_number="RJ-2021-0010",
                    status="Ley 1116 Insolvency",
                    filing_date=date.today()
                )
            )
        
        return records
