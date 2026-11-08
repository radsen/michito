from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from src.domain.exceptions import InvalidEbitdaException

class SolvencyTier(Enum):
    AAA = "AAA"
    AA = "AA"
    A = "A"
    DISTRESS = "Distress"

@dataclass(frozen=True)
class EbitdaMargin:
    value: Decimal

    def __post_init__(self):
        if not isinstance(self.value, Decimal):
            try:
                object.__setattr__(self, 'value', Decimal(str(self.value)))
            except Exception:
                raise InvalidEbitdaException("EBITDA margin must be a Decimal or convertible to Decimal.")

    @property
    def tier(self) -> SolvencyTier:
        margin_percent = self.value * 100
        if margin_percent > 20:
            return SolvencyTier.AAA
        elif margin_percent >= 8:
            return SolvencyTier.AA
        elif margin_percent >= 1:
            return SolvencyTier.A
        else:
            return SolvencyTier.DISTRESS
