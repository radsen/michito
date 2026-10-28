import pytest
from src.domain.entities.company import Company
from src.domain.value_objects.tax_id import TaxId

def test_valid_company():
    tax_id = TaxId("900353939-1")
    company = Company(id="c1", tax_id=tax_id, name="Acme Corp", industry="Tech")
    
    assert company.id == "c1"
    assert company.tax_id == tax_id
    assert company.name == "Acme Corp"
    assert company.industry == "Tech"

def test_invalid_company():
    tax_id = TaxId("900353939-1")
    
    with pytest.raises(ValueError, match="Company must have an ID."):
        Company(id="", tax_id=tax_id, name="Acme Corp")
        
    with pytest.raises(ValueError, match="Company must have a name."):
        Company(id="c1", tax_id=tax_id, name="   ")
