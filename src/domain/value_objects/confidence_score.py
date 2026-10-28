from dataclasses import dataclass
from decimal import Decimal
from src.domain.exceptions import InvalidConfidenceScoreException

@dataclass(frozen=True)
class ConfidenceScore:
    value: Decimal

    def __post_init__(self):
        try:
            val = Decimal(str(self.value))
        except Exception:
            raise InvalidConfidenceScoreException("Confidence score must be numeric.")
            
        if val < 0 or val > 100:
            raise InvalidConfidenceScoreException("Confidence score must be between 0 and 100.")
            
        object.__setattr__(self, 'value', val)
