"""
Domain Entity representing an Affiliate / Reseller Commercial Partner in Michito.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass(frozen=True)
class Partner:
    partner_id: str
    name: str
    commission_rate: float
    discount_rate: float = 0.0
    badge_text: str = ""
    default_campaign_id: Optional[str] = None
    description: str = ""
    active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "partner_id": self.partner_id,
            "name": self.name,
            "commission_rate": self.commission_rate,
            "discount_rate": self.discount_rate,
            "badge_text": self.badge_text,
            "default_campaign_id": self.default_campaign_id,
            "description": self.description,
            "active": self.active,
        }

