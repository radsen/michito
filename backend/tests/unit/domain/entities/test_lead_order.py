import pytest
from src.domain.entities.lead_order import LeadOrder
from src.domain.entities.company import Company
from src.domain.entities.decision_maker import DecisionMaker
from src.domain.entities.financial_report import FinancialReport
from src.domain.entities.litigation_record import LitigationRecord
from src.domain.value_objects.tax_id import TaxId
from src.domain.value_objects.email_address import EmailAddress
from src.domain.value_objects.confidence_score import ConfidenceScore

@pytest.fixture
def base_company():
    return Company(id="c1", tax_id=TaxId("900353939"), name="Acme")

def test_valid_lead_order(base_company):
    lead = LeadOrder(id="lo1", company=base_company)
    assert lead.id == "lo1"
    assert lead.company == base_company
    assert len(lead.decision_makers) == 0
    assert len(lead.financial_reports) == 0
    assert len(lead.litigation_records) == 0

def test_add_decision_maker(base_company):
    lead = LeadOrder(id="lo1", company=base_company)
    dm = DecisionMaker(id="dm1", name="John", email=EmailAddress("j@a.com"))
    lead.add_decision_maker(dm)
    assert len(lead.decision_makers) == 1
    assert lead.decision_makers[0] == dm

def test_add_financial_report(base_company):
    lead = LeadOrder(id="lo1", company=base_company)
    report = FinancialReport(id="fr1", company_id="c1", revenue=100, ebitda=10)
    lead.add_financial_report(report)
    assert len(lead.financial_reports) == 1
    
    report2 = FinancialReport(id="fr2", company_id="c2", revenue=100, ebitda=10)
    with pytest.raises(ValueError, match="Financial report must belong to the Lead's company."):
        lead.add_financial_report(report2)

def test_add_litigation_record(base_company):
    lead = LeadOrder(id="lo1", company=base_company)
    record = LitigationRecord(id="lr1", company_id="c1", case_number="c-1", status="Open")
    lead.add_litigation_record(record)
    assert len(lead.litigation_records) == 1
    
    record2 = LitigationRecord(id="lr2", company_id="c2", case_number="c-2", status="Open")
    with pytest.raises(ValueError, match="Litigation record must belong to the Lead's company."):
        lead.add_litigation_record(record2)

def test_invalid_lead_order(base_company):
    with pytest.raises(ValueError, match="Lead Order must have an ID."):
        LeadOrder(id="", company=base_company)
        
    with pytest.raises(ValueError, match="Lead Order must have a valid company."):
        LeadOrder(id="lo1", company=None)

def test_lead_order_with_score(base_company):
    score = ConfidenceScore(85)
    lead = LeadOrder(id="lo1", company=base_company, confidence_score=score)
    assert lead.confidence_score.value == 85
