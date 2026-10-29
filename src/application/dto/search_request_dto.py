from dataclasses import dataclass
from typing import Optional
from decimal import Decimal

@dataclass
class CompanyFilterDto:
    country_code: str
    min_revenue: Optional[Decimal] = None
    industry: Optional[str] = None
    city: Optional[str] = None

SearchRequestDto = CompanyFilterDto
