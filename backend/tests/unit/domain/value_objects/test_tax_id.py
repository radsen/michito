import pytest
from src.domain.value_objects.tax_id import TaxId
from src.domain.exceptions import InvalidTaxIdException

def test_valid_tax_id_with_dash():
    tax_id = TaxId("900353939-1")
    assert tax_id.value == "900353939-1"
    
    tax_id2 = TaxId("800197268-4")
    assert tax_id2.value == "800197268-4"

def test_valid_tax_id_without_dash():
    tax_id = TaxId("900353939")
    assert tax_id.value == "900353939-1"
    
    tax_id2 = TaxId("800197268")
    assert tax_id2.value == "800197268-4"

def test_invalid_tax_id_format():
    with pytest.raises(InvalidTaxIdException, match="Tax ID cannot be empty."):
        TaxId("")

    with pytest.raises(InvalidTaxIdException, match="Invalid Tax ID format."):
        TaxId("900-353-939")
        
    with pytest.raises(InvalidTaxIdException, match="Tax ID must contain digits."):
        TaxId("ABCDEFGH-1")
        
    with pytest.raises(InvalidTaxIdException, match="Invalid check digit format."):
        TaxId("900353939-A")
        
    with pytest.raises(InvalidTaxIdException, match="Invalid check digit format."):
        TaxId("900353939-12")

def test_invalid_check_digit():
    with pytest.raises(InvalidTaxIdException, match="Invalid check digit. Expected 1, got 2."):
        TaxId("900353939-2")

def test_str_representation():
    tax_id = TaxId("800197268")
    assert str(tax_id) == "800197268-4"
