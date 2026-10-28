from dataclasses import dataclass
from typing import Optional
from datetime import date

@dataclass
class LitigationRecord:
    id: str
    company_id: str
    case_number: str
    status: str
    filing_date: Optional[date] = None
    
    def __post_init__(self):
        if not self.id:
            raise ValueError("Litigation Record must have an ID.")
        if not self.company_id:
            raise ValueError("Litigation Record must belong to a company.")
        if not self.case_number or not str(self.case_number).strip():
            raise ValueError("Litigation Record must have a case number.")
        if not self.status or not str(self.status).strip():
            raise ValueError("Litigation Record must have a status.")
