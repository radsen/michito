class DomainException(Exception):
    """Base exception for domain layer."""
    pass

class InvalidTaxIdException(DomainException):
    """Raised when a Tax ID (NIT) is invalid."""
    pass

class InvalidEbitdaException(DomainException):
    """Raised when EBITDA margin is invalid."""
    pass

class InvalidEmailException(DomainException):
    """Raised when an Email is invalid."""
    pass

class InvalidConfidenceScoreException(DomainException):
    """Raised when a Confidence Score is invalid."""
    pass
