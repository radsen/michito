#!/usr/bin/env python3
"""
Michito B2B Engine — Idempotent Multi-Contact Schema Migration (v2.0)
Applies normalized relational schema for Companies, Individuals, Roles, and Contact Channels.
Safe for SQLite and PostgreSQL (Cloud SQL Staging / Production).
"""

import os
import sys
import argparse
from datetime import datetime, timezone
from sqlalchemy import create_engine, inspect, text

# Add backend directory to path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from src.adapters.db.models import (
    Base,
    CompanyModel,
    IndividualModel,
    CompanyIndividualRoleModel,
    ContactChannelModel,
    CompanyChannelLinkModel,
    IndividualChannelLinkModel,
)


def run_migration(clean_leads: bool = False, verbose: bool = True):
    db_url = os.environ.get("DATABASE_URL") or os.environ.get("TEST_DATABASE_URL") or "sqlite:///outputs/michito_orders.db"
    if verbose:
        print("=" * 80)
        print(" MICHITO B2B ENGINE — DATABASE MIGRATION (MULTI-CONTACT v2.0)")
        print(f" Target Database: {db_url.split('@')[-1] if '@' in db_url else db_url}")
        print("=" * 80)

    is_sqlite = db_url.startswith("sqlite")
    connect_args = {"check_same_thread": False, "timeout": 30} if is_sqlite else {}
    engine = create_engine(db_url, connect_args=connect_args)

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    if verbose:
        print(f"--> Found {len(existing_tables)} existing tables.")

    # 1. Optionally Clean Legacy Flat Leads Cache (Recommended for Staging Refresh)
    if clean_leads:
        if verbose:
            print("--> Cleaning legacy flat lead inventory while preserving orders & clients...")
        with engine.begin() as conn:
            if "order_leads" in existing_tables:
                conn.execute(text("DELETE FROM order_leads;"))
                if verbose:
                    print("    - Cleaned 'order_leads' manifest records.")
            if "leads" in existing_tables:
                conn.execute(text("DELETE FROM leads;"))
                if verbose:
                    print("    - Cleaned 'leads' legacy flat cache.")

    # 2. Idempotent Schema Creation for All Base Models
    if verbose:
        print("--> Creating normalized multi-contact tables if not present...")
    Base.metadata.create_all(bind=engine)

    # 3. Post-Creation Inspection & Verification
    refreshed_inspector = inspect(engine)
    refreshed_tables = set(refreshed_inspector.get_table_names())
    target_tables = [
        "companies",
        "individuals",
        "company_individual_roles",
        "contact_channels",
        "company_channel_links",
        "individual_channel_links",
    ]

    all_ok = True
    for tbl in target_tables:
        if tbl in refreshed_tables:
            cols = [c["name"] for c in refreshed_inspector.get_columns(tbl)]
            if verbose:
                print(f"    [OK] Table '{tbl}' active ({len(cols)} columns).")
        else:
            print(f"    [FAIL] Table '{tbl}' missing!")
            all_ok = False

    if verbose:
        print("=" * 80)
        if all_ok:
            print(" Migration Successfully Completed! Multi-Contact Graph Ready.")
        else:
            print(" Migration Encountered Issues. Review table logs above.")
        print("=" * 80)

    return all_ok


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate Michito database schema to Multi-Contact Enterprise Graph.")
    parser.add_argument("--clean-leads", action="store_true", help="Truncate legacy flat leads cache on Staging.")
    args = parser.parse_args()

    success = run_migration(clean_leads=args.clean_leads)
    sys.exit(0 if success else 1)
