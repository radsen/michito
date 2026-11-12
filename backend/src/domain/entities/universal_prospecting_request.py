"""
Universal Commercial Prospecting Request DTO.
Core domain representation that decouples prospecting orders from hardcoded campaign YAMLs,
supporting on-demand multi-territory quotas, dynamic CIIU sectors, and bespoke targeting criteria.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class LocationAllocation:
    """Represents a specific target territory and its allocated account volume."""
    country: str  # "CO", "DO", "EC"
    region: str   # e.g., "Antioquia", "Cundinamarca", "Distrito Nacional", "Pichincha"
    city: str     # e.g., "Medellín", "Bogotá", "Santo Domingo", "Quito"
    allocated_leads: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "country": self.country.upper(),
            "region": self.region,
            "city": self.city,
            "allocated_leads": self.allocated_leads,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LocationAllocation":
        return cls(
            country=data.get("country", "CO").upper(),
            region=data.get("region") or data.get("city") or "Nacional",
            city=data.get("city") or data.get("region") or "Nacional",
            allocated_leads=int(data.get("allocated_leads") or data.get("quota") or data.get("limit") or 10),
        )


@dataclass
class UniversalProspectingRequest:
    """
    Decoupled, universal B2B prospecting brief.
    Allows searching for companies in any of the 400+ CIIU sectors across 🇨🇴, 🇩🇴, and 🇪🇨.
    """
    # Core Offer Proposition
    offer_description: str  # What the customer sells / value proposition

    # Target Sectors & Classifications
    sectors: List[str] = field(default_factory=list)  # e.g., ["food_agriculture", "construction_infrastructure"]
    ciiu_codes: List[str] = field(default_factory=list)  # e.g., ["C1011", "F4111"]

    # Target Geographies & Sub-Quota Distribution
    locations: List[LocationAllocation] = field(default_factory=list)

    # Decision Maker Roles
    roles: List[str] = field(default_factory=list)  # e.g., ["Director de Compras", "Gerente de Operaciones"]

    # Keyword Matching & Exclusions
    keywords_include: List[str] = field(default_factory=list)
    keywords_exclude: List[str] = field(default_factory=list)
    excluded_nits: List[str] = field(default_factory=list)
    excluded_domains: List[str] = field(default_factory=list)

    # Commercial Volume & Quality Tier
    tier: int = 2  # Tier 1 (Directory), Tier 2 (Decision Makers), Tier 3 (Full Underwriting)
    total_leads: int = 25

    # Optional Preset Linkage (For demonstration case studies / template examples)
    preset_id: Optional[str] = None
    min_revenue_cop: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "offer_description": self.offer_description,
            "sectors": self.sectors,
            "ciiu_codes": self.ciiu_codes,
            "locations": [loc.to_dict() for loc in self.locations],
            "roles": self.roles,
            "keywords_include": self.keywords_include,
            "keywords_exclude": self.keywords_exclude,
            "excluded_nits": self.excluded_nits,
            "excluded_domains": self.excluded_domains,
            "tier": self.tier,
            "total_leads": self.total_leads,
            "preset_id": self.preset_id,
            "min_revenue_cop": self.min_revenue_cop,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UniversalProspectingRequest":
        raw_locs = data.get("locations") or []
        locations: List[LocationAllocation] = []
        if isinstance(raw_locs, list):
            for loc in raw_locs:
                if isinstance(loc, dict):
                    locations.append(LocationAllocation.from_dict(loc))
        elif isinstance(raw_locs, dict):
            # Country allocations fallback e.g. {"CO": 20, "DO": 10}
            for c_code, count in raw_locs.items():
                locations.append(
                    LocationAllocation(
                        country=c_code.upper(),
                        region="Nacional",
                        city="all",
                        allocated_leads=int(count),
                    )
                )

        return cls(
            offer_description=data.get("offer_description") or data.get("query") or data.get("offer") or "Búsqueda B2B Personalizada",
            sectors=data.get("sectors") or [],
            ciiu_codes=data.get("ciiu_codes") or [],
            locations=locations,
            roles=data.get("roles") or [],
            keywords_include=data.get("keywords_include") or [],
            keywords_exclude=data.get("keywords_exclude") or data.get("exclusions") or [],
            excluded_nits=data.get("excluded_nits") or [],
            excluded_domains=data.get("excluded_domains") or [],
            tier=int(data.get("tier") or 2),
            total_leads=int(data.get("total_leads") or data.get("limit") or 25),
            preset_id=data.get("preset_id") or data.get("campaign_id"),
            min_revenue_cop=data.get("min_revenue_cop"),
        )

