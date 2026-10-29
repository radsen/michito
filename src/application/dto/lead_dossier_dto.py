from dataclasses import dataclass
from decimal import Decimal
from typing import List

@dataclass
class LeadDossierDto:
    company_id: str
    company_name: str
    tax_id: str
    industry: str
    revenue: Decimal
    ebitda: Decimal
    ebitda_margin: Decimal
    litigation_count: int
    email_deliverability: str
    composite_score: float
