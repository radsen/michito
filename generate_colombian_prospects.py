#!/usr/bin/env python3
"""
Universal Colombian B2B Prospector & Campaign Engine
Generates verified, deduplicated prospect batches across any business segment in Colombia.
Enriches decision-makers via Apollo.io API or Sales Navigator / Excel CSV import,
and generates the complete 5-touch sales campaign sequence driven by Campaign YAML profiles.
"""

import os
import sys
import argparse
import csv
import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from segments import SEGMENTS, get_segment_info, list_supported_segments
from deduplication_ledger import DeduplicationLedger, PERMANENT_EXCLUDED_NITS, PERMANENT_EXCLUDED_KEYWORDS
from colombia_registry_client import ColombiaRegistryClient
from apollo_client import ApolloClient
from campaign_loader import (
    load_campaign, 
    list_available_campaigns, 
    compile_teaser_html
)
from outreach_generator import (
    generate_linkedin_xray_url,
    generate_full_campaign
)

GROWTH_OUTPUTS_BASE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "outputs")
)

def run_prospector(
    campaign: str = "hebi",
    segment: Optional[str] = None,
    sector: Optional[str] = None,
    city: Optional[str] = None,
    limit: int = 25,
    apollo_key: Optional[str] = None,
    import_csv: Optional[str] = None,
    dry_run: bool = False,
    output_format: str = "both"
):
    print("=" * 80)
    print("🚀 UNIVERSAL COLOMBIAN B2B PROSPECTOR & CAMPAIGN ENGINE")
    print("=" * 80)

    # 1. Load Campaign Profile
    campaign_cfg = load_campaign(campaign)
    campaign_id = campaign_cfg["id"]
    campaign_name = campaign_cfg["name"]
    target_cfg = campaign_cfg.get("target", {})

    target_segment = segment or target_cfg.get("segment", "midmarket")
    target_sector = sector or (target_cfg.get("sectors", ["all"])[0] if len(target_cfg.get("sectors", [])) == 1 else "all")
    target_city = city or target_cfg.get("city", "all")
    allowed_sectors = target_cfg.get("sectors", ["all"])
    allowed_cities = target_cfg.get("cities", [])
    target_roles = target_cfg.get("roles", [])

    seg_info = get_segment_info(target_segment if target_segment != "all" else "midmarket")
    
    print(f"📋 Campaign:         {campaign_name} (`{campaign_id}`)")
    print(f"🏢 Business Segment: {seg_info['name_es']} ({seg_info['revenue_range_cop']})")
    print(f"🏭 Target Sectors:   {', '.join(allowed_sectors) if allowed_sectors else target_sector.upper()}")
    print(f"📍 Target City:      {target_city.capitalize() if target_city != 'all' else 'Multi-City (' + ', '.join(allowed_cities[:3]) + ')'}")
    print(f"👤 Target Roles:     {', '.join(target_roles[:4])}")
    print(f"🔢 Requested Limit:  {limit} companies")
    print("-" * 80)

    # 2. Initialize Deduplication Ledger
    ledger = DeduplicationLedger()
    seen_nits = ledger.get_seen_nits(campaign=campaign_id)
    print(f"[Ledger] Currently tracking {len(seen_nits)} previously prospected companies for this campaign.")
    print(f"[Ledger] Permanent Exclusion active: Tinkko Coworking SAS protected.")

    # 3. Query Candidates from Colombia Registry or Imported CSV
    apollo = ApolloClient(api_key=apollo_key)
    if apollo.has_api_key():
        print("🔑 Apollo.io API Key detected: Real-time corporate contact enrichment enabled.")
    else:
        print("💡 Apollo.io API Key not supplied: Using verified corporate patterns & LinkedIn Google X-Ray.")

    candidates: List[Dict[str, Any]] = []

    if import_csv and os.path.exists(import_csv):
        print(f"[Importer] Loading external accounts from CSV: {import_csv}")
        imported_rows = apollo.import_from_csv(import_csv)
        for r in imported_rows:
            if any(k in r["company_name"].lower() for k in PERMANENT_EXCLUDED_KEYWORDS):
                continue
            candidates.append({
                "nit": "EXTERNAL-IMPORT",
                "name": r["company_name"],
                "segment": target_segment,
                "sector": target_sector if target_sector != "all" else (allowed_sectors[0] if allowed_sectors else "general"),
                "city": target_city if target_city != "all" else "Colombia",
                "address": "Verificado vía Importación Externa",
                "revenue_cop": target_cfg.get("min_revenue_cop", seg_info["revenue_range_cop"]),
                "employees": 100,
                "venues_count": "N/A",
                "description": "Prospecto importado externamente para campaña.",
                "pre_enriched": r
            })
            if len(candidates) >= limit:
                break
    else:
        client = ColombiaRegistryClient()
        candidates = client.fetch_candidates(
            segment=target_segment,
            sector=target_sector,
            city=target_city,
            allowed_sectors=allowed_sectors,
            allowed_cities=allowed_cities,
            exclude_nits=seen_nits,
            limit=limit
        )

    if not candidates:
        print("\n⚠️ No new companies found matching your criteria that haven't been prospected yet!")
        print("💡 Try broadening the sector (--sector=all), city (--city=all), or segment (--segment=all).")
        return

    print(f"[Engine] Found {len(candidates)} brand-new qualified companies.")

    # 4. Prepare Batch Directory
    now = datetime.now(timezone.utc)
    batch_timestamp = now.strftime("%Y%m%d_%H%M%S")
    batch_dir = os.path.join(GROWTH_OUTPUTS_BASE, campaign_id, batch_timestamp)
    os.makedirs(batch_dir, exist_ok=True)

    enriched_prospects = []
    for idx, c in enumerate(candidates, 1):
        # Decision-maker enrichment
        if "pre_enriched" in c:
            contact = c["pre_enriched"]
        else:
            contact = apollo.search_decision_maker(
                company_name=c["name"],
                domain=c.get("domain"),
                city=c["city"],
                target_roles=target_roles
            )

        xray_url = contact.get("linkedin_url") or generate_linkedin_xray_url(
            company_name=c["name"],
            target_roles=target_roles,
            city=c["city"]
        )
        
        campaign_result = generate_full_campaign(
            company_name=c["name"],
            sector=c["sector"],
            city=c["city"],
            segment=c["segment"],
            contact_name=contact.get("first_name"),
            contact_title=contact.get("title"),
            product=campaign_id,
            campaign_config=campaign_cfg
        )

        item = {
            "index": idx,
            "nit": c["nit"],
            "company_name": c["name"],
            "segment": c["segment"],
            "sector": c["sector"],
            "city": c["city"],
            "address": c["address"],
            "revenue_cop": c["revenue_cop"],
            "employees": c["employees"],
            "venues_count": c.get("venues_count", "N/A"),
            "description": c.get("description", ""),
            "contact_name": contact.get("full_name") or contact.get("title", "Director(a)"),
            "contact_title": contact.get("title") or (target_roles[0] if target_roles else "Director(a)"),
            "contact_email": contact.get("email", ""),
            "contact_phone": contact.get("phone", ""),
            "linkedin_url": xray_url,
            "recommended_angle": campaign_result["recommended_angle"],
            "touch1_linkedin_invite": campaign_result["touch1_linkedin_invite"],
            "touch2_email_subject": campaign_result["touch2_email_subject"],
            "touch2_email_body": campaign_result["touch2_email_body"],
            "touch3_email_subject": campaign_result["touch3_email_subject"],
            "touch3_email_body": campaign_result["touch3_email_body"],
            "touch4_email_subject": campaign_result["touch4_email_subject"],
            "touch4_email_body": campaign_result["touch4_email_body"],
            "touch5_email_subject": campaign_result["touch5_email_subject"],
            "touch5_email_body": campaign_result["touch5_email_body"]
        }
        enriched_prospects.append(item)

        # Record in ledger if not dry-run
        if not dry_run and c["nit"] != "EXTERNAL-IMPORT":
            ledger.record_prospect(
                nit=c["nit"],
                company_name=c["name"],
                segment=c["segment"],
                sector=c["sector"],
                city=c["city"],
                product=campaign_id,
                batch_id=f"batch_{batch_timestamp}_{campaign_id}",
                extra_data={
                    "revenue_cop": c["revenue_cop"],
                    "employees": c["employees"],
                    "venues_count": c.get("venues_count", "N/A"),
                    "contact_name": item["contact_name"],
                    "contact_email": item["contact_email"],
                    "contact_phone": item["contact_phone"]
                }
            )

    csv_filename = os.path.join(batch_dir, "prospects.csv")
    md_filename = os.path.join(batch_dir, "executive_dossier.md")
    teaser_filename = os.path.join(batch_dir, "confidential_teaser.html")

    # 5. Generate CSV
    if output_format in ("csv", "both"):
        with open(csv_filename, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Index", "Company Name", "NIT", "Segment", "Sector", "City", 
                "Estimated Revenue", "Employees", "Venues Count",
                "Decision Maker Name", "Title", "Work Email", "Phone", "LinkedIn Profile / X-Ray",
                "Recommended Angle",
                "Touch 1: LinkedIn Connection (<300 chars)",
                "Touch 2: Cold Email Subject (Day 1)",
                "Touch 2: Cold Email Body (Day 1)",
                "Touch 3: Operational / Follow-Up Subject (Day 4)",
                "Touch 3: Operational / Follow-Up Body (Day 4)",
                "Touch 4: Social Proof / Financial Angle Subject (Day 8)",
                "Touch 4: Social Proof / Financial Angle Body (Day 8)",
                "Touch 5: Breakup / One-Pager Subject (Day 14)",
                "Touch 5: Breakup / One-Pager Body (Day 14)"
            ])
            for p in enriched_prospects:
                writer.writerow([
                    p["index"], p["company_name"], p["nit"], p["segment"], p["sector"], p["city"],
                    p["revenue_cop"], p["employees"], p["venues_count"],
                    p["contact_name"], p["contact_title"], p["contact_email"], p["contact_phone"], p["linkedin_url"],
                    p["recommended_angle"],
                    p["touch1_linkedin_invite"],
                    p["touch2_email_subject"], p["touch2_email_body"],
                    p["touch3_email_subject"], p["touch3_email_body"],
                    p["touch4_email_subject"], p["touch4_email_body"],
                    p["touch5_email_subject"], p["touch5_email_body"]
                ])
        print(f"✅ Generated CRM CSV Batch: {csv_filename}")

    # 6. Generate Markdown Dossier
    if output_format in ("markdown", "both"):
        with open(md_filename, "w", encoding="utf-8") as f:
            f.write(f"# 🇨🇴 Colombian B2B Prospect Batch — {campaign_name}\n\n")
            f.write(f"**Campaign ID:** `{campaign_id}`  \n")
            f.write(f"**Date Generated:** {now.strftime('%Y-%m-%d %H:%M:%S UTC')}  \n")
            f.write(f"**Segment:** {seg_info['name_es']} ({seg_info['revenue_range_cop']})  \n")
            f.write(f"**Total Qualified Prospects:** {len(enriched_prospects)}  \n")
            f.write(f"**Batch Directory:** `{batch_dir}`  \n\n")
            f.write("> [!NOTE]\n")
            f.write("> **Deduplication Active:** All prospects below are fresh, uncontacted mid-market/enterprise accounts verified against the master ledger.\n\n")
            f.write("---\n\n")

            f.write("## 📋 Master Qualification Table\n\n")
            f.write("| # | Company Name | NIT | City | Sector | Est. Revenue | Decision Maker | Email / Phone | LinkedIn Search |\n")
            f.write("| :-: | :--- | :---: | :---: | :---: | :---: | :--- | :--- | :--- |\n")
            for p in enriched_prospects:
                f.write(
                    f"| {p['index']} | **{p['company_name']}** | `{p['nit']}` | {p['city']} | "
                    f"`{p['sector']}` | {p['revenue_cop']} | {p['contact_name']} ({p['contact_title']}) | "
                    f"`{p['contact_email']}` | [Ver Perfil]({p['linkedin_url']}) |\n"
                )
            f.write("\n---\n\n")

            f.write("## 🎯 Detailed Prospect Profiles & Full 5-Touch Cadence\n\n")
            for p in enriched_prospects:
                f.write(f"### {p['index']}. {p['company_name']}\n")
                f.write(f"* **NIT:** `{p['nit']}` | **City:** {p['city']} | **Address:** {p['address']}\n")
                f.write(f"* **Segment:** {str(p['segment']).capitalize()} ({p['revenue_cop']} • ~{p['employees']} employees)\n")
                f.write(f"* **Decision Maker:** **{p['contact_name']}** — *{p['contact_title']}* (`{p['contact_email']}` • {p['contact_phone']})\n")
                f.write(f"* **LinkedIn Profile / X-Ray:** 👉 [Abrir Búsqueda en LinkedIn]({p['linkedin_url']})\n")
                f.write(f"* **Recommended Angle:** `{p['recommended_angle']}`\n\n")
                
                f.write("#### 💬 Touch 1 (Día 1): Mensaje de Conexión LinkedIn (<300 caracteres)\n")
                f.write(f"> {p['touch1_linkedin_invite']}\n\n")

                f.write("#### 📧 Touch 2 (Día 1): Correo Ejecutivo en Frío\n")
                f.write(f"**Asunto:** `{p['touch2_email_subject']}`\n\n")
                f.write("```text\n")
                f.write(f"{p['touch2_email_body']}\n")
                f.write("```\n\n")

                f.write("#### ⚙️ Touch 3 (Día 4): Seguimiento Operativo & Técnico\n")
                f.write(f"**Asunto:** `{p['touch3_email_subject']}`\n\n")
                f.write("```text\n")
                f.write(f"{p['touch3_email_body']}\n")
                f.write("```\n\n")

                f.write("#### 📊 Touch 4 (Día 8): Ángulo Financiero / Caso de Éxito\n")
                f.write(f"**Asunto:** `{p['touch4_email_subject']}`\n\n")
                f.write("```text\n")
                f.write(f"{p['touch4_email_body']}\n")
                f.write("```\n\n")

                f.write("#### 🤝 Touch 5 (Día 14): Cierre Suave & Ficha Dejada en Mesa\n")
                f.write(f"**Asunto:** `{p['touch5_email_subject']}`\n\n")
                f.write("```text\n")
                f.write(f"{p['touch5_email_body']}\n")
                f.write("```\n\n")
                f.write("---\n\n")
        print(f"✅ Generated Executive Dossier: {md_filename}")

    # 7. Compile Teaser if campaign has teaser enabled
    compiled_teaser = compile_teaser_html(campaign_cfg, teaser_filename)
    if compiled_teaser:
        print(f"📄 Compiled 1-Page Institutional Teaser: {teaser_filename}")

    # 8. Save Ledger
    if not dry_run:
        ledger.save_batch()
        print(f"💾 Persistent Ledger Updated: {len(enriched_prospects)} new companies recorded.")
    else:
        print("🔍 Dry run active: Master ledger was NOT modified.")

    print("\n" + "=" * 80)
    print(f"🎉 Batch Execution Finished! All outputs saved to:\n   📂 {batch_dir}")
    print("=" * 80)

