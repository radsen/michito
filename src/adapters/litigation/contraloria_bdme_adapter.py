import uuid
from datetime import date
from typing import List
from src.application.ports.litigation_port import LitigationScreeningPort
from src.domain.entities.litigation_record import LitigationRecord

class ContraloriaBdmeAdapter(LitigationScreeningPort):
    def screen_litigation(self, tax_id: str) -> List[LitigationRecord]:
        records = []
        if tax_id == "800987654":
            records.append(
                LitigationRecord(
                    id=str(uuid.uuid4()),
                    company_id=tax_id,
                    case_number="CB-2023-0099",
                    status="Fiscal Debt Sanction",
                    filing_date=date.today()
                )
            )
        elif tax_id == "900123456":
            records.append(
                LitigationRecord(
                    id=str(uuid.uuid4()),
                    company_id=tax_id,
                    case_number="CB-2021-0100",
                    status="Fiscal Debt Sanction",
                    filing_date=date.today()
                )
            )
        
        return records
