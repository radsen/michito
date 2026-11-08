import pytest
from decimal import Decimal
from src.domain.value_objects.ebitda_margin import EbitdaMargin, SolvencyTier
from src.domain.exceptions import InvalidEbitdaException

def test_ebitda_margin_tiers():
    assert EbitdaMargin(Decimal('0.25')).tier == SolvencyTier.AAA
    assert EbitdaMargin(Decimal('0.201')).tier == SolvencyTier.AAA
    
    assert EbitdaMargin(Decimal('0.20')).tier == SolvencyTier.AA
    assert EbitdaMargin(Decimal('0.08')).tier == SolvencyTier.AA
    assert EbitdaMargin(Decimal('0.15')).tier == SolvencyTier.AA
    
    assert EbitdaMargin(Decimal('0.079')).tier == SolvencyTier.A
    assert EbitdaMargin(Decimal('0.01')).tier == SolvencyTier.A
    
    assert EbitdaMargin(Decimal('0.009')).tier == SolvencyTier.DISTRESS
    assert EbitdaMargin(Decimal('0.0')).tier == SolvencyTier.DISTRESS
    assert EbitdaMargin(Decimal('-0.05')).tier == SolvencyTier.DISTRESS

def test_ebitda_margin_conversion():
    margin = EbitdaMargin("0.15")
    assert margin.tier == SolvencyTier.AA
    
    margin2 = EbitdaMargin(0.05)
    assert margin2.tier == SolvencyTier.A

def test_invalid_ebitda_margin():
    with pytest.raises(InvalidEbitdaException, match="EBITDA margin must be a Decimal or convertible to Decimal."):
        EbitdaMargin("invalid")
