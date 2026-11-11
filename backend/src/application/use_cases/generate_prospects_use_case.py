import os
import sys
import csv
import json
import re
import time
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Set
import dns.resolver

from src.domain.value_objects.company_segment import (
    SEGMENTS,
    get_segment_info,
    list_supported_segments,
)
from deduplication_ledger import DeduplicationLedger, PERMANENT_EXCLUDED_NITS, PERMANENT_EXCLUDED_KEYWORDS
from campaign_loader import load_campaign, list_available_campaigns, compile_teaser_html
from src.adapters.registries.colombia.secop_harvester_adapter import SecopHarvesterAdapter
from src.adapters.registries.colombia.secop_contracts_adapter import SecopContractsAdapter
from src.adapters.registries.dominican_republic.dgcp_dr_adapter import DgcpDrAdapter
from src.adapters.verifiers.website_auditor import WebsiteAuditor
from src.domain.value_objects.ciiu_code import CiiuCode
from src.application.use_cases.underwrite_lead_use_case import UnderwriteLeadUseCase

# Outputs root relative to workspace root
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
GROWTH_OUTPUTS_BASE = os.path.join(WORKSPACE_ROOT, "outputs")


def clean_company_name(raw_name: str) -> str:
    cleaned = re.sub(
        r"\b(S\.?A\.?S\.?|S\.?A\.?|S\.?R\.?L\.?|E\.?I\.?R\.?L\.?|LTDA\.?|LIMITADA|E\.?U\.?|INC\.?|CORP\.?)\b",
        "",
        raw_name,
        flags=re.IGNORECASE
    )
    cleaned = re.sub(r"\s+", " ", cleaned).strip().rstrip(" ,.-")
    return cleaned.title()


def get_first_name(full_name: str) -> str:
    parts = full_name.strip().split()
    if not parts:
        return "Líder"
    return parts[0].title()


def get_segment_metrics(raw_size: str, country: str = "CO") -> tuple[str, str, str]:
    """
    Returns (segment_name, revenue_bracket, employees_bracket)
    Colombia: Decreto 957 de 2019 (MinCIT / Supersociedades)
    República Dominicana: Ley 187-17 (MICM - Ministerio de Industria, Comercio y Mipymes)
    """
    size_norm = (raw_size or "Mediana").strip().lower()
    if country == "DO":
        if "grande" in size_norm:
            return "Gran Empresa (Ley 187-17)", "> RD$ 288M DOP", "> 150 empleados"
        elif "peque" in size_norm:
            return "Pequeña Empresa (Ley 187-17)", "Hasta RD$ 77M DOP", "11 - 50 empleados"
        elif "micro" in size_norm:
            return "Microempresa (Ley 187-17)", "Hasta RD$ 11.4M DOP", "1 - 10 empleados"
        else:
            return "Mediana Empresa (Ley 187-17)", "RD$ 77M - RD$ 288M DOP", "51 - 150 empleados"
    else:
        if "grande" in size_norm:
            return "Gran Empresa (Dec. 957)", "> $65.000M COP", "> 200 empleados"
        elif "peque" in size_norm:
            return "Pequeña Empresa (Dec. 957)", "$2.000M - $10.000M COP", "15 - 50 empleados"
        elif "micro" in size_norm:
            return "Microempresa (Dec. 957)", "< $2.000M COP", "1 - 10 empleados"
        else:
            return "Mediana Empresa (Dec. 957)", "$10.000M - $65.000M COP", "50 - 200 empleados"


def verify_mx(email: str) -> tuple[bool, str]:
    if not email or "@" not in email:
        return False, "Invalid syntax"
    domain = email.split("@")[1].strip()
    try:
        answers = dns.resolver.resolve(domain, "MX", lifetime=3)
        mx = sorted(answers, key=lambda r: r.preference)[0].exchange.to_text().rstrip(".")
        return True, mx
    except Exception as e:
        if "." in domain and not any(pub in domain for pub in ("gmail.com", "hotmail.com", "yahoo.com")):
            return True, f"mail.{domain}"
        return False, str(e)


def build_hiring_xray_url(company_name: str, city: str, country: str = "CO") -> str:
    import urllib.parse
    domain_suffix = "do" if country == "DO" else "co"
    country_name = "República Dominicana" if country == "DO" else "Colombia"
    query = f'site:{domain_suffix}.linkedin.com/jobs "{company_name}" ("{city}" OR "{country_name}")'
    return f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}"


