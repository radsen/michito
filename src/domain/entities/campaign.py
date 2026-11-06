"""
Campaign Domain Entity.
Represents a multi-client target campaign profile with target geography,
sectors, negative/positive keyword filters, decision maker roles, and 5-touch outreach cadences.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any


@dataclass
class Campaign:
    id: str
    name: str
    client_id: str
    description: str
    country: str = "CO"
    currency: str = "COP"
    cities: List[str] = field(default_factory=list)
    segment: str = "midmarket"
    min_revenue: Optional[str] = None
    sectors: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    roles: List[str] = field(default_factory=list)
    keywords_include: List[str] = field(default_factory=list)
    keywords_exclude: List[str] = field(default_factory=list)
    recommended_angle: str = "Eficiencia Operativa B2B"
    touches: Dict[str, str] = field(default_factory=dict)
    raw_config: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Campaign":
        target = data.get("target", {})
        angles = data.get("angles", {})
        touches = data.get("touches", {})

        # Resolve client_id from campaign id prefix or explicit client field
        cid = data.get("id", "custom")
        client = data.get("client_id") or cid.split("_")[0]

        # Resolve cities list
        cities: List[str] = []
        if target.get("cities"):
            cities = list(target["cities"])
        elif target.get("city") and target.get("city") != "all":
            cities = [target["city"]]
        else:
            cities = ["Santo Domingo"] if target.get("country", "CO").upper() == "DO" else ["Medellín", "Bogotá"]

        return cls(
            id=cid,
            name=data.get("name", cid.title()),
            client_id=client,
            description=data.get("description", ""),
            country=target.get("country", "CO").upper(),
            currency=target.get("currency", "DOP" if target.get("country", "CO").upper() == "DO" else "COP"),
            cities=cities,
            segment=target.get("segment", "midmarket"),
            min_revenue=target.get("min_revenue_cop") or target.get("min_revenue"),
            sectors=target.get("sectors", []),
            categories=target.get("categories", []),
            roles=target.get("roles", []),
            keywords_include=target.get("keywords_include", []),
            keywords_exclude=target.get("keywords_exclude", []),
            recommended_angle=angles.get("recommended", "Solución B2B de Alto Impacto"),
            touches=touches,
            raw_config=data,
        )

