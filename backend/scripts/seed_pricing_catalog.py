#!/usr/bin/env python3
"""
Seed script to populate the Chiketto Dynamic Pricing Catalog in PostgreSQL.
Inserts master products, regional prices, progressive volume discounts, and affiliate rules.
"""

import os
import sys

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.adapters.db.sql_order_adapter import SqlOrderAdapter
from src.domain.services.pricing_catalog_service import PricingCatalogService

def main():
    print("=" * 70)
    print("CHIKETTO DYNAMIC PRICING CATALOG SEEDER")
    print("=" * 70)
    adapter = SqlOrderAdapter()
    service = PricingCatalogService.get_instance(session_factory=adapter._get_session)
    seeded = service.seed_catalog_if_empty()
    if seeded:
        print("[OK] Successfully seeded dynamic pricing catalog.")
    else:
        print("[INFO] Catalog already seeded or tables contain active products.")

    catalog = service.get_active_catalog("COP")
    print(f"[CATALOG COP] Min Order: {catalog.get('min_order_leads')}")
    print(f"             Tier Prices: {catalog.get('tier_prices')}")
    print(f"             Products: {len(catalog.get('products', []))}")
    print("=" * 70)

if __name__ == "__main__":
    main()
