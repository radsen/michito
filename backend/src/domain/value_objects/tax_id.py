from dataclasses import dataclass
from src.domain.exceptions import InvalidTaxIdException

@dataclass(frozen=True)
class TaxId:
    value: str

    def __post_init__(self):
        cleaned_value = self.value.strip()
        if not cleaned_value:
            raise InvalidTaxIdException("Tax ID cannot be empty.")
        
        parts = cleaned_value.split('-')
        if len(parts) > 2:
            raise InvalidTaxIdException("Invalid Tax ID format.")
            
        nit_str = parts[0]
        if not nit_str.isdigit():
            raise InvalidTaxIdException("Tax ID must contain digits.")
            
        if len(parts) == 2:
            check_digit = parts[1]
            if not check_digit.isdigit() or len(check_digit) != 1:
                raise InvalidTaxIdException("Invalid check digit format.")
            calculated = self._calculate_check_digit(nit_str)
            if int(check_digit) != calculated:
                raise InvalidTaxIdException(f"Invalid check digit. Expected {calculated}, got {check_digit}.")
            # Store formatted with dash
            object.__setattr__(self, 'value', f"{nit_str}-{check_digit}")
        else:
            # If no check digit is provided, calculate and append it
            calculated = self._calculate_check_digit(nit_str)
            object.__setattr__(self, 'value', f"{nit_str}-{calculated}")

    @staticmethod
    def _calculate_check_digit(nit_str: str) -> int:
        weights = [3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71]
        if len(nit_str) > len(weights):
            raise InvalidTaxIdException("Tax ID is too long.")
        total = 0
        for i, digit in enumerate(reversed(nit_str)):
            total += int(digit) * weights[i]
        rem = total % 11
        if rem > 1:
            return 11 - rem
        return rem

    def __str__(self):
        return self.value