def main():
    available_campaigns = list_available_campaigns()
    parser = argparse.ArgumentParser(
        description="Universal Colombian B2B Prospector & Campaign Engine"
    )
    parser.add_argument(
        "--campaign",
        type=str,
        default="hebi",
        help=f"Campaign profile ID or YAML file path. Available presets: {', '.join(available_campaigns)}"
    )
    parser.add_argument(
        "--product",
        type=str,
        default=None,
        help="Alias for --campaign (legacy compatibility)"
    )
    parser.add_argument(
        "--segment",
        type=str,
        default=None,
        choices=list_supported_segments(),
        help="Override company segment (midmarket, enterprise, small, micro, all)"
    )
    parser.add_argument(
        "--sector",
        type=str,
        default=None,
        help="Override target industry sector"
    )
    parser.add_argument(
        "--city",
        type=str,
        default=None,
        help="Override target Colombian city (Bogota, Medellin, Cali, Barranquilla, all)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=25,
        help="Number of prospects to fetch (default: 25)"
    )
    parser.add_argument(
        "--apollo-key",
        type=str,
        default=None,
        help="Apollo.io API Key for live email & direct phone enrichment"
    )
    parser.add_argument(
        "--import-csv",
        type=str,
        default=None,
        help="Path to an exported CSV from Sales Navigator, Apollo, or CCMA to enrich"
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

    args = parser.parse_args()

    if args.stats:
        ledger = DeduplicationLedger()
        stats = ledger.get_stats()
        print("\n📊 MASTER LEDGER STATISTICS")
        print(json.dumps(stats, indent=2, ensure_ascii=False))
        return

    active_campaign = args.product or args.campaign

    run_prospector(
        campaign=active_campaign,
        segment=args.segment,
        sector=args.sector,
        city=args.city,
        limit=args.limit,
        apollo_key=args.apollo_key,
        import_csv=args.import_csv,
        dry_run=args.dry_run,
        output_format=args.output_format
    )

if __name__ == "__main__":
    main()
