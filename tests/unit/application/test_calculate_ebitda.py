import pytest
from decimal import Decimal
from src.application.use_cases.calculate_ebitda import CalculateCompanyEbitdaUseCase
from src.domain.value_objects.ebitda_margin import SolvencyTier

def test_calculate_ebitda_success():
    use_case = CalculateCompanyEbitdaUseCase()
    raw_financials = {
        'operating_revenue': 10000,
        'cost_of_sales': 4000,
        'operating_expenses': 2000,
        'depreciation': 500,
        'amortization': 500
    }
    
    result = use_case.execute(raw_financials)
    
    # EBIT = 10000 - 4000 - 2000 = 4000
    assert result['ebit'] == Decimal('4000')
    
    # EBITDA = 4000 + 500 + 500 = 5000
    assert result['ebitda'] == Decimal('5000')
    
    # Margin = 5000 / 10000 = 0.5 (50%)
    assert result['ebitda_margin'].value == Decimal('0.5')
    assert result['ebitda_margin'].tier == SolvencyTier.AAA

def test_calculate_ebitda_zero_revenue():
    use_case = CalculateCompanyEbitdaUseCase()
    raw_financials = {
        'operating_revenue': 0,
        'cost_of_sales': 1000,
        'operating_expenses': 500,
        'depreciation': 0,
        'amortization': 0
    }
    
    result = use_case.execute(raw_financials)
    assert result['ebit'] == Decimal('-1500')
    assert result['ebitda'] == Decimal('-1500')
    assert result['ebitda_margin'].value == Decimal('0')
    assert result['ebitda_margin'].tier == SolvencyTier.DISTRESS

def test_calculate_ebitda_missing_fields():
    use_case = CalculateCompanyEbitdaUseCase()
    raw_financials = {
        'operating_revenue': 5000
    }
    
    result = use_case.execute(raw_financials)
    assert result['ebit'] == Decimal('5000')
    assert result['ebitda'] == Decimal('5000')
    assert result['ebitda_margin'].value == Decimal('1')
