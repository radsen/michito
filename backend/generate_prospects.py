#!/usr/bin/env python3
"""
Universal Colombian & Multi-Country B2B Prospector & Intent Engine (CLI & Entrypoint)
Delegates orchestration to src.application.use_cases.generate_prospects_use_case.GenerateProspectsUseCase
"""

import os
import sys
import argparse
import json
from typing import Optional

# Ensure backend directory and monorepo root are on sys.path
backend_dir = os.path.abspath(os.path.dirname(__file__))
repo_root = os.path.abspath(os.path.join(backend_dir, ".."))
for p in [backend_dir, repo_root]:
    if p not in sys.path:
        sys.path.insert(0, p)

from campaign_loader import list_available_campaigns
from deduplication_ledger import DeduplicationLedger
from src.domain.value_objects.company_segment import list_supported_segments

# Import adapters so they can be discovered or mocked in tests
from src.adapters.registries.colombia.secop_harvester_adapter import SecopHarvesterAdapter
from src.adapters.registries.colombia.secop_contracts_adapter import SecopContractsAdapter
from src.adapters.registries.dominican_republic.dgcp_dr_adapter import DgcpDrAdapter
from src.adapters.verifiers.website_auditor import WebsiteAuditor

# Import use case logic and domain helpers
from src.application.use_cases.generate_prospects_use_case import (
    GenerateProspectsUseCase,
    clean_company_name,
    get_first_name,
    get_segment_metrics,
    verify_mx,
    build_hiring_xray_url,
)


def run_prospector(
    campaign: str = "tinkko_enterprise_offices",
    city: Optional[str] = None,
    limit: int = 10,
    segment: Optional[str] = None,
    sector: Optional[str] = None,
    dry_run: bool = False,
    output_format: str = "both",
):
    """
    Executes the GenerateProspectsUseCase using active adapters and configuration.
    Supports dynamic mocks in unit tests by resolving adapters from current module globals.
    """
    use_case = GenerateProspectsUseCase(
        harvester_co=SecopHarvesterAdapter(timeout=15) if "SecopHarvesterAdapter" in globals() else None,
        harvester_dr=DgcpDrAdapter(timeout=15) if "DgcpDrAdapter" in globals() else None,
        contracts_adapter=SecopContractsAdapter(timeout=6) if "SecopContractsAdapter" in globals() else None,
        web_auditor=WebsiteAuditor(timeout=5) if "WebsiteAuditor" in globals() else None,
        verify_mx_fn=verify_mx,
    )
    return use_case.execute(
        campaign=campaign,
        city=city,
        limit=limit,
        segment=segment,
        sector=sector,
        dry_run=dry_run,
        output_format=output_format,
    )


# Exact alias required by workers, cloud functions, and tests
run_prospecting_job = run_prospector


def main():
    available_campaigns = list_available_campaigns()
    parser = argparse.ArgumentParser(
        description="Universal Multi-Country B2B Prospector & Intent Engine (Michito)"
    )
    parser.add_argument(
        "--campaign",
        type=str,
        default="tinkko_enterprise_offices",
        help=f"Campaign profile ID or YAML file path. Available: {', '.join(available_campaigns)}"
    )
    parser.add_argument(
        "--product",
        type=str,
        default=None,
        help="Alias for --campaign (legacy compatibility)"
    )
    parser.add_argument(
        "--city",
        type=str,
        default=None,
        help="Target city or comma-separated cities (e.g. 'Medellín', 'Bogotá', 'Medellín,Bogotá', 'all')"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Total number of qualified accounts to generate (default: 10)"
    )
    parser.add_argument(
        "--segment",
        type=str,
        default=None,
        choices=list_supported_segments(),
        help="Override company segment (midmarket, enterprise, small, all)"
    )
    parser.add_argument(
        "--sector",
        type=str,
        default=None,
        help="Override target industry sector"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without modifying the master deduplication ledger"
    )
    parser.add_argument(
        "--output-format",
        type=str,
        default="both",
        choices=["markdown", "csv", "both"],
        help="Export format (markdown, csv, or both)"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Display master ledger statistics and exit"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print structured result dictionary as JSON to stdout (for subprocesses/APIs)"
    )

    args = parser.parse_args()

    if args.stats:
        ledger = DeduplicationLedger()
        stats = ledger.get_stats()
        print("\n📊 MASTER LEDGER STATISTICS")
        print(json.dumps(stats, indent=2, ensure_ascii=False))
        return

    active_campaign = args.product or args.campaign

    result = run_prospector(
        campaign=active_campaign,
        city=args.city,
        limit=args.limit,
        segment=args.segment,
        sector=args.sector,
        dry_run=args.dry_run,
        output_format=args.output_format,
    )

    if args.json:
        def serialize_clean(obj):
            if hasattr(obj, "code"):
                return {"code": obj.code, "description": obj.description, "sector_macro": obj.sector_macro}
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

        print("\n__JSON_OUTPUT_START__")
        print(json.dumps(result, indent=2, ensure_ascii=False, default=serialize_clean))
        print("__JSON_OUTPUT_END__")


if __name__ == "__main__":
    main()

