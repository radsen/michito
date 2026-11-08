"""
Prospecting Order Domain Entity.
Represents an on-demand multi-client lead intelligence request through its full lifecycle:
queued -> processing -> awaiting_payment -> paid -> delivered.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any


@dataclass
class ProspectingOrder:
    order_id: str
    client_id: str
    client_name: str
    client_email: str
    campaign_id: str
    country: str = "CO"
    currency: str = "COP"
    cities: List[str] = field(default_factory=list)
    limit: int = 10
    segment: str = "midmarket"
    tier: int = 2
    status: str = "queued"
    client_phone: str = ""
    min_revenue: Optional[str] = None
    sectors: List[str] = field(default_factory=list)
    keywords_include: List[str] = field(default_factory=list)
    keywords_exclude: List[str] = field(default_factory=list)
    target_roles: List[str] = field(default_factory=list)
    amount_in_cents: int = 0
    wompi_transaction_id: Optional[str] = None
    csv_path: Optional[str] = None
    dossier_path: Optional[str] = None
    sample_teaser: List[Dict[str, Any]] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "order_id": self.order_id,
            "client_id": self.client_id,
            "client": {
                "name": self.client_name,
                "email": self.client_email,
                "phone": self.client_phone,
            },
            "request": {
                "campaign_id": self.campaign_id,
                "country": self.country,
                "currency": self.currency,
                "cities": self.cities,
                "limit": self.limit,
                "segment": self.segment,
                "tier": self.tier,
                "min_revenue": self.min_revenue,
                "sectors": self.sectors,
                "keywords_include": self.keywords_include,
                "keywords_exclude": self.keywords_exclude,
                "target_roles": self.target_roles,
            },
            "status": self.status,
            "payment": {
                "provider": "wompi",
                "status": "approved" if self.status == "paid" else "pending",
                "amount_in_cents": self.amount_in_cents,
                "currency": self.currency,
                "transaction_id": self.wompi_transaction_id,
            },
            "delivery": {
                "total_qualified": len(self.sample_teaser),
                "sample_teaser": self.sample_teaser,
                "csv_path": self.csv_path,
                "dossier_path": self.dossier_path,
            },
            "metrics": self.metrics,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

