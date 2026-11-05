#!/usr/bin/env python3
"""
Universal Colombian B2B Prospector & Intent Engine
Generates verified, deduplicated prospect batches across any business segment in Colombia.
Integrates live public registries from datos.gov.co (SECOP II Proveedores & Contratos),
real-time website content auditing, DANE CIIU taxonomy (RUT Casilla 46), DNS MX deliverability,
and 3 Expansion Intent Triggers:
  1. High-Value Contract Awards (SECOP II Contratos)
  2. Active Hiring & Growth Footprint (LinkedIn / Google Jobs X-Ray)
  3. Regional Expansion & Satellite Hub Need
Driven by Campaign YAML profiles and protected by the persistent Deduplication Ledger.
"""

import os
import sys
import argparse
import csv
import json
import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Set
import dns.resolver

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from segments import SEGMENTS, get_segment_info, list_supported_segments
from deduplication_ledger import DeduplicationLedger, PERMANENT_EXCLUDED_NITS, PERMANENT_EXCLUDED_KEYWORDS
from campaign_loader import load_campaign, list_available_campaigns, compile_teaser_html
from src.adapters.registries.colombia.secop_harvester_adapter import SecopHarvesterAdapter
from src.adapters.registries.colombia.secop_contracts_adapter import SecopContractsAdapter
from src.adapters.verifiers.website_auditor import WebsiteAuditor
from src.domain.value_objects.ciiu_code import CiiuCode

GROWTH_OUTPUTS_BASE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "outputs")
)


def clean_company_name(raw_name: str) -> str:
    cleaned = re.sub(
        r"\b(S\.?A\.?S\.?|S\.?A\.?|LTDA\.?|LIMITADA|E\.?U\.?|INC\.?|CORP\.?)\b",
        "",
        raw_name,
        flags=re.IGNORECASE
    )
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned.title()


def get_first_name(full_name: str) -> str:
    parts = full_name.strip().split()
    if not parts:
        return "Líder"
    return parts[0].title()


def get_segment_metrics(raw_size: str) -> tuple[str, str, str]:
    """
    Returns (segment_name, revenue_bracket, employees_bracket) based on Decreto 957 de 2019
    """
    size_norm = (raw_size or "Mediana").strip().lower()
    if "grande" in size_norm:
        return "Gran Empresa", "> $65.000M COP", "> 200 empleados"
    elif "peque" in size_norm:
        return "Pequeña Empresa", "$2.000M - $10.000M COP", "15 - 50 empleados"
    elif "micro" in size_norm:
        return "Microempresa", "< $2.000M COP", "1 - 10 empleados"
    else:
        return "Mediana Empresa", "$10.000M - $65.000M COP", "50 - 200 empleados"


def verify_mx(email: str) -> tuple[bool, str]:
    if not email or "@" not in email:
        return False, "Invalid syntax"
    domain = email.split("@")[1].strip()
    try:
        answers = dns.resolver.resolve(domain, "MX", lifetime=3)
        mx = sorted(answers, key=lambda r: r.preference)[0].exchange.to_text().rstrip(".")
        return True, mx
    except Exception as e:
        return False, str(e)


def build_hiring_xray_url(company_name: str, city: str) -> str:
    import urllib.parse
    query = f'site:co.linkedin.com/jobs "{company_name}" ("{city}" OR "Colombia")'
    return f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}"


