import pytest
from decimal import Decimal
from src.domain.entities.financial_report import FinancialReport
from src.domain.value_objects.ebitda_margin import SolvencyTier

def test_valid_financial_report():
    report = FinancialReport(id="fr1", company_id="c1", revenue=1000000, ebitda=150000)
    
    assert report.id == "fr1"
    assert report.company_id == "c1"
    assert report.revenue == Decimal('1000000')
    assert report.ebitda == Decimal('150000')
    
    margin = report.ebitda_margin
    assert margin.value == Decimal('0.15')
    assert margin.tier == SolvencyTier.AA

def test_zero_revenue_margin():
    report = FinancialReport(id="fr1", company_id="c1", revenue=0, ebitda=0)
    assert report.ebitda_margin.value == Decimal(0)
    assert report.ebitda_margin.tier == SolvencyTier.DISTRESS

def test_invalid_financial_report():
    with pytest.raises(ValueError, match="Financial Report must have an ID."):
        FinancialReport(id="", company_id="c1", revenue=100, ebitda=10)
        
    with pytest.raises(ValueError, match="Financial Report must belong to a company."):
        FinancialReport(id="fr1", company_id="", revenue=100, ebitda=10)
        
    with pytest.raises(ValueError, match="Revenue and EBITDA must be numeric."):
        FinancialReport(id="fr1", company_id="c1", revenue="abc", ebitda=10)
