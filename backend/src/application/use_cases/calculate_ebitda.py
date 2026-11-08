from decimal import Decimal
from typing import Dict, Any
from src.domain.value_objects.ebitda_margin import EbitdaMargin

class CalculateCompanyEbitdaUseCase:
    def execute(self, raw_financials: Dict[str, Any]) -> Dict[str, Any]:
        """
        raw_financials must contain:
        - operating_revenue
        - cost_of_sales
        - operating_expenses
        - depreciation
        - amortization
        """
        operating_revenue = Decimal(str(raw_financials.get('operating_revenue', 0)))
        cost_of_sales = Decimal(str(raw_financials.get('cost_of_sales', 0)))
        operating_expenses = Decimal(str(raw_financials.get('operating_expenses', 0)))
        depreciation = Decimal(str(raw_financials.get('depreciation', 0)))
        amortization = Decimal(str(raw_financials.get('amortization', 0)))

        ebit = operating_revenue - cost_of_sales - operating_expenses
        ebitda = ebit + depreciation + amortization

        if operating_revenue != 0:
            ebitda_margin = EbitdaMargin(ebitda / operating_revenue)
        else:
            ebitda_margin = EbitdaMargin(Decimal(0))

        return {
            "ebit": ebit,
            "ebitda": ebitda,
            "ebitda_margin": ebitda_margin
        }
