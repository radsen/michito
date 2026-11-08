from dataclasses import dataclass
from typing import Optional
from src.domain.value_objects.email_address import EmailAddress

@dataclass
class DecisionMaker:
    id: str
    name: str
    email: EmailAddress
    role: Optional[str] = None
    linkedin_url: Optional[str] = None
    
    def __post_init__(self):
        if not self.id:
            raise ValueError("Decision Maker must have an ID.")
        if not self.name or not self.name.strip():
            raise ValueError("Decision Maker must have a name.")
