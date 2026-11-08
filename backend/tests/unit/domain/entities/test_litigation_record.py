import pytest
from datetime import date
from src.domain.entities.litigation_record import LitigationRecord

def test_valid_litigation_record():
    record = LitigationRecord(id="lr1", company_id="c1", case_number="CASE-123", status="Active", filing_date=date(2023, 1, 1))
    
    assert record.id == "lr1"
    assert record.company_id == "c1"
    assert record.case_number == "CASE-123"
    assert record.status == "Active"
    assert record.filing_date == date(2023, 1, 1)

def test_invalid_litigation_record():
    with pytest.raises(ValueError, match="Litigation Record must have an ID."):
        LitigationRecord(id="", company_id="c1", case_number="C-1", status="Active")
        
    with pytest.raises(ValueError, match="Litigation Record must belong to a company."):
        LitigationRecord(id="lr1", company_id="", case_number="C-1", status="Active")
        
    with pytest.raises(ValueError, match="Litigation Record must have a case number."):
        LitigationRecord(id="lr1", company_id="c1", case_number="", status="Active")
        
    with pytest.raises(ValueError, match="Litigation Record must have a status."):
        LitigationRecord(id="lr1", company_id="c1", case_number="C-1", status="")