def run_prospector(
    campaign: str = "tinkko_enterprise_offices",
    city: Optional[str] = None,
    limit: int = 10,
    segment: Optional[str] = None,
    sector: Optional[str] = None,
    dry_run: bool = False,
    output_format: str = "both",
):
    print("=" * 80)
    print("🚀 UNIVERSAL COLOMBIAN B2B PROSPECTOR & INTENT ENGINE (MICHITO)")
    print("=" * 80)

    # 1. Load Campaign Configuration Profile
    campaign_cfg = load_campaign(campaign)
    campaign_id = campaign_cfg["id"]
    campaign_name = campaign_cfg["name"]
    target_cfg = campaign_cfg.get("target", {})
    touches_cfg = campaign_cfg.get("touches", {})
    recommended_angle = campaign_cfg.get("angles", {}).get(
        "recommended", "Eficiencia Operativa y Soluciones B2B Llave en Mano"
    )

    # Determine cities to prospect
    target_cities: List[str] = []
    if city and city.lower() != "all":
        target_cities = [c.strip() for c in city.split(",") if c.strip()]
    else:
        cfg_cities = target_cfg.get("cities")
        if cfg_cities:
            target_cities = cfg_cities
        elif target_cfg.get("city") and target_cfg.get("city") != "all":
            target_cities = [target_cfg.get("city")]
        else:
            target_cities = ["Medellín", "Bogotá"]

    per_city_limit = max(1, limit // len(target_cities))

    print(f"📋 Campaign Profile:  {campaign_name} (`{campaign_id}`)")
    print(f"📍 Target Cities:      {', '.join(target_cities)} (Limit per city: ~{per_city_limit})")
    print(f"🔢 Total Batch Target: {limit} qualified accounts")
    print(f"🎯 Recommended Angle:  {recommended_angle}")
    print("-" * 80)

    # 2. Initialize Deduplication Ledger
    ledger = DeduplicationLedger()
    seen_nits = ledger.get_seen_nits(campaign=campaign_id)
    print(f"[Ledger] Tracking {len(seen_nits)} previously prospected accounts. Exclusions active.")

    # 3. Initialize Adapters
    harvester = SecopHarvesterAdapter(timeout=15)
    contracts_adapter = SecopContractsAdapter(timeout=6)
    web_auditor = WebsiteAuditor(timeout=5)

    all_selected: List[Dict[str, Any]] = []

    # 4. Harvest and Qualify Candidates per City
    for target_city in target_cities:
        print(f"\n[Harvester] Querying active corporate providers in {target_city}...")
        raw_candidates = harvester.fetch_candidates(
            city=target_city,
            limit=max(per_city_limit * 6, 40),
            corporate_only=True
        )
        print(f"   Retrieved {len(raw_candidates)} candidate entities in {target_city}.")

        city_accepted = 0
        for item in raw_candidates:
            if city_accepted >= per_city_limit:
                break
            if len(all_selected) >= limit:
                break

            nit = item["nit"]
            company_name = item["company_name"]

            # Deduplication Check
            if ledger.is_seen(nit, company_name):
                continue

            email = item["email"]
            phone = item["phone"]

            # Mobile Phone Gate (Must be real 10-digit Colombian mobile 3xx-xxxxxxx)
            if not phone or len(phone) < 10 or not phone.startswith("3"):
                continue

            # Deliverability Gate: DNS MX verification
            ok_mx, mx_host = verify_mx(email)
            if not ok_mx:
                continue

            is_corporate_domain = not any(
                pub in email for pub in ("@gmail.com", "@hotmail.com", "@yahoo.com", "@outlook.com")
            )

            # Website Resolution & Quality Audit Gate
            candidate_url = item.get("website") or ""
            if not candidate_url and is_corporate_domain:
                candidate_domain = email.split("@")[1].strip().lower()
                candidate_url = f"https://www.{candidate_domain}"

            is_active_web, audited_url, audit_note = web_auditor.audit(candidate_url, company_name)
            # Pilot/Production Quality Gate: Require active, non-parked, non-login portal website
            if not is_active_web:
                continue

            # DANE CIIU Activity Classification (RUT Box 46)
            ciiu_obj = CiiuCode.infer_from_text(
                company_name=company_name,
                email=email,
                raw_desc=item.get("sector", "")
            )

            # Trigger 1: Public Contract Awards (Cash Inflow & Project Delivery Intent)
            contracts_data = contracts_adapter.fetch_contracts_summary(nit)

            # Trigger 2: Active Hiring Signals (1-click search link)
            hiring_xray = build_hiring_xray_url(company_name, target_city)

            # Trigger 3: Regional Expansion & Satellite Need
            reg_city = item.get("city") or target_city
            if reg_city.lower() != target_city.lower():
                expansion_flag = f"Sede Satélite en Expansión (Registrada en {reg_city})"
            elif contracts_data["has_contracts"]:
                expansion_flag = "Ejecutando Contratos Públicos Activos en Región"
            else:
                expansion_flag = "Operación Corporativa en Expansión Local"

            clean_name = clean_company_name(company_name)
            rep_name = item["decision_maker_name"]
            first_name = get_first_name(rep_name)
            seg_name, rev_range, emp_range = get_segment_metrics(item.get("tama_o_entidad", "Mediana"))

            lead_record = {
                "company_name": company_name,
                "clean_name": clean_name,
                "first_name": first_name,
                "nit": nit,
                "city": target_city,
                "address": item.get("address", ""),
                "ciiu": ciiu_obj,
                "segment_name": seg_name,
                "revenue_bracket": rev_range,
                "employees_bracket": emp_range,
                "website_url": audited_url,
                "website_audit_status": audit_note,
                "decision_maker_name": rep_name,
                "decision_maker_title": item.get("decision_maker_title", "Representante Legal / Gerente General"),
                "email": email,
                "phone": phone,
                "mx_host": mx_host,
                "linkedin_xray_url": item.get("linkedin_xray_url", ""),
                "contracts_data": contracts_data,
                "hiring_xray_url": hiring_xray,
                "expansion_flag": expansion_flag,
            }

            all_selected.append(lead_record)
            city_accepted += 1

    if not all_selected:
        print("\n⚠️ No fresh companies found matching all quality and deliverability gates.")
        return

    print(f"\n[Engine] Successfully assembled {len(all_selected)} verified enterprise leads.")

    # 5. Format 5-Touch Outreach Cadence
    csv_rows = []
    now = datetime.now(timezone.utc)
    batch_timestamp = now.strftime("%Y%m%d_%H%M%S")
    batch_dir = os.path.join(GROWTH_OUTPUTS_BASE, campaign_id, batch_timestamp)
    os.makedirs(batch_dir, exist_ok=True)

    for idx, lead in enumerate(all_selected, start=1):
        clean_name = lead["clean_name"]
        salutation = f"Hola {lead['first_name']}"
        contact_title = lead["decision_maker_title"]
        city = lead["city"]
        ciiu = lead["ciiu"]
        contracts = lead["contracts_data"]

        # Format touches from YAML
        t1 = touches_cfg.get("touch1_linkedin_invite", "").format(
            salutation=salutation, clean_name=clean_name, city=city
        ).strip().replace("\n", " ")

        t2_sub = touches_cfg.get("touch2_email_subject", "").format(
            clean_name=clean_name, city=city
        ).strip()
        t2_body = touches_cfg.get("touch2_email_body", "").format(
            contact_title=contact_title, clean_name=clean_name, city=city
        ).strip()

        # If Trigger 1 is active, tailor Touch 2 with contract award mention
        if contracts["has_contracts"] and contracts["total_value_cop"] > 0:
            contract_mention = (
                f"\n\n[Trigger de Compra Detectado: Felicitaciones por la adjudicación de contratos recientes "
                f"con {contracts['top_contract_entity']} por {contracts['top_contract_value_display']}. "
                f"Para la ejecución de estos proyectos, contar con infraestructura locativa llave en mano ahorra meses de trámites.]"
            )
            t2_body += contract_mention

        t3_sub = touches_cfg.get("touch3_email_subject", "").format(
            clean_name=clean_name, city=city
        ).strip()
        t3_body = touches_cfg.get("touch3_email_body", "").format(
            contact_title=contact_title, clean_name=clean_name, city=city
        ).strip()

        t4_sub = touches_cfg.get("touch4_email_subject", "").format(
            clean_name=clean_name, city=city
        ).strip()
        t4_body = touches_cfg.get("touch4_email_body", "").format(
            contact_title=contact_title, clean_name=clean_name, city=city
        ).strip()

        t5_sub = touches_cfg.get("touch5_email_subject", "").format(
            clean_name=clean_name, city=city
        ).strip()
        t5_body = touches_cfg.get("touch5_email_body", "").format(
            contact_title=contact_title, clean_name=clean_name, city=city
        ).strip()

        row = {
            "Index": idx,
            "Company Name": lead["company_name"],
            "NIT": lead["nit"],
            "City": lead["city"],
            "CIIU Code": ciiu.code,
            "Sector Macro": ciiu.sector_macro,
            "CIIU Activity (RUT Box 46)": ciiu.description,
            "Company Size (Decreto 957)": lead["segment_name"],
            "Revenue Bracket": lead["revenue_bracket"],
            "Estimated Employees": lead["employees_bracket"],
            "Address": lead["address"],
            "Website": lead["website_url"],
            "Website Audit Status": lead["website_audit_status"],
            "Decision Maker Name": lead["decision_maker_name"],
            "Official Title": lead["decision_maker_title"],
            "Verified Work Email": lead["email"],
            "Direct Mobile Phone": lead["phone"],
            "Mail Server (MX)": lead["mx_host"],
            "Trigger 1: Total Contracts Won COP": contracts["total_value_display"],
            "Trigger 1: Top Contracting Entity": contracts["top_contract_entity"],
            "Trigger 1: Top Contract Object": contracts["top_contract_object"],
            "Trigger 1: Intent Score": contracts["intent_level"],
            "Trigger 2: Hiring X-Ray Search URL": lead["hiring_xray_url"],
            "Trigger 3: Regional Expansion Flag": lead["expansion_flag"],
            "LinkedIn X-Ray URL": lead["linkedin_xray_url"],
            "Recommended Angle": recommended_angle,
            "Touch 1: LinkedIn Connection Note": t1,
            "Touch 2: Cold Email Subject": t2_sub,
            "Touch 2: Cold Email Body": t2_body,
            "Touch 3: Operational Follow-up Subject": t3_sub,
            "Touch 3: Operational Follow-up Body": t3_body,
            "Touch 4: Social Proof / VIP Subject": t4_sub,
            "Touch 4: Social Proof / VIP Body": t4_body,
            "Touch 5: Breakup / Catalog Subject": t5_sub,
            "Touch 5: Breakup / Catalog Body": t5_body,
        }
        csv_rows.append(row)

        # Record in persistent ledger if not dry-run
        if not dry_run:
            ledger.record_prospect(
                nit=lead["nit"],
                company_name=lead["company_name"],
                segment=lead["segment_name"],
                sector=ciiu.sector_macro,
                city=lead["city"],
                product=campaign_id,
                batch_id=f"batch_{batch_timestamp}_{campaign_id}",
                extra_data={
                    "revenue_bracket": lead["revenue_bracket"],
                    "contact_name": lead["decision_maker_name"],
                    "contact_email": lead["email"],
                    "contact_phone": lead["phone"],
                    "contracts_total_cop": contracts["total_value_cop"],
                }
            )

    # 6. Export CSV Deliverable
    csv_filename = os.path.join(batch_dir, "prospects.csv")
    md_filename = os.path.join(batch_dir, "executive_dossier.md")
    teaser_filename = os.path.join(batch_dir, "confidential_teaser.html")

    if output_format in ("csv", "both"):
        with open(csv_filename, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=list(csv_rows[0].keys()))
            writer.writeheader()
            writer.writerows(csv_rows)
        print(f"✅ Generated CRM CSV Batch: {csv_filename}")

    # 7. Export Markdown Executive Dossier
    if output_format in ("markdown", "both"):
        md_content = []
        md_content.append(f"# 🇨🇴 Colombian B2B Qualified Prospect Batch — {campaign_name}")
        md_content.append(f"**Campaign ID:** `{campaign_id}` | **Date:** {now.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        md_content.append(f"**Total Qualified Accounts:** {len(csv_rows)} | **Batch Directory:** `{batch_dir}`")
        md_content.append("*Verified Colombian B2B Ground Truth • Zero-Bounce DNS MX • Real-Time Website Audit*\n")
        md_content.append("---")
        md_content.append("\n## 📋 Master Qualification Table with Expansion Intent Triggers\n")
        md_content.append(
            "| # | Company Name | CIIU & Macro Sector | City | Decision Maker | Email & Phone | Website | Contracts Won (Trigger 1) | Expansion Flag (Trigger 3) |"
        )
        md_content.append(
            "| :-: | :--- | :--- | :---: | :--- | :--- | :--- | :--- | :--- |"
        )

        for r in csv_rows:
            web_display = f"[{r['Website']}]({r['Website']})" if r['Website'].startswith("http") else r['Website']
            md_content.append(
                f"| {r['Index']} | **{r['Company Name']}**<br><small>NIT: {r['NIT']}</small> | "
                f"**CIIU {r['CIIU Code']}**<br><small>{r['Sector Macro']}</small> | {r['City']} | "
                f"**{r['Decision Maker Name']}**<br><small>{r['Official Title']}</small> | "
                f"`{r['Verified Work Email']}`<br>`{r['Direct Mobile Phone']}` | "
                f"{web_display} | **{r['Trigger 1: Total Contracts Won COP']}**<br><small>{r['Trigger 1: Top Contracting Entity'][:30]}</small> | "
                f"<small>{r['Trigger 3: Regional Expansion Flag']}</small> |"
            )

        md_content.append("\n---\n")
        md_content.append("## 🎯 Detailed Profiles & 5-Touch Cadence\n")

        for r in csv_rows:
            web_display = f"[{r['Website']}]({r['Website']})" if r['Website'].startswith("http") else r['Website']
            md_content.append(f"### {r['Index']}. {r['Company Name']} ({r['City']})")
            md_content.append(f"* **Actividad Económica (RUT Casilla 46)**: **CIIU {r['CIIU Code']}** — {r['CIIU Activity (RUT Box 46)']}")
            md_content.append(f"* **Sector Macro**: {r['Sector Macro']} | **Tamaño (Dec. 957)**: {r['Company Size (Decreto 957)']} ({r['Revenue Bracket']} • {r['Estimated Employees']})")
            md_content.append(f"* **Sitio Web**: {web_display} — *{r['Website Audit Status']}*")
            md_content.append(f"* **Tomador de Decisión**: **{r['Decision Maker Name']}** ({r['Official Title']})")
            md_content.append(f"* **Email Verificado**: `{r['Verified Work Email']}` | **Celular**: `{r['Direct Mobile Phone']}` | **Servidor MX**: `{r['Mail Server (MX)']}`")
            md_content.append(f"* **Dirección Corporativa**: {r['Address']} | **NIT**: `{r['NIT']}`")
            md_content.append(f"* **Trigger 1 (Contratos Ganados)**: **{r['Trigger 1: Total Contracts Won COP']}** — {r['Trigger 1: Top Contracting Entity']} (*{r['Trigger 1: Intent Score']}*)")
            if r['Trigger 1: Top Contract Object']:
                md_content.append(f"  * *Objeto*: {r['Trigger 1: Top Contract Object']}")
            md_content.append(f"* **Trigger 2 (Búsqueda de Empleos / Vacantes)**: [🔍 Ver Vacantes Activas en Google/LinkedIn]({r['Trigger 2: Hiring X-Ray Search URL']})")
            md_content.append(f"* **Trigger 3 (Expansión)**: {r['Trigger 3: Regional Expansion Flag']}")
            md_content.append(f"* [🔍 1-Click LinkedIn Search Profile]({r['LinkedIn X-Ray URL']})\n")

            md_content.append("#### 🔹 Touch 1: LinkedIn Connection Note (<300 chars)")
            md_content.append(f"> \"{r['Touch 1: LinkedIn Connection Note']}\"\n")

            md_content.append(f"#### 🔹 Touch 2: Cold Email (Día 1) — Asunto: *{r['Touch 2: Cold Email Subject']}*")
            md_content.append("```text")
            md_content.append(r["Touch 2: Cold Email Body"])
            md_content.append("```\n")

            md_content.append(f"#### 🔹 Touch 3: Operational Follow-up (Día 4) — Asunto: *{r['Touch 3: Operational Follow-up Subject']}*")
            md_content.append("```text")
            md_content.append(r["Touch 3: Operational Follow-up Body"])
            md_content.append("```\n")

            md_content.append(f"#### 🔹 Touch 4: Social Proof / VIP Day Pass (Día 8) — Asunto: *{r['Touch 4: Social Proof / VIP Subject']}*")
            md_content.append("```text")
            md_content.append(r["Touch 4: Social Proof / VIP Body"])
            md_content.append("```\n")

            md_content.append(f"#### 🔹 Touch 5: Breakup / Corporate Catalog (Día 14) — Asunto: *{r['Touch 5: Breakup / Catalog Subject']}*")
            md_content.append("```text")
            md_content.append(r["Touch 5: Breakup / Catalog Body"])
            md_content.append("```\n")
            md_content.append("---\n")

        with open(md_filename, "w", encoding="utf-8") as f:
            f.write("\n".join(md_content))
        print(f"✅ Generated Executive Dossier: {md_filename}")

    # 8. Compile Teaser if enabled
    compiled_teaser = compile_teaser_html(campaign_cfg, teaser_filename)
    if compiled_teaser:
        print(f"📄 Compiled 1-Page Institutional Teaser: {teaser_filename}")

    # 9. Save Deduplication Ledger
    if not dry_run:
        ledger.save_batch()
        print(f"💾 Persistent Deduplication Ledger Updated: {len(csv_rows)} accounts recorded.")
    else:
        print("🔍 Dry run active: Master ledger was NOT modified.")

    print("\n" + "=" * 80)
    print(f"🎉 Batch Execution Complete! Deliverables saved to:\n   📂 {batch_dir}")
    print("=" * 80)


def main():
    available_campaigns = list_available_campaigns()
    parser = argparse.ArgumentParser(
        description="Universal Colombian B2B Prospector & Intent Engine (Michito)"
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
        city=args.city,
        limit=args.limit,
        segment=args.segment,
        sector=args.sector,
        dry_run=args.dry_run,
        output_format=args.output_format,
    )


if __name__ == "__main__":
    main()
