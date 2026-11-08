import pytest
from unittest.mock import Mock
from decimal import Decimal
from src.application.use_cases.search_companies import SearchQualifiedCompaniesUseCase
from src.application.use_cases.calculate_ebitda import CalculateCompanyEbitdaUseCase
from src.application.dto.search_request_dto import CompanyFilterDto
from src.domain.entities.company import Company
from src.domain.value_objects.tax_id import TaxId
from src.domain.entities.litigation_record import LitigationRecord

def test_search_companies_success():
    # Setup Mocks
    mock_corporate_registry = Mock()
    mock_provider = Mock()
    mock_corporate_registry.get_provider.return_value = mock_provider
    
    # Mock Companies
    company1 = Company(id="c1", tax_id=TaxId("123456789"), name="Test Co", industry="Tech")
    company2 = Company(id="c2", tax_id=TaxId("987654321"), name="Poor Co", industry="Retail")
    mock_provider.fetch_companies.return_value = [company1, company2]
    
    mock_financial_statements = Mock()
    def fetch_raw_financials(tax_id):
        if "123456789" in tax_id:
            return {
                'operating_revenue': 10_000_000_000,
                'cost_of_sales': 5_000_000_000,
                'operating_expenses': 2_000_000_000,
                'depreciation': 0,
                'amortization': 0
            } # EBITDA = 3,000,000,000, margin = 30% (>15% => 100)
        else:
            return {
                'operating_revenue': 1_000_000_000,
                'cost_of_sales': 1_000_000_000,
                'operating_expenses': 1_000_000_000,
                'depreciation': 0,
                'amortization': 0
            } # EBITDA = -1B, margin < 0 => 0
    mock_financial_statements.fetch_raw_financials.side_effect = fetch_raw_financials
    
    mock_litigation_screening = Mock()
    def screen_litigation(tax_id):
        if "123456789" in tax_id:
            return [] # 0 lawsuits => 100
        else:
            return [LitigationRecord(id="l1", company_id="c2", case_number="case1", status="insolvency")] # => 0
    mock_litigation_screening.screen_litigation.side_effect = screen_litigation
    
    mock_mailbox_verifier = Mock()
    def verify_email(email):
        if "c1" in email:
            return 'valid' # => 100
        else:
            return 'invalid' # => 0
    mock_mailbox_verifier.verify_email.side_effect = verify_email
    
    ebitda_calculator = CalculateCompanyEbitdaUseCase()
    
    use_case = SearchQualifiedCompaniesUseCase(
        corporate_registry=mock_corporate_registry,
        financial_statements=mock_financial_statements,
        litigation_screening=mock_litigation_screening,
        mailbox_verifier=mock_mailbox_verifier,
        ebitda_calculator=ebitda_calculator
    )
    
    filter_dto = CompanyFilterDto(country_code="CO", min_revenue=Decimal("1000"))
    results = use_case.execute(filter_dto)
    
    assert len(results) == 2
    # Company 1 should be first because it has higher score
    assert results[0].company_id == "c1"
    
    # Check Company 1 score
    # Revenue = 10B -> 100 * 0.25 = 25
    # EBITDA margin = 30% -> 100 * 0.30 = 30
    # Litigation = 0 -> 100 * 0.25 = 25
    # Mailbox = valid -> 100 * 0.20 = 20
    # Total = 100
    assert results[0].composite_score == 100.0
    
    # Check Company 2 score
    # Revenue = 1B -> 10 * 0.25 = 2.5
    # EBITDA margin < 0 -> 0
    # Litigation = insolvency -> 0
    # Mailbox = invalid -> 0
    # Total = 2.5
    assert results[1].composite_score == 2.5
