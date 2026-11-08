import pytest
from decimal import Decimal
from src.domain.value_objects.confidence_score import ConfidenceScore
from src.domain.exceptions import InvalidConfidenceScoreException

def test_valid_confidence_score():
    score1 = ConfidenceScore(0)
    assert score1.value == Decimal('0')
    
    score2 = ConfidenceScore("55.5")
    assert score2.value == Decimal('55.5')
    
    score3 = ConfidenceScore(100)
    assert score3.value == Decimal('100')

def test_invalid_confidence_score_type():
    with pytest.raises(InvalidConfidenceScoreException, match="Confidence score must be numeric."):
        ConfidenceScore("invalid")

def test_invalid_confidence_score_range():
    with pytest.raises(InvalidConfidenceScoreException, match="Confidence score must be between 0 and 100."):
        ConfidenceScore(-1)
        
    with pytest.raises(InvalidConfidenceScoreException, match="Confidence score must be between 0 and 100."):
        ConfidenceScore(100.1)
