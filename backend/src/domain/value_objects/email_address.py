from dataclasses import dataclass
import re
from src.domain.exceptions import InvalidEmailException

@dataclass(frozen=True)
class EmailAddress:
    value: str

    def __post_init__(self):
        cleaned_value = self.value.strip()
        if not cleaned_value:
            raise InvalidEmailException("Email cannot be empty.")
            
        # Basic email regex
        pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        if not re.match(pattern, cleaned_value):
            raise InvalidEmailException(f"Invalid email format: {cleaned_value}")
            
        object.__setattr__(self, 'value', cleaned_value.lower())

    def __str__(self):
        return self.value
