import pytest
from src.domain.value_objects.email_address import EmailAddress
from src.domain.exceptions import InvalidEmailException

def test_valid_email():
    email = EmailAddress("test@example.com")
    assert email.value == "test@example.com"
    
    email2 = EmailAddress("  TEST@Example.com ")
    assert email2.value == "test@example.com"

def test_invalid_email():
    with pytest.raises(InvalidEmailException, match="Email cannot be empty."):
        EmailAddress("")
        
    with pytest.raises(InvalidEmailException, match="Invalid email format: invalid-email"):
        EmailAddress("invalid-email")
        
    with pytest.raises(InvalidEmailException, match="Invalid email format: test@.com"):
        EmailAddress("test@.com")

def test_str_representation():
    email = EmailAddress("Test@Example.com")
    assert str(email) == "test@example.com"
