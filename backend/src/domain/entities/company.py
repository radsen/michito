from dataclasses import dataclass
from typing import Optional
from src.domain.value_objects.tax_id import TaxId

@dataclass
class Company:
    id: str
    tax_id: TaxId
    name: str
    industry: Optional[str] = None
    
    def __post_init__(self):
        if not self.id:
            raise ValueError("Company must have an ID.")
        if not self.name or not str(self.name).strip():
            raise ValueError("Company must have a name.")
