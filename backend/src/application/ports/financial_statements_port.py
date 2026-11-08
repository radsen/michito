from abc import ABC, abstractmethod
from typing import Dict, Any

class FinancialStatementsPort(ABC):
    @abstractmethod
    def fetch_raw_financials(self, tax_id: str) -> Dict[str, Any]:
        """
        Fetches raw financials which must include:
        - operating_revenue
        - cost_of_sales
        - operating_expenses
        - depreciation
        - amortization
        """
        pass
