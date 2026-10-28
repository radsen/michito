import pytest
from src.domain.entities.decision_maker import DecisionMaker
from src.domain.value_objects.email_address import EmailAddress

def test_valid_decision_maker():
    email = EmailAddress("ceo@acme.com")
    dm = DecisionMaker(id="dm1", name="John Doe", email=email, role="CEO")
    
    assert dm.id == "dm1"
    assert dm.name == "John Doe"
    assert dm.email == email
    assert dm.role == "CEO"

def test_invalid_decision_maker():
    email = EmailAddress("ceo@acme.com")
    
    with pytest.raises(ValueError, match="Decision Maker must have an ID."):
        DecisionMaker(id="", name="John Doe", email=email)
        
    with pytest.raises(ValueError, match="Decision Maker must have a name."):
        DecisionMaker(id="dm1", name="", email=email)