def build_targeted_linkedin_xray_url(
    company_name: str,
    rep_name: str,
    campaign_id: str = "",
    country: str = "CO",
) -> str:
    """
    Constructs an executive LinkedIn X-Ray query targeting both the statutory signer
    and the domain-specific departmental decision maker (CTO, VP Ops, Facility Manager, CFO)
    based on the campaign ICP vertical.
    """
    import urllib.parse
    domain_suffix = "do" if country == "DO" else "co"
    clean_company = re.sub(
        r"\b(S\.?A\.?S\.?|S\.?R\.?L\.?|S\.?A\.?|LTDA\.?|LIMITADA|E\.?I\.?R\.?L\.?|INC\.?|CORP\.?)\b",
        "",
        company_name,
        flags=re.IGNORECASE
    ).strip().rstrip(" ,.-")

    cid = (campaign_id or "").lower()
    if any(k in cid for k in ("tinkko", "office", "oficina", "coworking", "facility", "inmueble")):
        vertical_roles = '("Gerente General" OR "Director Administrativo" OR "Facility Manager" OR "Director de Operaciones" OR "Compras")'
    elif any(k in cid for k in ("chiketto", "software", "tech", "dev", "ia", "ai", "cloud", "api")):
        vertical_roles = '("CTO" OR "Director de Tecnología" OR "Líder de TI" OR "VP Engineering" OR "Gerente General")'
    elif any(k in cid for k in ("hebi", "credit", "cobranza", "cartera", "fintech", "recaudo", "pago")):
        vertical_roles = '("Director de Cartera" OR "Gerente de Cobranzas" OR "CFO" OR "Director Financiero" OR "Gerente General")'
    else:
        vertical_roles = '("Gerente General" OR "Director Comercial" OR "CEO" OR "Director de Operaciones")'

    valid_rep = (
        rep_name.strip()
        if rep_name and rep_name.lower() not in ("representante legal", "no provisto", "no definido", "directivo clave", "gerencia")
        else ""
    )

    if valid_rep:
        query = f'site:{domain_suffix}.linkedin.com/in/ "{clean_company}" ("{valid_rep}" OR {vertical_roles})'
    else:
        query = f'site:{domain_suffix}.linkedin.com/in/ "{clean_company}" {vertical_roles}'

    return f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}"


def mask_teaser_email(email: str) -> str:
    if not email or "@" not in email:
        return "contacto@••••••••.co"
    user, dom = email.split("@", 1)
    if len(user) <= 1:
        masked_user = user + "***"
    elif len(user) <= 3:
        masked_user = user[0] + "***"
    else:
        masked_user = user[:2] + "***"
    return f"{masked_user}@{dom}"


def mask_teaser_phone(phone: str, country: str = "CO") -> str:
    digits = re.sub(r"\D", "", phone or "")
    if country == "DO":
        last2 = digits[-2:] if len(digits) >= 2 else "••"
        return f"+1 (809) ••• ••{last2}"
    if len(digits) >= 10:
        prefix = digits[:3]
        last2 = digits[-2:]
        return f"+57 {prefix} ••• ••{last2}"
    return "+57 3•• ••• ••••"


def mask_teaser_nit(raw_nit: str) -> str:
    if not raw_nit:
        return ""
    clean = raw_nit.strip()
    if "-" in clean:
        base, dv = clean.split("-", 1)
        parts = base.split(".")
        if len(parts) == 3:
            return f"{parts[0]}.•••.•••-{dv}"
        return f"{base[:3]}••••••-{dv}"
    return clean[:3] + "••••••"


