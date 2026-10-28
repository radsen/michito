from dataclasses import dataclass
from decimal import Decimal
from src.domain.value_objects.ebitda_margin import EbitdaMargin

@dataclass
class FinancialReport:
    id: str
    company_id: str
    revenue: Decimal
    ebitda: Decimal
    
    def __post_init__(self):
        if not self.id:
            raise ValueError("Financial Report must have an ID.")
        if not self.company_id:
            raise ValueError("Financial Report must belong to a company.")
            
        try:
            object.__setattr__(self, 'revenue', Decimal(str(self.revenue)))
            object.__setattr__(self, 'ebitda', Decimal(str(self.ebitda)))
        except Exception:
            raise ValueError("Revenue and EBITDA must be numeric.")
            
    @property
    def ebitda_margin(self) -> EbitdaMargin:
        if self.revenue == 0:
            return EbitdaMargin(Decimal(0))
        return EbitdaMargin(self.ebitda / self.revenue)
