"""
Dynamic Location Taxonomy & Concentric Ring Resolution Service.

Resolves geographic territories, metropolitan valleys, and concentric expansion ladders
from PostgreSQL taxonomy_locations with in-memory TTL caching and strict geo-fencing.
"""

import time
import unicodedata
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.adapters.db.models import TaxonomyLocationModel
from src.adapters.db.seed_taxonomy import LOCATION_SEEDS


def normalize_geo_text(text: str) -> str:
    """Normalizes text for fuzzy geographic matching (lowercase, no accents)."""
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    no_accents = "".join(c for c in nfkd if not unicodedata.combining(c))
    return no_accents.lower().strip()


@dataclass
class LocationHierarchy:
    location_id: str
    country_code: str
    country_name: str
    region_name: str
    city_name: str
    aliases: List[str] = field(default_factory=list)
    concentric_rings: Dict[str, List[str]] = field(default_factory=dict)
    expansion_rules: Dict[str, Any] = field(default_factory=dict)
    registry_sources: List[str] = field(default_factory=list)

    def get_rings_for_scope(self, scope: str = "metro_area") -> List[Tuple[int, List[str]]]:
        """
        Returns an ordered list of (ring_index, [cities]) bounded strictly by the requested scope.
        Scope limits:
          - strict_city: ring 0 only
          - metro_area: ring 0 and ring 1 (natural metropolitan valley)
          - regional_corridor: ring 0, ring 1, ring 2 (includes close industrial sub-hubs)
          - national: all rings available
        """
        scope_max_ring = {
            "strict_city": 0,
            "metro_area": 1,
            "regional_corridor": 2,
            "national": 99,
        }
        max_allowed = scope_max_ring.get(scope, 1)

        rings: List[Tuple[int, List[str]]] = []
        for key, cities in self.concentric_rings.items():
            if not key.startswith("ring_"):
                continue
            try:
                ring_idx = int(key.split("_")[1])
            except (ValueError, IndexError):
                continue

            if ring_idx <= max_allowed:
                rings.append((ring_idx, [c for c in cities if c]))

        rings.sort(key=lambda x: x[0])
        if not rings and self.city_name:
            rings.append((0, [self.city_name]))
        return rings


class LocationTaxonomyService:
    """
    Central repository and resolution service for multi-country administrative territories.
    Provides in-memory caching with 1-hour TTL.
    """

    _CACHE_TTL_SECONDS = 3600

    def __init__(self, session_factory=None):
        self._session_factory = session_factory
        self._cache: Dict[str, Tuple[float, LocationHierarchy]] = {}
        self._fallback_seeds: Dict[str, LocationHierarchy] = self._build_fallback_seeds()

    def _build_fallback_seeds(self) -> Dict[str, LocationHierarchy]:
        seeds = {}
        for s in LOCATION_SEEDS:
            hier = LocationHierarchy(
                location_id=s["location_id"],
                country_code=s["country_code"],
                country_name=s["country_name"],
                region_name=s["region_name"],
                city_name=s["city_name"],
                aliases=s.get("aliases", []),
                concentric_rings=s.get("concentric_rings", {}),
                expansion_rules=s.get("expansion_rules", {}),
                registry_sources=s.get("registry_sources", []),
            )
            seeds[s["location_id"]] = hier
        return seeds

    def resolve_location(self, country: str, city: str) -> LocationHierarchy:
        """
        Resolves a country code and target city into a LocationHierarchy with concentric rings.
        Matches by country + canonical city name, or alias substrings.
        """
        c_code = (country or "CO").strip().upper()
        norm_city = normalize_geo_text(city or "Medellín")
        cache_key = f"{c_code}:{norm_city}"

        now = time.time()
        if cache_key in self._cache:
            ts, hierarchy = self._cache[cache_key]
            if now - ts < self._CACHE_TTL_SECONDS:
                return hierarchy

        # 1. Attempt database lookup if session factory available
        hierarchy = self._lookup_database(c_code, norm_city)

        # 2. Fallback to pre-seeded memory graph if DB unavailable or no match
        if not hierarchy:
            hierarchy = self._lookup_fallback(c_code, norm_city)

        # 3. If still unresolved, construct a synthetic single-municipality hierarchy
        if not hierarchy:
            hierarchy = LocationHierarchy(
                location_id=f"{c_code.lower()}_{norm_city}",
                country_code=c_code,
                country_name=c_code,
                region_name=city or "Core",
                city_name=city or "Core",
                aliases=[city] if city else [],
                concentric_rings={"ring_0": [city] if city else []},
                expansion_rules={"default_scope": "metro_area", "max_allowed_ring": 0},
                registry_sources=[],
            )

        self._cache[cache_key] = (now, hierarchy)
        return hierarchy

    def _lookup_database(self, country_code: str, norm_city: str) -> Optional[LocationHierarchy]:
        if not self._session_factory:
            return None

        try:
            with self._session_factory() as session:
                stmt = select(TaxonomyLocationModel).where(
                    TaxonomyLocationModel.country_code == country_code,
                    TaxonomyLocationModel.is_active.is_(True),
                )
                locations = session.scalars(stmt).all()

                # Exact canonical city match
                for loc in locations:
                    if normalize_geo_text(loc.city_name) == norm_city:
                        return self._model_to_hierarchy(loc)

                # Alias match
                for loc in locations:
                    aliases = loc.aliases or []
                    for alias in aliases:
                        if normalize_geo_text(alias) == norm_city:
                            return self._model_to_hierarchy(loc)

                # Substring containment match
                for loc in locations:
                    loc_norm = normalize_geo_text(loc.city_name)
                    if norm_city in loc_norm or loc_norm in norm_city:
                        return self._model_to_hierarchy(loc)
        except Exception:
            return None
        return None

    def _lookup_fallback(self, country_code: str, norm_city: str) -> Optional[LocationHierarchy]:
        candidates = [h for h in self._fallback_seeds.values() if h.country_code == country_code]

        # Exact city match
        for h in candidates:
            if normalize_geo_text(h.city_name) == norm_city:
                return h

        # Alias match
        for h in candidates:
            for alias in h.aliases:
                if normalize_geo_text(alias) == norm_city:
                    return h

        # Substring containment
        for h in candidates:
            h_norm = normalize_geo_text(h.city_name)
            if norm_city in h_norm or h_norm in norm_city:
                return h

        return None

    def _model_to_hierarchy(self, model: TaxonomyLocationModel) -> LocationHierarchy:
        return LocationHierarchy(
            location_id=model.location_id,
            country_code=model.country_code,
            country_name=model.country_name,
            region_name=model.region_name,
            city_name=model.city_name,
            aliases=model.aliases or [],
            concentric_rings=model.concentric_rings or {},
            expansion_rules=model.expansion_rules or {},
            registry_sources=model.registry_sources or [],
        )