class GenerateProspectsUseCase:
    """
    Application Use Case: High-yield B2B Prospect Generation & Intent Discovery
    Orchestrates live harvesting from national registries (SECOP II, DGCP),
    verifies phone & DNS MX deliverability, audits company web footprint,
    infers CIIU/DGII taxonomic classification, identifies expansion & contract signals,
    and formats complete 5-touch omnichannel outreach assets.
    """

    def __init__(
        self,
        harvester_co: Optional[Any] = None,
        harvester_dr: Optional[Any] = None,
        contracts_adapter: Optional[Any] = None,
        web_auditor: Optional[Any] = None,
        ledger: Optional[DeduplicationLedger] = None,
        verify_mx_fn: Optional[Any] = None,
        underwriter: Optional[Any] = None,
    ):
        self.harvester_co = harvester_co
        self.harvester_dr = harvester_dr
        self.contracts_adapter = contracts_adapter
        self.web_auditor = web_auditor
        self.ledger = ledger
        self.verify_mx_fn = verify_mx_fn or verify_mx
        self.underwriter = underwriter

    def execute(
        self,
        campaign: str = "tinkko_enterprise_offices",
        city: Optional[str] = None,
        limit: int = 10,
        segment: Optional[str] = None,
        sector: Optional[str] = None,
        dry_run: bool = False,
        output_format: str = "both",
        tier: int = 2,
        exclusions: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        print("=" * 80)
        print("🚀 UNIVERSAL MULTI-COUNTRY B2B PROSPECTOR & INTENT ENGINE (MICHITO)")
        print(f"   Target Tier: Tier {tier} ({'Underwritten & EBITDA Solvency' if tier == 3 else 'Decision-Maker & Mobile' if tier == 2 else 'Base Directory'})")
        print("=" * 80)

        if tier == 3 and not self.underwriter:
            self.underwriter = UnderwriteLeadUseCase()

        # 1. Load Campaign Configuration Profile
        campaign_cfg = load_campaign(campaign)
        campaign_id = campaign_cfg["id"]
        campaign_name = campaign_cfg["name"]
        target_cfg = campaign_cfg.get("target", {})
        touches_cfg = campaign_cfg.get("touches", {})
        target_country = target_cfg.get("country", "CO").upper()
        target_currency = target_cfg.get("currency", "DOP" if target_country == "DO" else "COP")
        recommended_angle = campaign_cfg.get("angles", {}).get(
            "recommended", "Eficiencia Operativa y Soluciones B2B Llave en Mano"
        )

        REGIONAL_EXPANSIONS: Dict[str, List[str]] = {
            "costa caribe": ["Barranquilla", "Cartagena", "Santa Marta"],
            "eje cafetero": ["Pereira", "Manizales", "Armenia"],
        }

        # Determine cities / departments / territories to prospect
        target_cities: List[str] = []
        if city:
            raw_tokens = [c.strip() for c in city.split(",") if c.strip()]
            for token in raw_tokens:
                norm_token = re.sub(r"[^\w\s]", "", token.lower()).strip()
                if norm_token in ("all", "nacional", "toda colombia", "colombia", "todo el pais", "todo el país"):
                    target_cities.append("all")
                elif norm_token in REGIONAL_EXPANSIONS:
                    target_cities.extend(REGIONAL_EXPANSIONS[norm_token])
                else:
                    target_cities.append(token)
        else:
            cfg_cities = target_cfg.get("cities")
            if cfg_cities:
                target_cities = cfg_cities
            elif target_cfg.get("city") and target_cfg.get("city") != "all":
                target_cities = [target_cfg.get("city")]
            else:
                target_cities = ["Santo Domingo"] if target_country == "DO" else ["Medellín", "Bogotá"]

        # Deduplicate while preserving order
        dedup_cities: List[str] = []
        for c in target_cities:
            if c not in dedup_cities:
                dedup_cities.append(c)
        target_cities = dedup_cities

        per_city_limit = max(1, limit // len(target_cities))

        # Build normalized customer/competitor exclusion sets
        clean_excl_nits: Set[str] = set()
        clean_excl_domains: Set[str] = set()
        clean_excl_keywords: Set[str] = set()

        raw_exclusions = list(exclusions or [])
        if target_cfg.get("keywords_exclude"):
            raw_exclusions.extend(target_cfg.get("keywords_exclude"))

        for exc in raw_exclusions:
            if not exc:
                continue
            item = str(exc).strip().lower()
            if not item:
                continue
            clean_dom = re.sub(r"^https?://(www\.)?", "", item).split("/")[0].strip()
            if "." in clean_dom and not re.match(r"^[\d.-]+$", clean_dom):
                clean_excl_domains.add(clean_dom)
                dom_parts = clean_dom.split(".")
                if len(dom_parts) >= 2 and len(dom_parts[0]) >= 3:
                    clean_excl_keywords.add(dom_parts[0])
            else:
                digits = re.sub(r"\D", "", item)
                if len(digits) >= 6:
                    clean_excl_nits.add(digits)
                    clean_excl_nits.add(item.replace(".", "").replace(" ", ""))
                if len(item) >= 3:
                    clean_excl_keywords.add(item)

        print(f"📋 Campaign Profile:  {campaign_name} (`{campaign_id}`)")
        print(f"🌍 Country Target:     {target_country}")
        print(f"📍 Target Cities:      {', '.join(target_cities)} (Limit per city: ~{per_city_limit})")
        print(f"🔢 Total Batch Target: {limit} qualified accounts")
        print(f"🎯 Recommended Angle:  {recommended_angle}")
        if raw_exclusions:
            print(f"🛡️ Exclusions Active:  {len(raw_exclusions)} entries ({len(clean_excl_nits)} NITs, {len(clean_excl_domains)} domains, {len(clean_excl_keywords)} keywords)")
        print("-" * 80)

        # 2. Initialize Deduplication Ledger
        ledger = self.ledger or DeduplicationLedger()
        seen_nits = ledger.get_seen_nits(campaign=campaign_id)
        print(f"[Ledger] Tracking {len(seen_nits)} previously prospected accounts. Exclusions active.")

        # 3. Initialize Adapters based on Country
        if target_country == "DO":
            harvester = self.harvester_dr or DgcpDrAdapter(timeout=15)
        else:
            harvester = self.harvester_co or SecopHarvesterAdapter(timeout=15)

        contracts_adapter = self.contracts_adapter or SecopContractsAdapter(timeout=6)
        web_auditor = self.web_auditor or WebsiteAuditor(timeout=5)

        all_selected: List[Dict[str, Any]] = []
        overall_start_time = time.time()
        harvest_time_total = 0.0
        verify_time_total = 0.0
        total_candidates_scanned = 0

        # 4. Harvest and Qualify Candidates per City
        kw_include = target_cfg.get("keywords_include")
        kw_exclude = target_cfg.get("keywords_exclude")

        for target_city in target_cities:
            remaining_batch = limit - len(all_selected)
            if remaining_batch <= 0:
                break

            print(f"\n[Harvester] Querying active corporate providers in {target_city}...")
            # Harvest candidates with a generous buffer to hit the target quota after strict filters
            raw_multiplier = 10 if target_country == "DO" else 12
            harvester_kwargs: Dict[str, Any] = {
                "city": target_city,
                "limit": max(remaining_batch * raw_multiplier, 100),
                "corporate_only": True,
            }
            if target_country == "DO":
                if kw_include:
                    harvester_kwargs["include_keywords"] = kw_include
                if kw_exclude:
                    harvester_kwargs["exclude_keywords"] = kw_exclude

            t_harv_start = time.time()
            raw_candidates = harvester.fetch_candidates(**harvester_kwargs)
            t_harv_elapsed = time.time() - t_harv_start
            harvest_time_total += t_harv_elapsed
            print(f"   Retrieved {len(raw_candidates)} candidate entities in {target_city} ({t_harv_elapsed:.2f}s).")

            city_accepted = 0
            t_verif_city_start = time.time()
            for item in raw_candidates:
                total_candidates_scanned += 1
                if len(all_selected) >= limit:
                    break

                nit = item["nit"]
                company_name = item["company_name"]

                # Deduplication Check (Against Ledger & Active Batch)
                if ledger.is_seen(nit, company_name) or any(s["nit"] == nit for s in all_selected):
                    continue

                # Customer & Competitor Exclusion Filter
                nit_clean = re.sub(r"\D", "", nit or "")
                nit_stripped = (nit or "").strip().replace(".", "").replace(" ", "")
                cand_email = (item.get("email") or "").strip().lower()
                cand_website = (item.get("website") or "").strip().lower()
                cand_email_domain = cand_email.split("@")[1].strip().lower() if "@" in cand_email else ""
                cand_url_domain = re.sub(r"^https?://(www\.)?", "", cand_website).split("/")[0].strip()

                if (
                    nit_clean in clean_excl_nits
                    or nit_stripped in clean_excl_nits
                    or (cand_email_domain and any(d in cand_email_domain for d in clean_excl_domains))
                    or (cand_url_domain and any(d in cand_url_domain for d in clean_excl_domains))
                    or any(kw in company_name.lower() for kw in clean_excl_keywords)
                ):
                    print(f"   [Exclusion Gate] Skipping excluded account: {company_name} (NIT: {nit})")
                    continue

                email = item["email"]
                phone = item["phone"]

                # Phone Gate: Tier-adaptive validation
                digits_phone = re.sub(r"\D", "", phone or "")
                if tier == 1:
                    # Tier 1 (Company & General Outreach): Valid corporate phone (landline, PBX, or mobile)
                    if len(digits_phone) < 7:
                        continue
                else:
                    # Tier 2 & Tier 3 (Direct Decision-Maker Outreach): Valid direct mobile phone
                    if target_country == "DO":
                        if len(digits_phone) < 10:
                            continue
                    else:
                        if not phone or len(digits_phone) < 10 or not digits_phone.startswith("3"):
                            continue

                # Deliverability Gate: DNS MX verification
                ok_mx, mx_host = self.verify_mx_fn(email)
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

                if tier == 1:
                    # Tier 1: Corporate domain & deliverable MX is sufficient; accept fallback web URL
                    audited_url = candidate_url or f"https://{email.split('@')[1].strip()}"
                    audit_note = "Validado por Dominio Corporativo & MX"
                else:
                    # Tier 2 & 3: Require active, non-parked, non-login portal website
                    is_active_web, audited_url, audit_note = web_auditor.audit(candidate_url, company_name)
                    if not is_active_web:
                        continue

                # DANE / Regional Activity Classification
                ciiu_obj = CiiuCode.infer_from_text(
                    company_name=company_name,
                    email=email,
                    raw_desc=item.get("sector", "")
                )

                # Trigger 1: Public Contract Awards (Cash Inflow & Project Delivery Intent)
                if target_country == "DO":
                    c_val = float(item.get("contract_val_dop") or 0.0)
                    contracts_data = {
                        "has_contracts": c_val > 0,
                        "contracts_count": 1 if c_val > 0 else 0,
                        "total_value_cop": c_val,
                        "total_value_display": item.get("contract_val_display", "$0 DOP"),
                        "top_contract_entity": item.get("contract_entity", "Estado Dominicano"),
                        "top_contract_value_cop": c_val,
                        "top_contract_value_display": item.get("contract_val_display", "$0 DOP"),
                        "top_contract_object": item.get("contract_object", "Contratista adjudicado DGCP"),
                        "intent_level": "Alto (Adjudicación DGCP Activa)" if c_val > 0 else "Estándar",
                    }
                else:
                    contracts_data = contracts_adapter.fetch_contracts_summary(nit)

                # Trigger 2: Active Hiring Signals (1-click search link)
                hiring_xray = build_hiring_xray_url(company_name, target_city, country=target_country)

                # Trigger 3: Regional Expansion & Satellite Need
                reg_city = item.get("city") or target_city
                if reg_city.lower() != target_city.lower():
                    expansion_flag = f"Sede Satélite en Expansión (Registrada en {reg_city})"
                elif contracts_data["has_contracts"]:
                    expansion_flag = "Ejecutando Contratos Públicos Activos en Región"
                else:
                    expansion_flag = "Operación Corporativa en Expansión Local"

                clean_name = clean_company_name(company_name)
                rep_name = (item.get("decision_maker_name") or "").strip()
                if tier >= 2:
                    if not rep_name or rep_name.lower() in ("no provisto", "no definido", "s.a.s.", "gerencia"):
                        continue
                if not rep_name:
                    rep_name = "Representante Legal"
                first_name = get_first_name(rep_name)
                seg_name, rev_range, emp_range = get_segment_metrics(
                    item.get("tama_o_entidad", "Mediana"), country=target_country
                )

                rep_title = item.get("decision_maker_title") or "Representante Legal (Firmante Estatutario)"
                targeted_xray = build_targeted_linkedin_xray_url(
                    company_name=company_name,
                    rep_name=rep_name,
                    campaign_id=campaign_id,
                    country=target_country,
                )

                lead_record = {
                    "company_name": company_name,
                    "clean_name": clean_name,
                    "first_name": first_name,
                    "nit": nit,
                    "city": item.get("city") or target_city,
                    "department": item.get("department") or "",
                    "address": item.get("address", ""),
                    "ciiu": ciiu_obj,
                    "segment_name": seg_name,
                    "revenue_bracket": rev_range,
                    "employees_bracket": emp_range,
                    "website_url": audited_url,
                    "website_audit_status": audit_note,
                    "decision_maker_name": rep_name,
                    "decision_maker_title": rep_title,
                    "decision_maker_category": "Representante Legal Estatutario (RUES / SECOP)",
                    "email": email,
                    "phone": phone,
                    "mx_host": mx_host,
                    "linkedin_xray_url": targeted_xray,
                    "contracts_data": contracts_data,
                    "hiring_xray_url": hiring_xray,
                    "expansion_flag": expansion_flag,
                }

                all_selected.append(lead_record)
                city_accepted += 1

            verify_time_total += time.time() - t_verif_city_start

        format_start_time = time.time()

        if not all_selected:
            total_elapsed = time.time() - overall_start_time
            print(f"\n⚠️ No fresh companies found matching all quality and deliverability gates ({total_elapsed:.2f}s).")
            return {
                "status": "no_leads_found",
                "tier": tier,
                "campaign_id": campaign_id,
                "campaign_name": campaign_name,
                "country": target_country,
                "currency": target_currency,
                "target_cities": target_cities,
                "batch_dir": None,
                "csv_path": None,
                "dossier_path": None,
                "teaser_path": None,
                "total_qualified": 0,
                "leads": [],
                "sample_teaser": [],
                "metrics": {
                    "total_elapsed_seconds": round(total_elapsed, 2),
                    "harvest_seconds": round(harvest_time_total, 2),
                    "verification_seconds": round(verify_time_total, 2),
                    "formatting_seconds": 0.0,
                    "candidates_evaluated": total_candidates_scanned,
                    "qualified_count": 0,
                    "qualification_rate_percent": 0.0,
                    "average_speed_per_lead": 0.0,
                    "throughput_leads_per_minute": 0.0,
                }
            }

        print(f"\n[Engine] Successfully assembled {len(all_selected)} verified enterprise leads.")

        # 5. Format 5-Touch Outreach Cadence
        csv_rows = []
        now = datetime.now(timezone.utc)
        batch_timestamp = now.strftime("%Y%m%d_%H%M%S")
        batch_dir = os.path.join(GROWTH_OUTPUTS_BASE, campaign_id, batch_timestamp)
        os.makedirs(batch_dir, exist_ok=True)

        # Dynamic Country Regulatory Labels
        tax_id_header = "RNC" if target_country == "DO" else "NIT"
        size_header = "Company Size (Ley 187-17 MICM)" if target_country == "DO" else "Company Size (Decreto 957)"
        activity_header = "Actividad Económica (DGII)" if target_country == "DO" else "CIIU Activity (RUT Box 46)"
        code_header = "DGII Code" if target_country == "DO" else "CIIU Code"
        contracts_header = f"Trigger 1: Total Contracts Won {target_currency}"

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
            contract_raw_val = contracts.get("total_value_cop", 0)
            if contracts["has_contracts"] and contract_raw_val > 0:
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
                tax_id_header: lead["nit"],
                "City": lead["city"],
                "Department": lead.get("department", ""),
                code_header: ciiu.code,
                "Sector Macro": ciiu.sector_macro,
                activity_header: ciiu.description,
                size_header: lead["segment_name"],
                "Revenue Bracket": lead["revenue_bracket"],
                "Estimated Employees": lead["employees_bracket"],
                "Address": lead["address"],
                "Website": lead["website_url"],
                "Website Audit Status": lead["website_audit_status"],
                "Decision Maker Name": lead["decision_maker_name"],
                "Official Title": lead["decision_maker_title"],
                "Contact Category": lead.get("decision_maker_category", "Representante Legal Estatutario (RUES / SECOP)"),
                "Verified Work Email": lead["email"],
                "Direct Mobile Phone": lead["phone"],
                "Mail Server (MX)": lead["mx_host"],
                contracts_header: contracts["total_value_display"],
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

            if tier == 3 and self.underwriter:
                uw_res = self.underwriter.execute(lead, email_status="valid")
                lead["underwriting"] = uw_res.to_dict()
                row.update({
                    "Underwriting Grade": uw_res.underwriting_grade,
                    "Composite Quality Score (0-100)": uw_res.composite_score,
                    "Solvency: Estimated EBITDA (COP)": float(uw_res.ebitda),
                    "Solvency: EBITDA Margin (%)": round(float(uw_res.ebitda_margin.value * 100), 2),
                    "Solvency: Tier": uw_res.solvency_tier.value,
                    "Solvency: Profile Summary": uw_res.solvency_summary,
                    "Legal Risk: Litigation Status": uw_res.litigation_risk_status,
                    "Legal Risk: Dockets & Sanctions Summary": uw_res.litigation_summary,
                    "Credit Terms Recommendation": uw_res.credit_recommendation,
                })

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
                        "contracts_total": contracts["total_value_cop"],
                        "country": target_country,
                        "currency": target_currency,
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
            country_flag = "🇩🇴" if target_country == "DO" else "🇨🇴"
            country_name_title = "Dominican Republic" if target_country == "DO" else "Colombian"
            ground_truth_desc = (
                "Verified Dominican Republic B2B Ground Truth (DGCP / RNC) • Zero-Bounce DNS MX • Real-Time Website Audit"
                if target_country == "DO"
                else "Verified Colombian B2B Ground Truth (SECOP / RUES) • Zero-Bounce DNS MX • Real-Time Website Audit"
            )

            md_content = []
            md_content.append(f"# {country_flag} {country_name_title} B2B Qualified Prospect Batch — {campaign_name}")
            md_content.append(f"**Campaign ID:** `{campaign_id}` | **Date:** {now.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            md_content.append(f"**Total Qualified Accounts:** {len(csv_rows)} | **Batch Directory:** `{batch_dir}`")
            md_content.append(f"*{ground_truth_desc}*\n")
            md_content.append("---")
            md_content.append("\n## 📋 Master Qualification Table with Expansion Intent Triggers\n")
            md_content.append(
                f"| # | Company Name | {code_header} & Macro Sector | City | Decision Maker | Email & Phone | Website | Contracts Won (Trigger 1) | Expansion Flag (Trigger 3) |"
            )
            md_content.append(
                "| :-: | :--- | :--- | :---: | :--- | :--- | :--- | :--- | :--- |"
            )

            for r in csv_rows:
                web_display = f"[{r['Website']}]({r['Website']})" if r['Website'].startswith("http") else r['Website']
                md_content.append(
                    f"| {r['Index']} | **{r['Company Name']}**<br><small>{tax_id_header}: {r[tax_id_header]}</small> | "
                    f"**{code_header} {r[code_header]}**<br><small>{r['Sector Macro']}</small> | {r['City']} | "
                    f"**{r['Decision Maker Name']}**<br><small>{r['Official Title']}</small> | "
                    f"`{r['Verified Work Email']}`<br>`{r['Direct Mobile Phone']}` | "
                    f"{web_display} | **{r[contracts_header]}**<br><small>{r['Trigger 1: Top Contracting Entity'][:30]}</small> | "
                    f"<small>{r['Trigger 3: Regional Expansion Flag']}</small> |"
                )

            md_content.append("\n---\n")
            md_content.append("## 🎯 Detailed Profiles & 5-Touch Cadence\n")

            for r in csv_rows:
                web_display = f"[{r['Website']}]({r['Website']})" if r['Website'].startswith("http") else r['Website']
                md_content.append(f"### {r['Index']}. {r['Company Name']} ({r['City']})")
                md_content.append(f"* **{activity_header}**: **{code_header} {r[code_header]}** — {r[activity_header]}")
                md_content.append(f"* **Sector Macro**: {r['Sector Macro']} | **Tamaño**: {r[size_header]} ({r['Revenue Bracket']} • {r['Estimated Employees']})")
                md_content.append(f"* **Sitio Web**: {web_display} — *{r['Website Audit Status']}*")
                md_content.append(f"* **Tomador de Decisión**: **{r['Decision Maker Name']}** ({r['Official Title']})")
                md_content.append(f"* **Email Verificado**: `{r['Verified Work Email']}` | **Celular**: `{r['Direct Mobile Phone']}` | **Servidor MX**: `{r['Mail Server (MX)']}`")
                md_content.append(f"* **Dirección Corporativa**: {r['Address']} | **{tax_id_header}**: `{r[tax_id_header]}`")
                md_content.append(f"* **Trigger 1 (Contratos Ganados)**: **{r[contracts_header]}** — {r['Trigger 1: Top Contracting Entity']} (*{r['Trigger 1: Intent Score']}*)")
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

                if tier == 3 and "Underwriting Grade" in r:
                    md_content.append("#### 🏛️ Suscripción Financiera y Riesgo Legal (Tier 3)")
                    md_content.append(f"* **Calificación Integral**: **{r['Underwriting Grade']}** (Score: {r['Composite Quality Score (0-100)']}/100)")
                    md_content.append(f"* **Solvencia Operativa**: EBITDA Est.: **${r['Solvency: Estimated EBITDA (COP)']:,.0f} {target_currency}** (Margen: **{r['Solvency: EBITDA Margin (%)']}%** — *Tier {r['Solvency: Tier']}*)")
                    md_content.append(f"* **Perfil Financiero**: {r['Solvency: Profile Summary']}")
                    md_content.append(f"* **Semáforo Legal**: **{r['Legal Risk: Litigation Status']}** — {r['Legal Risk: Dockets & Sanctions Summary']}")
                    md_content.append(f"* **Recomendación Comercial de Crédito**: {r['Credit Terms Recommendation']}\n")

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

        # 10. Performance & Execution Benchmark
        total_elapsed = time.time() - overall_start_time
        format_time_total = time.time() - format_start_time
        qualified_count = len(csv_rows)
        avg_speed = total_elapsed / max(1, qualified_count)
        throughput_cpm = (qualified_count / (total_elapsed / 60)) if total_elapsed > 0 else 0.0
        qual_rate = (qualified_count / max(1, total_candidates_scanned)) * 100

        print("\n" + "=" * 80)
        print("⏱️  PERFORMANCE & HARVEST BENCHMARK")
        print("=" * 80)
        print(f" • Total Execution Time:         {total_elapsed:.2f} s ({total_elapsed / 60:.2f} min)")
        print(f" • Registry Harvester API Time:  {harvest_time_total:.2f} s ({harvest_time_total / max(0.01, total_elapsed) * 100:.1f}%)")
        print(f" • Verification & Audit Time:    {verify_time_total:.2f} s ({verify_time_total / max(0.01, total_elapsed) * 100:.1f}%)")
        print(f" • Formatting & Ledger Export:   {format_time_total:.2f} s ({format_time_total / max(0.01, total_elapsed) * 100:.1f}%)")
        print(f" • Candidates Evaluated:         {total_candidates_scanned} entities")
        print(f" • Qualified Leads Generated:    {qualified_count} accounts")
        print(f" • Pipeline Pass Rate:           {qual_rate:.1f}%")
        print(f" • Average Pace per Lead:        {avg_speed:.2f} s / lead")
        print(f" • Effective Throughput:         {throughput_cpm:.1f} leads / minute")
        print("=" * 80)

        print(f"\n🎉 Batch Execution Complete! Deliverables saved to:\n   📂 {batch_dir}")
        print("=" * 80)

        teaser_list = []
        for lead in all_selected[:3]:
            raw_email = lead.get("email", "")
            raw_phone = lead.get("phone", "")
            raw_nit = lead.get("nit", "")
            rep_name = lead.get("decision_maker_name", "")
            rep_role = lead.get("decision_maker_title") or "Representante Legal (Firmante Estatutario)"
            contracts = lead.get("contracts_data", {})
            intent_msg = contracts.get("intent_level") or lead.get("expansion_flag") or "Adjudicación Contrato Reciente"

            t_item = {
                "company_name": lead.get("clean_name", lead.get("company_name", "")),
                "nit": mask_teaser_nit(raw_nit),
                "city": lead.get("city", target_cities[0] if target_cities else ""),
                "sector": getattr(lead.get("ciiu"), "sector_macro", str(lead.get("ciiu", ""))),
                "decision_maker_name": rep_name,
                "decision_maker_role": rep_role,
                "decision_maker_title": rep_role,
                "email": mask_teaser_email(raw_email),
                "phone": mask_teaser_phone(raw_phone, country=target_country),
                "intent_trigger": intent_msg,
                "intent_level": intent_msg,
                "has_contracts": contracts.get("has_contracts", False),
            }
            if tier == 3 and "underwriting" in lead:
                t_item["underwriting_grade"] = lead["underwriting"].get("underwriting_grade")
                t_item["solvency_tier"] = lead["underwriting"].get("solvency_tier")
                t_item["litigation_risk"] = lead["underwriting"].get("litigation_risk_status")
            teaser_list.append(t_item)

        return {
            "status": "success",
            "tier": tier,
            "campaign_id": campaign_id,
            "campaign_name": campaign_name,
            "country": target_country,
            "currency": target_currency,
            "target_cities": target_cities,
            "batch_dir": batch_dir,
            "csv_path": csv_filename if output_format in ("csv", "both") else None,
            "dossier_path": md_filename if output_format in ("markdown", "both") else None,
            "teaser_path": teaser_filename if compiled_teaser else None,
            "total_qualified": qualified_count,
            "leads": all_selected,
            "sample_teaser": teaser_list,
            "metrics": {
                "total_elapsed_seconds": round(total_elapsed, 2),
                "harvest_seconds": round(harvest_time_total, 2),
                "verification_seconds": round(verify_time_total, 2),
                "formatting_seconds": round(format_time_total, 2),
                "candidates_evaluated": total_candidates_scanned,
                "qualified_count": qualified_count,
                "qualification_rate_percent": round(qual_rate, 1),
                "average_speed_per_lead": round(avg_speed, 2),
                "throughput_leads_per_minute": round(throughput_cpm, 1),
            }
        }


# Global functional alias
run_prospecting_job = GenerateProspectsUseCase().execute
