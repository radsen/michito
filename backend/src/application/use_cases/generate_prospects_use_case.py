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
from campaign_loader import load_campaign, list_available_campaigns, compile_teaser_html, DEFAULT_ROLES
from src.domain.entities.universal_prospecting_request import UniversalProspectingRequest, LocationAllocation
from src.application.services.dynamic_cadence_generator import generate_dynamic_touches
from src.adapters.registries.colombia.secop_harvester_adapter import SecopHarvesterAdapter
from src.adapters.registries.colombia.secop_contracts_adapter import SecopContractsAdapter
from src.adapters.registries.dominican_republic.dgcp_dr_adapter import DgcpDrAdapter
from src.adapters.registries.ecuador.sercop_ecuador_adapter import SercopEcuadorAdapter
from src.adapters.verifiers.website_auditor import WebsiteAuditor
from src.adapters.export.excel_dossier_adapter import ExcelDossierAdapter
from src.adapters.export.pdf_dossier_adapter import PdfDossierAdapter
from src.domain.value_objects.ciiu_code import CiiuCode
from src.application.use_cases.underwrite_lead_use_case import UnderwriteLeadUseCase
from src.application.ports.mailbox_verifier_port import MailboxVerifierPort
from src.adapters.verifiers.socket_smtp_verifier_adapter import SocketSmtpVerifierAdapter

# Outputs root relative to workspace root (canonical repo root outputs/)
_candidate_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
if os.path.exists(os.path.join(_candidate_root, "backend")):
    WORKSPACE_ROOT = _candidate_root
else:
    WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
GROWTH_OUTPUTS_BASE = os.path.join(WORKSPACE_ROOT, "outputs")


def clean_company_name(raw_name: str) -> str:
    cleaned = re.sub(
        r"\b(S\.?A\.?S\.?|S\.?A\.?|S\.?R\.?L\.?|E\.?I\.?R\.?L\.?|LTDA\.?|LIMITADA|E\.?U\.?|INC\.?|CORP\.?|C\.?A\.?)\b",
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
    Ecuador: COPCI / SuperCias (Superintendencia de Compañías)
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
    elif country == "EC":
        if "grande" in size_norm:
            return "Gran Empresa (SuperCias)", "> $5.000.000 USD", "> 200 empleados"
        elif "peque" in size_norm:
            return "Pequeña Empresa (SuperCias)", "$100.001 - $1.000.000 USD", "10 - 49 empleados"
        elif "micro" in size_norm:
            return "Microempresa (SuperCias)", "< $100.000 USD", "1 - 9 empleados"
        else:
            return "Mediana Empresa (SuperCias)", "$1.000.001 - $5.000.000 USD", "50 - 199 empleados"
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
    c_up = (country or "CO").upper()
    if c_up == "DO":
        domain_suffix = "do"
        country_name = "República Dominicana"
    elif c_up == "EC":
        domain_suffix = "ec"
        country_name = "Ecuador"
    else:
        domain_suffix = "co"
        country_name = "Colombia"
    query = f'site:{domain_suffix}.linkedin.com/jobs "{company_name}" ("{city}" OR "{country_name}")'
    return f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}"


def build_targeted_linkedin_xray_url(
    company_name: str,
    rep_name: str,
    campaign_id: str = "",
    country: str = "CO",
    target_roles: Optional[List[str]] = None,
) -> str:
    """
    Constructs an executive LinkedIn X-Ray query targeting both the statutory signer
    and the domain-specific departmental decision maker (CTO, VP Ops, Facility Manager, CFO)
    based on the campaign ICP vertical or explicitly supplied target roles.
    """
    import urllib.parse
    c_up = (country or "CO").upper()
    if c_up == "DO":
        domain_suffix = "do"
    elif c_up == "EC":
        domain_suffix = "ec"
    else:
        domain_suffix = "co"
    clean_company = re.sub(
        r"\b(S\.?A\.?S\.?|S\.?R\.?L\.?|S\.?A\.?|LTDA\.?|LIMITADA|E\.?I\.?R\.?L\.?|INC\.?|CORP\.?)\b",
        "",
        company_name,
        flags=re.IGNORECASE
    ).strip().rstrip(" ,.-")

    if target_roles and len(target_roles) > 0:
        roles_quoted = [f'"{r.strip()}"' for r in target_roles if r.strip()]
        vertical_roles = f"({' OR '.join(roles_quoted)})"
    else:
        cid = (campaign_id or "").lower()
        if any(k in cid for k in ("tinkko", "office", "oficina", "coworking", "facility", "inmueble")):
            vertical_roles = '("Gerente General" OR "Director Administrativo" OR "Facility Manager" OR "Director de Operaciones" OR "Compras")'
        elif any(k in cid for k in ("chiketto_school", "colegio", "escuela", "educa", "carnet", "school")):
            vertical_roles = '("Rector" OR "Rectora" OR "Director de Colegio" OR "Coordinador Administrativo" OR "Jefe de Compras")'
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
        clean_do = digits[1:] if digits.startswith("1") and len(digits) == 11 else digits
        last2 = clean_do[-2:] if len(clean_do) >= 2 else "••"
        return f"+1 (809) ••• ••{last2}"
    if country == "EC":
        clean_ec = digits[3:] if digits.startswith("593") and len(digits) >= 12 else digits
        last2 = clean_ec[-2:] if len(clean_ec) >= 2 else "••"
        return f"+593 9• ••• ••{last2}"
    if country == "CO":
        clean = digits[2:] if digits.startswith("57") and len(digits) >= 12 else digits
        last2 = clean[-2:] if len(clean) >= 2 else "••"
        if len(clean) == 10 and clean.startswith("3"):
            prefix = clean[:3]
            return f"+57 {prefix} ••• ••{last2}"
        elif len(clean) == 10 and clean.startswith("60"):
            prefix = clean[:3]
            return f"+57 ({prefix}) ••• ••{last2} (PBX)"
        elif len(clean) == 7:
            return f"+57 ••• ••{last2} (PBX)"
        elif len(clean) >= 7:
            return f"+57 {clean[:3]} ••• ••{last2}"
        return "+57 ••• ••• ••••"
    last2 = digits[-2:] if len(digits) >= 2 else "••"
    return f"+{digits[:3]} ••• ••{last2}" if len(digits) >= 5 else "••••••••••"


def mask_teaser_nit(raw_nit: str) -> str:
    if not raw_nit:
        return ""
    clean = raw_nit.strip()
    if len(clean) == 13 and clean.endswith("001"):
        return f"{clean[:4]}•••••••{clean[-2:]}"
    if "-" in clean:
        base, dv = clean.split("-", 1)
        parts = base.split(".")
        if len(parts) == 3:
            return f"{parts[0]}.•••.•••-{dv}"
        return f"{base[:3]}••••••-{dv}"
    return clean[:3] + "••••••"


def classify_phone(phone: str, country: str = "CO") -> Dict[str, Any]:
    """
    Transparently classifies and standardizes corporate contact phone numbers.
    Distinguishes direct corporate mobile lines (WhatsApp-enabled) from corporate
    landlines, PBX switchboards, and institutional reception lines without false claims.
    """
    digits = re.sub(r"\D", "", phone or "")
    if country == "CO":
        clean = digits[2:] if digits.startswith("57") and len(digits) >= 12 else digits
        if len(clean) == 10 and clean.startswith("3"):
            return {
                "raw": phone,
                "formatted": f"+57 {clean[:3]} {clean[3:6]} {clean[6:]}",
                "line_type": "Móvil Corporativo (WhatsApp)",
                "is_mobile": True,
                "whatsapp_url": f"https://wa.me/57{clean}",
                "whatsapp_display": f"+57 {clean[:3]} {clean[3:6]} {clean[6:]}",
            }
        elif len(clean) == 10 and clean.startswith("60"):
            return {
                "raw": phone,
                "formatted": f"+57 ({clean[:3]}) {clean[3:6]} {clean[6:]}",
                "line_type": "Línea Fija / Conmutador (PBX)",
                "is_mobile": False,
                "whatsapp_url": "",
                "whatsapp_display": "No aplica (Línea Fija PBX)",
            }
        elif len(clean) == 7:
            return {
                "raw": phone,
                "formatted": f"+57 {clean[:3]} {clean[3:]}",
                "line_type": "Línea Fija Local (PBX)",
                "is_mobile": False,
                "whatsapp_url": "",
                "whatsapp_display": "No aplica (Línea Fija)",
            }
        elif len(clean) >= 7:
            is_mob = clean.startswith("3")
            return {
                "raw": phone,
                "formatted": f"+57 {clean}",
                "line_type": "Móvil Corporativo (WhatsApp)" if is_mob else "Línea Corporativa (PBX)",
                "is_mobile": is_mob,
                "whatsapp_url": f"https://wa.me/57{clean}" if is_mob else "",
                "whatsapp_display": f"+57 {clean}" if is_mob else "No aplica (Línea Fija)",
            }
    elif country == "DO":
        clean = digits[1:] if digits.startswith("1") and len(digits) == 11 else digits
        is_mob = clean.startswith("829") or clean.startswith("849") or clean.startswith("809")
        formatted = f"+1 ({clean[:3]}) {clean[3:6]}-{clean[6:]}" if len(clean) == 10 else f"+1 {clean}"
        return {
            "raw": phone,
            "formatted": formatted,
            "line_type": "Móvil Corporativo (WhatsApp)" if is_mob else "Línea Corporativa / Centralita",
            "is_mobile": is_mob,
            "whatsapp_url": f"https://wa.me/1{clean}" if is_mob else "",
            "whatsapp_display": formatted if is_mob else "No aplica (Línea Fija)",
        }
    elif country == "EC":
        clean = digits[3:] if digits.startswith("593") and len(digits) >= 12 else digits
        if clean.startswith("0"):
            clean = clean[1:]
        is_mob = clean.startswith("9")
        formatted = f"+593 {clean[:2]} {clean[2:5]} {clean[5:]}" if len(clean) >= 9 else f"+593 {clean}"
        return {
            "raw": phone,
            "formatted": formatted,
            "line_type": "Móvil Corporativo (WhatsApp)" if is_mob else "Línea Fija / Centralita (PBX)",
            "is_mobile": is_mob,
            "whatsapp_url": f"https://wa.me/593{clean}" if is_mob else "",
            "whatsapp_display": formatted if is_mob else "No aplica (Línea Fija)",
        }

    is_mob = len(digits) >= 10 and digits.startswith("3")
    return {
        "raw": phone,
        "formatted": f"+{digits}" if digits else "",
        "line_type": "Móvil Corporativo (WhatsApp)" if is_mob else "Línea Corporativa",
        "is_mobile": is_mob,
        "whatsapp_url": f"https://wa.me/{digits}" if is_mob else "",
        "whatsapp_display": f"+{digits}" if is_mob else "No aplica",
    }


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
        harvester_ec: Optional[Any] = None,
        contracts_adapter: Optional[Any] = None,
        web_auditor: Optional[Any] = None,
        ledger: Optional[DeduplicationLedger] = None,
        verify_mx_fn: Optional[Any] = None,
        underwriter: Optional[Any] = None,
        mailbox_verifier: Optional[MailboxVerifierPort] = None,
    ):
        self.harvester_co = harvester_co
        self.harvester_dr = harvester_dr
        self.harvester_ec = harvester_ec
        self.contracts_adapter = contracts_adapter
        self.web_auditor = web_auditor
        self.ledger = ledger
        self.verify_mx_fn = verify_mx_fn or verify_mx
        self.underwriter = underwriter
        self.mailbox_verifier = mailbox_verifier or SocketSmtpVerifierAdapter()

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
        country: Optional[str] = None,
        country_allocations: Optional[Dict[str, int]] = None,
        # Universal dynamic parameters
        universal_request: Optional[UniversalProspectingRequest] = None,
        offer_description: Optional[str] = None,
        target_roles: Optional[List[str]] = None,
        target_sectors: Optional[List[str]] = None,
        target_ciiu_codes: Optional[List[str]] = None,
        location_allocations: Optional[List[Dict[str, Any]]] = None,
        keywords_include: Optional[List[str]] = None,
        keywords_exclude: Optional[List[str]] = None,
        directionality: str = "vendor_to_clients",
        rfq_specifications: Optional[str] = None,
    ) -> Dict[str, Any]:
        print("=" * 80)
        print("[ENGINE] UNIVERSAL MULTI-COUNTRY B2B PROSPECTOR & INTENT ENGINE (MICHITO)")
        print(f"   Target Tier: Tier {tier} ({'Underwritten & EBITDA Solvency' if tier == 3 else 'Decision-Maker & Mobile' if tier == 2 else 'Base Directory'})")
        print("=" * 80)

        if tier == 3 and not self.underwriter:
            self.underwriter = UnderwriteLeadUseCase()

        # 0. Unpack Universal Prospecting Request if provided
        if universal_request is not None:
            if hasattr(universal_request, "to_dict"):
                u_dict = universal_request.to_dict()
            elif isinstance(universal_request, dict):
                u_dict = universal_request
            else:
                u_dict = vars(universal_request)
            offer_description = offer_description or u_dict.get("offer_description")
            target_roles = target_roles or u_dict.get("roles")
            target_sectors = target_sectors or u_dict.get("sectors")
            target_ciiu_codes = target_ciiu_codes or u_dict.get("ciiu_codes")
            keywords_include = keywords_include or u_dict.get("keywords_include")
            keywords_exclude = keywords_exclude or u_dict.get("keywords_exclude")
            tier = u_dict.get("tier", tier)
            limit = u_dict.get("total_leads", limit)
            directionality = u_dict.get("directionality") or directionality
            rfq_specifications = u_dict.get("rfq_specifications") or rfq_specifications
            if u_dict.get("preset_id"):
                campaign = u_dict.get("preset_id")
            if u_dict.get("locations"):
                location_allocations = location_allocations or u_dict.get("locations")
            extra_excl = (u_dict.get("excluded_nits") or []) + (u_dict.get("excluded_domains") or [])
            if extra_excl:
                exclusions = list(set((exclusions or []) + extra_excl))

        # 1. Load Campaign Configuration Profile or Synthesize Universal Dynamic Profile
        available_camps = list_available_campaigns()
        is_dynamic = bool(offer_description) or campaign in ("custom", "universal", "none", None) or campaign not in available_camps
        loaded_cfg: Optional[Dict[str, Any]] = None

        if not is_dynamic:
            try:
                loaded_cfg = load_campaign(campaign)
            except Exception:
                is_dynamic = True

        campaign_cfg: Dict[str, Any]
        target_cfg: Dict[str, Any]

        if is_dynamic or loaded_cfg is None:
            campaign_id = campaign if (campaign and campaign not in ("custom", "universal", "none") and campaign in available_camps) else "universal_prospecting"
            campaign_name = offer_description[:45].strip().title() if offer_description else "Prospección Comercial B2B Universal"
            target_cfg = {
                "country": country or "CO",
                "currency": "USD" if country in ("MULTI", "EC") else ("DOP" if country == "DO" else "COP"),
                "city": city or "all",
                "cities": [loc.get("city") for loc in (location_allocations or []) if isinstance(loc, dict) and loc.get("city")] or ([city] if city else ["Medellín"]),
                "segment": segment or "midmarket",
                "sectors": target_sectors or ([sector] if sector else ["all"]),
                "ciiu_codes": target_ciiu_codes or [],
                "keywords_include": keywords_include or [],
                "keywords_exclude": keywords_exclude or [],
                "roles": target_roles or (["Director Comercial", "Gerente Comercial", "Gerente de Ventas", "Gerente General"] if directionality in ("client_to_vendors", "procurement") else DEFAULT_ROLES),
            }
            touches_cfg = generate_dynamic_touches(
                offer_description=offer_description,
                sectors=target_sectors or ([sector] if sector else None),
                roles=target_roles,
                directionality=directionality,
                rfq_specifications=rfq_specifications,
            )
            campaign_cfg = {
                "id": campaign_id,
                "name": campaign_name,
                "client_id": "universal",
                "description": offer_description or ("Solicitud y Homologación de Proveedores (Auto-RFQ)" if directionality in ("client_to_vendors", "procurement") else "Campaña B2B de prospección dinámica sobre demanda"),
                "target": target_cfg,
                "angles": {
                    "recommended": offer_description or ("Licitación y Cotización de Proveedores B2B" if directionality in ("client_to_vendors", "procurement") else "Eficiencia Operativa y Crecimiento Estratégico B2B"),
                },
                "specs": {},
                "teaser": {},
                "touches": touches_cfg,
            }
        else:
            campaign_cfg = loaded_cfg
            campaign_id = str(campaign_cfg.get("id", campaign))
            campaign_name = str(campaign_cfg.get("name", campaign))
            target_cfg = dict(campaign_cfg.get("target") or {})
            if keywords_include:
                target_cfg["keywords_include"] = list(set((target_cfg.get("keywords_include") or []) + keywords_include))
            if keywords_exclude:
                target_cfg["keywords_exclude"] = list(set((target_cfg.get("keywords_exclude") or []) + keywords_exclude))
            if target_roles:
                target_cfg["roles"] = target_roles
            if target_sectors:
                target_cfg["sectors"] = target_sectors
            if target_ciiu_codes:
                target_cfg["ciiu_codes"] = target_ciiu_codes
            if offer_description:
                touches_cfg = generate_dynamic_touches(
                    offer_description=offer_description,
                    sectors=target_sectors or target_cfg.get("sectors"),
                    roles=target_roles or target_cfg.get("roles"),
                    directionality=directionality,
                    rfq_specifications=rfq_specifications,
                )
            else:
                touches_cfg = dict(campaign_cfg.get("touches") or {})

        # Determine targeting & allocations across countries and territories
        val_country = country or target_cfg.get("country", "CO")
        if isinstance(val_country, list):
            raw_country = (val_country[0] if val_country else "CO").upper()
        else:
            raw_country = str(val_country or "CO").upper()

        REGIONAL_EXPANSIONS: Dict[str, List[str]] = {
            "costa caribe": ["Barranquilla", "Cartagena", "Santa Marta"],
            "eje cafetero": ["Pereira", "Manizales", "Armenia"],
        }

        def get_country_cities(c_code: str, raw_city_str: Optional[str]) -> List[str]:
            c_defaults = {
                "EC": ["Quito", "Guayaquil", "Cuenca"],
                "DO": ["Santo Domingo", "Santiago"],
                "CO": ["Medellín", "Bogotá"],
            }
            if not raw_city_str:
                cfg_cities = target_cfg.get("cities")
                if cfg_cities and raw_country not in ("MULTI", "CROSS_BORDER", "LATAM"):
                    if isinstance(cfg_cities, list):
                        return [str(c) for c in cfg_cities]
                    return [str(cfg_cities)]
                return c_defaults.get(c_code, ["Medellín"])

            tokens = [c.strip() for c in raw_city_str.split(",") if c.strip()]
            matched = []
            for token in tokens:
                norm_token = re.sub(r"[^\w\s]", "", token.lower()).strip()
                if norm_token in ("all", "nacional", "todo", "toda colombia", "todo el pais", "todo el país", "multi", "cross-border"):
                    return ["all"]
                if norm_token in REGIONAL_EXPANSIONS and c_code == "CO":
                    matched.extend(REGIONAL_EXPANSIONS[norm_token])
                    continue
                if c_code == "EC" and any(k in norm_token for k in ("quito", "guayaquil", "cuenca", "pichincha", "guayas", "azuay", "ecuador")):
                    matched.append(token)
                elif c_code == "DO" and any(k in norm_token for k in ("santo domingo", "santiago", "punta cana", "romana", "dominicana")):
                    matched.append(token)
                elif c_code == "CO" and not any(k in norm_token for k in ("quito", "guayaquil", "cuenca", "santo domingo", "santiago", "dominicana", "ecuador")):
                    matched.append(token)
            return matched if matched else c_defaults.get(c_code, ["Medellín"])

        # Build normalized territorial quota fulfillment plan
        normalized_territories: List[Dict[str, Any]] = []
        if location_allocations and len(location_allocations) > 0:
            if isinstance(location_allocations, dict):
                for loc_key, q_val in location_allocations.items():
                    c_code = (raw_country or "CO").upper()
                    c_city = str(loc_key)
                    if ":" in loc_key:
                        parts = loc_key.split(":", 1)
                        c_code = parts[0].upper()
                        c_city = parts[1]
                    normalized_territories.append({
                        "country": c_code,
                        "region": c_city,
                        "city": c_city,
                        "quota": int(q_val),
                    })
            else:
                for loc in location_allocations:
                    if hasattr(loc, "to_dict"):
                        loc = loc.to_dict()
                    if isinstance(loc, str):
                        c_code = (raw_country or "CO").upper()
                        c_city = loc
                        if ":" in loc:
                            parts = loc.split(":", 1)
                            c_code = parts[0].upper()
                            c_city = parts[1]
                        normalized_territories.append({
                            "country": c_code,
                            "region": c_city,
                            "city": c_city,
                            "quota": max(1, limit // len(location_allocations)),
                        })
                        continue
                    c_code = (loc.get("country") or loc.get("country_code") or raw_country or "CO").upper()
                    c_city = loc.get("city") or loc.get("city_name") or "all"
                    c_region = loc.get("region") or loc.get("region_name") or c_city
                    q = int(loc.get("allocated_leads") or loc.get("quota") or loc.get("limit") or 1)
                    normalized_territories.append({
                        "country": c_code,
                        "region": c_region,
                        "city": c_city,
                        "quota": q,
                    })
        else:
            active_allocations: Dict[str, int] = {}
            if country_allocations and isinstance(country_allocations, dict) and len(country_allocations) > 0:
                alloc_sum = sum(country_allocations.values())
                if alloc_sum == 100 and limit != 100:
                    accum = 0
                    items = list(country_allocations.items())
                    for c_k, pct in items[:-1]:
                        q = max(1, round(limit * (pct / 100.0)))
                        accum += q
                        active_allocations[c_k.upper()] = q
                    last_k, _ = items[-1]
                    active_allocations[last_k.upper()] = max(1, limit - accum)
                else:
                    active_allocations = {c_k.upper(): q for c_k, q in country_allocations.items()}
            elif raw_country in ("MULTI", "CROSS_BORDER", "LATAM"):
                q_co = max(1, round(limit * 0.50))
                q_do = max(1, round(limit * 0.30))
                q_ec = max(1, limit - q_co - q_do)
                active_allocations = {"CO": q_co, "DO": q_do, "EC": q_ec}
            else:
                active_allocations = {raw_country: limit}

            for c_code, c_quota in active_allocations.items():
                c_cities = get_country_cities(c_code, city)
                per_city_quota = max(1, c_quota // len(c_cities))
                for idx, c_city in enumerate(c_cities):
                    alloc_q = c_quota - (per_city_quota * (len(c_cities) - 1)) if idx == len(c_cities) - 1 else per_city_quota
                    normalized_territories.append({
                        "country": c_code,
                        "region": c_city,
                        "city": c_city,
                        "quota": alloc_q,
                    })

        unique_countries = list(dict.fromkeys(t["country"] for t in normalized_territories))
        is_multi_country = len(unique_countries) > 1
        target_country = "MULTI" if is_multi_country else (unique_countries[0] if unique_countries else "CO")
        target_currency = "USD" if is_multi_country or target_country == "EC" else ("DOP" if target_country == "DO" else "COP")
        angles_obj = campaign_cfg.get("angles")
        angles_dict = angles_obj if isinstance(angles_obj, dict) else {}
        recommended_angle = str(angles_dict.get(
            "recommended", "Eficiencia Operativa y Soluciones B2B Llave en Mano"
        ))

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
            item = exc.strip().lower()
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

        territories_summary = ", ".join(f"{t['country']}:{t['city']}:{t['quota']}" for t in normalized_territories)
        print(f"[PROFILE] Campaign Profile:  {campaign_name} (`{campaign_id}`)")
        print(f"[TERRITORY] Country Target:     {target_country} ({territories_summary})")
        print(f"[BATCH] Total Batch Target: {limit} qualified accounts")
        print(f"[ANGLE] Recommended Angle:  {recommended_angle}")
        if raw_exclusions:
            print(f"[SECURE] Exclusions Active:  {len(raw_exclusions)} entries ({len(clean_excl_nits)} NITs, {len(clean_excl_domains)} domains, {len(clean_excl_keywords)} keywords)")
        print("-" * 80)

        # 2. Initialize Deduplication Ledger
        ledger = self.ledger or DeduplicationLedger()
        seen_nits = ledger.get_seen_nits(campaign=campaign_id)
        print(f"[Ledger] Tracking {len(seen_nits)} previously prospected accounts. Exclusions active.")

        contracts_adapter = self.contracts_adapter or SecopContractsAdapter(timeout=6)
        web_auditor = self.web_auditor or WebsiteAuditor(timeout=5)

        all_selected: List[Dict[str, Any]] = []
        overall_start_time = time.time()
        harvest_time_total = 0.0
        verify_time_total = 0.0
        total_candidates_scanned = 0

        # 3. Harvest and Qualify Candidates per Territory Allocation
        kw_include = target_cfg.get("keywords_include")
        kw_exclude = target_cfg.get("keywords_exclude")
        scanned_cities: List[str] = []
        territory_fulfillment: Dict[str, Dict[str, Any]] = {}

        for territory in normalized_territories:
            c_code = territory["country"]
            c_region = territory["region"]
            target_city = territory["city"]
            t_quota = territory["quota"]

            territory_key = f"{target_city} ({c_region}, {c_code})"
            if territory_key not in territory_fulfillment:
                territory_fulfillment[territory_key] = {
                    "country": c_code,
                    "region": c_region,
                    "city": target_city,
                    "requested_quota": t_quota,
                    "delivered_count": 0,
                }
            else:
                territory_fulfillment[territory_key]["requested_quota"] += t_quota

            if target_city not in scanned_cities:
                scanned_cities.append(target_city)

            if len(all_selected) >= limit:
                break

            c_country_name = "Ecuador" if c_code == "EC" else ("República Dominicana" if c_code == "DO" else "Colombia")
            c_currency = "USD" if c_code == "EC" else ("DOP" if c_code == "DO" else "COP")
            c_tax_type = "RUC" if c_code == "EC" else ("RNC" if c_code == "DO" else "NIT")

            if c_code == "EC":
                harvester = self.harvester_ec or SercopEcuadorAdapter(timeout=15)
            elif c_code == "DO":
                harvester = self.harvester_dr or DgcpDrAdapter(timeout=15)
            else:
                harvester = self.harvester_co or SecopHarvesterAdapter(timeout=15)

            territory_selected = 0

            print(f"\n[Harvester] Querying active corporate providers in {target_city} ({c_country_name})...")
            raw_multiplier = 10 if c_code in ("DO", "EC") else 12
            harvester_kwargs: Dict[str, Any] = {
                "city": target_city,
                "limit": max(t_quota * raw_multiplier, 100),
                "corporate_only": True,
            }
            if kw_include:
                harvester_kwargs["include_keywords"] = kw_include
            if kw_exclude:
                harvester_kwargs["exclude_keywords"] = kw_exclude
            if target_ciiu_codes:
                harvester_kwargs["ciiu_codes"] = target_ciiu_codes
            if target_sectors:
                harvester_kwargs["sectors"] = target_sectors

            t_harv_start = time.time()
            raw_candidates = harvester.fetch_candidates(**harvester_kwargs)
            t_harv_elapsed = time.time() - t_harv_start
            harvest_time_total += t_harv_elapsed
            print(f"   Retrieved {len(raw_candidates)} candidate entities in {target_city} ({t_harv_elapsed:.2f}s).")

            t_verif_city_start = time.time()
            for item in raw_candidates:
                total_candidates_scanned += 1
                if territory_selected >= t_quota or len(all_selected) >= limit:
                    break

                nit = item["nit"]
                company_name = item["company_name"]

                # Deduplication Check (Against Ledger & Active Batch)
                if ledger.is_seen(nit, company_name, email=item.get("email", ""), campaign=campaign_id) or any(s["nit"] == nit for s in all_selected):
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
                    print(f"   [Exclusion Gate] Skipping excluded account: {company_name} ({c_tax_type}: {nit})")
                    continue

                email = item["email"]
                phone = item["phone"]

                # Phone Gate: Tier-adaptive validation and line classification
                phone_info = classify_phone(phone, country=c_code)
                digits_phone = re.sub(r"\D", "", phone or "")
                if len(digits_phone) < 7:
                    continue

                if tier >= 2:
                    if c_code == "DO":
                        clean_do = digits_phone[1:] if digits_phone.startswith("1") and len(digits_phone) == 11 else digits_phone
                        if len(clean_do) < 7:
                            continue
                    elif c_code == "EC":
                        clean_ec = digits_phone[3:] if digits_phone.startswith("593") and len(digits_phone) >= 12 else digits_phone
                        if len(clean_ec) < 7:
                            continue
                    else:
                        clean_co = digits_phone[2:] if digits_phone.startswith("57") and len(digits_phone) >= 12 else digits_phone
                        if len(clean_co) < 7:
                            continue

                # Deliverability Gate: DNS MX verification & Socket SMTP handshake
                ok_mx, mx_host = self.verify_mx_fn(email)
                if not ok_mx:
                    continue

                if self.mailbox_verifier and tier >= 2:
                    try:
                        mb_status = self.mailbox_verifier.verify_email(email, mx_host=mx_host)
                        if mb_status == "invalid":
                            continue
                    except Exception:
                        pass

                is_corporate_domain = not any(
                    pub in email for pub in ("@gmail.com", "@hotmail.com", "@yahoo.com", "@outlook.com")
                )

                # Website Resolution & Quality Audit Gate
                candidate_url = item.get("website") or ""
                if not candidate_url and is_corporate_domain:
                    candidate_domain = email.split("@")[1].strip().lower()
                    candidate_url = f"https://www.{candidate_domain}"

                if tier == 1:
                    audited_url = candidate_url or f"https://{email.split('@')[1].strip()}"
                    audit_note = "Validado por Dominio Corporativo & MX"
                else:
                    is_active_web, audited_url, audit_note = web_auditor.audit(candidate_url, company_name)
                    if not is_active_web:
                        continue

                # DANE / Regional Activity Classification
                ciiu_obj = CiiuCode.infer_from_text(
                    company_name=company_name,
                    email=email,
                    raw_desc=item.get("sector", "")
                )

                # CIIU Specific Filtering if requested
                if target_ciiu_codes and len(target_ciiu_codes) > 0:
                    ciiu_clean = [str(c).upper().strip() for c in target_ciiu_codes]
                    cand_ciiu = ciiu_obj.code.upper()
                    if cand_ciiu not in ciiu_clean and not any(cand_ciiu.startswith(prefix) for prefix in ciiu_clean):
                        if kw_include and not any(kw.lower() in company_name.lower() or kw.lower() in str(item.get("sector", "")).lower() for kw in kw_include):
                            continue

                # Trigger 1: Public Contract Awards
                if c_code == "DO":
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
                elif c_code == "EC":
                    c_val = float(item.get("contract_val_usd") or 0.0)
                    contracts_data = {
                        "has_contracts": c_val > 0,
                        "contracts_count": 1 if c_val > 0 else 0,
                        "total_value_cop": c_val,
                        "total_value_display": item.get("contract_val_display", "$0 USD"),
                        "top_contract_entity": item.get("contract_entity", "Estado Ecuatoriano (SERCOP)"),
                        "top_contract_value_cop": c_val,
                        "top_contract_value_display": item.get("contract_val_display", "$0 USD"),
                        "top_contract_object": item.get("contract_object", "Contratista adjudicado SERCOP"),
                        "intent_level": "Alto (Adjudicación SERCOP Activa)" if c_val > 0 else "Estándar",
                    }
                else:
                    contracts_data = contracts_adapter.fetch_contracts_summary(nit)

                # Trigger 2: Active Hiring Signals
                hiring_xray = build_hiring_xray_url(company_name, target_city, country=c_code)

                # Trigger 3: Regional Expansion & Satellite Need
                reg_city = item.get("city") or target_city
                if reg_city.lower() != target_city.lower():
                    expansion_flag = f"Sede Satélite en Expansión (Registrada en {reg_city})"
                elif contracts_data["has_contracts"]:
                    expansion_flag = f"Ejecutando Contratos Públicos Activos en {c_country_name}"
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
                    item.get("tama_o_entidad", "Mediana"), country=c_code
                )

                default_title = (
                    "Representante Legal / Gerente General (SuperCias)"
                    if c_code == "EC"
                    else ("Titular / Representante Registrado (DGCP)" if c_code == "DO" else "Representante Legal (Firmante Estatutario)")
                )
                rep_title = item.get("decision_maker_title") or default_title

                roles_to_pass: Optional[List[str]] = None
                if target_roles:
                    roles_to_pass = target_roles
                else:
                    cfg_roles = target_cfg.get("roles")
                    if isinstance(cfg_roles, list):
                        roles_to_pass = [str(r) for r in cfg_roles]
                    elif isinstance(cfg_roles, str):
                        roles_to_pass = [cfg_roles]

                targeted_xray = build_targeted_linkedin_xray_url(
                    company_name=company_name,
                    rep_name=rep_name,
                    campaign_id=campaign_id,
                    country=c_code,
                    target_roles=roles_to_pass,
                )

                targeted_persona = (
                    roles_to_pass[0]
                    if roles_to_pass
                    else "Dirección General / Gerencia General"
                )

                lead_record = {
                    "company_name": company_name,
                    "clean_name": clean_name,
                    "first_name": first_name,
                    "nit": nit,
                    "tax_id": nit,
                    "tax_id_type": c_tax_type,
                    "country": c_code,
                    "country_name": c_country_name,
                    "currency": c_currency,
                    "city": item.get("city") or target_city,
                    "department": item.get("department") or c_region,
                    "territory": territory_key,
                    "address": item.get("address", ""),
                    "ciiu": ciiu_obj,
                    "segment_name": seg_name,
                    "revenue_bracket": rev_range,
                    "employees_bracket": emp_range,
                    "website_url": audited_url,
                    "website_audit_status": audit_note,
                    "decision_maker_name": rep_name,
                    "decision_maker_title": rep_title,
                    "decision_maker_category": default_title,
                    "registered_contact_name": rep_name,
                    "registered_contact_title": rep_title,
                    "targeted_campaign_persona": targeted_persona,
                    "email": email,
                    "phone": phone_info.get("formatted") or phone,
                    "raw_phone": phone,
                    "phone_line_type": phone_info.get("line_type", "Línea Corporativa"),
                    "is_mobile": phone_info.get("is_mobile", False),
                    "whatsapp_url": phone_info.get("whatsapp_url", ""),
                    "whatsapp_display": phone_info.get("whatsapp_display", ""),
                    "mx_host": mx_host,
                    "linkedin_xray_url": targeted_xray,
                    "contracts_data": contracts_data,
                    "hiring_xray_url": hiring_xray,
                    "expansion_flag": expansion_flag,
                }

                all_selected.append(lead_record)
                territory_selected += 1
                territory_fulfillment[territory_key]["delivered_count"] = territory_selected

            verify_time_total += time.time() - t_verif_city_start

        format_start_time = time.time()

        if not all_selected:
            total_elapsed = time.time() - overall_start_time
            print(f"\n[WARN] No fresh companies found matching all quality and deliverability gates ({total_elapsed:.2f}s).")
            return {
                "status": "no_leads_found",
                "tier": tier,
                "campaign_id": campaign_id,
                "campaign_name": campaign_name,
                "country": target_country,
                "currency": target_currency,
                "target_cities": scanned_cities,
                "territory_fulfillment": territory_fulfillment,
                "universal_request": universal_request.to_dict() if (universal_request and hasattr(universal_request, "to_dict")) else None,
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

        # 4. Lead Quality & Intent Ranking (Ensure highest intent & solvency appear first)
        def compute_lead_rank(lead: Dict[str, Any]) -> int:
            score = 0
            if lead.get("is_mobile"):
                score += 25
            contracts = lead.get("contracts_data", {})
            if contracts.get("has_contracts"):
                score += 35
            audit_status = str(lead.get("website_audit_status") or "").lower()
            if audit_status and "offline" not in audit_status and "fallido" not in audit_status:
                score += 25
            dm_name = str(lead.get("decision_maker_name") or "").lower()
            if dm_name and not any(g in dm_name for g in ("representante legal", "no provisto", "titular", "gerencia")):
                score += 20
            email_val = str(lead.get("email") or "").lower()
            if email_val and not any(pub in email_val for pub in ("@gmail.com", "@hotmail.com", "@yahoo.com", "@outlook.com")):
                score += 20
            return score

        all_selected.sort(key=compute_lead_rank, reverse=True)
        print(f"\n[Engine] Successfully assembled and ranked {len(all_selected)} verified enterprise leads.")

        # 5. Format 5-Touch Outreach Cadence
        csv_rows = []
        crm_rows = []
        playbook_cadences = []
        now = datetime.now(timezone.utc)
        batch_timestamp = now.strftime("%Y%m%d_%H%M%S")
        batch_dir = os.path.join(GROWTH_OUTPUTS_BASE, campaign_id, batch_timestamp)
        os.makedirs(batch_dir, exist_ok=True)

        # Dynamic Country Regulatory Labels
        tax_id_header = "RUC" if target_country == "EC" else ("RNC" if target_country == "DO" else "NIT")
        size_header = (
            "Company Size (SuperCias)"
            if target_country == "EC"
            else ("Company Size (Ley 187-17 MICM)" if target_country == "DO" else "Company Size (Decreto 957)")
        )
        activity_header = (
            "Actividad Económica (SRI)"
            if target_country == "EC"
            else ("Actividad Económica (DGII)" if target_country == "DO" else "CIIU Activity (RUT Box 46)")
        )
        code_header = "SRI Code" if target_country == "EC" else ("DGII Code" if target_country == "DO" else "CIIU Code")
        contracts_header = f"Trigger 1: Total Contracts Won {target_currency}"

        # Standardized Tax Header for Clean CRM:
        # If single-country batch: use the respective national tax ID label (NIT / RNC / RUC)
        # If multi-country cross-border batch: unified header "Tax ID (NIT / RNC / RUC)"
        batch_countries = {lead.get("country", target_country) for lead in all_selected}
        if len(batch_countries) == 1:
            only_c = list(batch_countries)[0]
            batch_tax_label = "NIT" if only_c == "CO" else ("RNC" if only_c == "DO" else ("RUC" if only_c == "EC" else "Tax ID"))
        else:
            batch_tax_label = "Tax ID (NIT / RNC / RUC)"

        for idx, lead in enumerate(all_selected, start=1):
            clean_name = lead["clean_name"]
            salutation = f"Hola {lead['first_name']}"
            contact_title = lead["decision_maker_title"]
            city = lead["city"]
            ciiu = lead["ciiu"]
            contracts = lead["contracts_data"]
            lead_c = lead.get("country", target_country)
            lead_curr = lead.get("currency", target_currency)
            lead_tax = lead.get("tax_id_type", "NIT")

            # Format touches safely across both YAML and dynamic templates
            def safe_format(tmpl: str) -> str:
                if not tmpl:
                    return ""
                res = tmpl
                replacements = {
                    "{salutation}": salutation,
                    "{clean_name}": clean_name,
                    "{company_name}": lead["company_name"],
                    "{city}": city,
                    "{contact_title}": contact_title,
                }
                for k, v in replacements.items():
                    res = res.replace(k, str(v))
                return res.strip()

            t1 = safe_format(touches_cfg.get("touch1_linkedin_invite", "")).replace("\n", " ")
            t2_sub = safe_format(touches_cfg.get("touch2_email_subject", ""))
            t2_body = safe_format(touches_cfg.get("touch2_email_body", ""))

            # If Trigger 1 is active, tailor Touch 2 with contract award mention
            contract_raw_val = contracts.get("total_value_cop", 0)
            if contracts["has_contracts"] and contract_raw_val > 0:
                contract_mention = (
                    f"\n\n[Trigger de Compra Detectado: Felicitaciones por la adjudicación de contratos recientes "
                    f"con {contracts['top_contract_entity']} por {contracts['top_contract_value_display']}. "
                    f"Para la ejecución de estos proyectos, contar con infraestructura locativa llave en mano ahorra meses de trámites.]"
                )
                t2_body += contract_mention

            t3_sub = safe_format(touches_cfg.get("touch3_email_subject", ""))
            t3_body = safe_format(touches_cfg.get("touch3_email_body", ""))

            t4_sub = safe_format(touches_cfg.get("touch4_email_subject", ""))
            t4_body = safe_format(touches_cfg.get("touch4_email_body", ""))

            t5_sub = safe_format(touches_cfg.get("touch5_email_subject", ""))
            t5_body = safe_format(touches_cfg.get("touch5_email_body", ""))

            row = {
                "Index": idx,
                "Country": lead_c,
                "Country Name": lead.get("country_name", "Colombia"),
                "Tax ID Type": lead_tax,
                "Tax ID": lead["nit"],
                "Company Name": lead["company_name"],
                "City": lead["city"],
                "Department": lead.get("department", ""),
                "Activity Code": ciiu.code,
                "Sector Macro": ciiu.sector_macro,
                "Economic Activity": ciiu.description,
                "Company Size": lead["segment_name"],
                "Revenue Bracket": lead["revenue_bracket"],
                "Estimated Employees": lead["employees_bracket"],
                "Address": lead["address"],
                "Website": lead["website_url"],
                "Website Audit Status": lead["website_audit_status"],
                "Official Registered Contact": lead["decision_maker_name"],
                "Official Statutory Title": lead["decision_maker_title"],
                "Contact Category": lead.get("decision_maker_category", "Representante Legal Estatutario (RUES / SECOP)"),
                "Targeted Campaign Persona": lead.get("targeted_campaign_persona", "Dirección General"),
                "Decision Maker Name": lead["decision_maker_name"],  # Backward-compatible alias
                "Official Title": lead["decision_maker_title"],  # Backward-compatible alias
                "Verified Work Email": lead["email"],
                "Corporate Phone": lead["phone"],
                "Phone Line Type": lead.get("phone_line_type", "Línea Corporativa"),
                "WhatsApp Direct Link": lead.get("whatsapp_url", ""),
                "Direct Mobile Phone": lead["phone"],  # Backward-compatible alias
                "Mail Server (MX)": lead["mx_host"],
                "Trigger 1: Total Contracts Won": contracts["total_value_display"],
                "Trigger 1: Currency": lead_curr,
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

            # Backward-compatible country-specific regulatory tax header
            row[tax_id_header] = lead["nit"]
            row[code_header] = ciiu.code
            row[activity_header] = ciiu.description
            row[size_header] = lead["segment_name"]
            row[contracts_header] = contracts["total_value_display"]
            if lead_c == "CO" and "NIT" not in row:
                row["NIT"] = lead["nit"]
            elif lead_c == "DO" and "RNC" not in row:
                row["RNC"] = lead["nit"]
            elif lead_c == "EC" and "RUC" not in row:
                row["RUC"] = lead["nit"]

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

            trigger_summary = contracts["total_value_display"]
            if contracts.get("has_contracts") and contracts.get("top_contract_entity"):
                trigger_summary = f"Contratos SECOP: {contracts['total_value_display']} ({contracts['top_contract_entity']})"
            elif lead.get("expansion_flag"):
                trigger_summary = lead["expansion_flag"]
            else:
                trigger_summary = "Operación Corporativa Activa (Crecimiento Privado)"

            crm_row = {
                "Index": idx,
                "Company Name": lead["company_name"],
                batch_tax_label: lead["nit"],
                "City": lead["city"],
                "Department": lead.get("department", ""),
                "Country": lead.get("country_name", "Colombia"),
                "Sector Macro": ciiu.sector_macro,
                "Economic Activity": ciiu.description,
                "Activity Code": ciiu.code,
                "Company Size": lead["segment_name"],
                "Official Registered Contact": lead["decision_maker_name"],
                "Official Statutory Title": lead["decision_maker_title"],
                "Targeted Campaign Persona": lead.get("targeted_campaign_persona", "Dirección General"),
                "Decision Maker Name": lead["decision_maker_name"],  # Backward compatibility
                "Official Title": lead["decision_maker_title"],  # Backward compatibility
                "Verified Work Email": lead["email"],
                "Corporate Phone": lead["phone"],
                "Phone Line Type": lead.get("phone_line_type", "Línea Corporativa"),
                "WhatsApp Direct Link": lead.get("whatsapp_url", ""),
                "Direct Mobile Phone": lead["phone"],  # Backward compatibility
                "Website": lead["website_url"],
                "Commercial Trigger": trigger_summary,
                "Recommended Angle": recommended_angle,
            }
            if tier == 3 and lead.get("underwriting"):
                uw = lead["underwriting"]
                crm_row["Underwriting Grade"] = uw.get("underwriting_grade", "A")
                crm_row["Solvency Tier"] = uw.get("solvency_tier", "Solvente")
                crm_row["Litigation Risk"] = uw.get("litigation_risk_status", "Clean")

            crm_rows.append(crm_row)

            # Structured Playbook Cadence for Interactive Web SDR UI
            playbook_cadences.append({
                "index": idx,
                "company_name": lead["company_name"],
                "clean_name": clean_name,
                "tax_id": lead["nit"],
                "tax_id_type": lead_tax,
                "country": lead_c,
                "city": lead["city"],
                "website": lead["website_url"],
                "decision_maker_name": lead["decision_maker_name"],
                "decision_maker_title": lead["decision_maker_title"],
                "targeted_campaign_persona": lead.get("targeted_campaign_persona", "Dirección General"),
                "email": lead["email"],
                "phone": lead["phone"],
                "phone_line_type": lead.get("phone_line_type", "Línea Corporativa"),
                "is_mobile": lead.get("is_mobile", False),
                "whatsapp_url": lead.get("whatsapp_url", ""),
                "recommended_angle": recommended_angle,
                "touches": {
                    "touch1_linkedin": t1,
                    "touch2_email": {
                        "subject": t2_sub,
                        "body": t2_body,
                    },
                    "touch3_followup": {
                        "subject": t3_sub,
                        "body": t3_body,
                    },
                    "touch4_social_proof": {
                        "subject": t4_sub,
                        "body": t4_body,
                    },
                    "touch5_breakup": {
                        "subject": t5_sub,
                        "body": t5_body,
                    },
                },
                "triggers": {
                    "contracts_won": contracts["total_value_display"],
                    "entity": contracts["top_contract_entity"],
                    "intent": contracts["intent_level"],
                    "expansion": lead["expansion_flag"],
                }
            })

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
                        "country": lead_c,
                        "currency": lead_curr,
                    }
                )

        # 6. Export CRM Deliverables (Clean CSV & Styled XLSX)
        csv_filename = os.path.join(batch_dir, "prospects.csv")
        xlsx_filename = os.path.join(batch_dir, "prospects.xlsx")
        md_filename = os.path.join(batch_dir, "executive_dossier.md")
        pdf_filename = os.path.join(batch_dir, "executive_dossier.pdf")
        teaser_filename = os.path.join(batch_dir, "confidential_teaser.html")

        full_csv_filename = os.path.join(batch_dir, "prospects_full_intelligence.csv")
        if output_format in ("csv", "both", "all", "xlsx"):
            crm_fieldnames: List[str] = []
            for r in crm_rows:
                for k in r.keys():
                    if k not in crm_fieldnames:
                        crm_fieldnames.append(k)

            with open(csv_filename, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=crm_fieldnames, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(crm_rows)
            print(f"[OK] Generated CRM CSV Batch: {csv_filename}")

            full_fieldnames: List[str] = []
            for r in csv_rows:
                for k in r.keys():
                    if k not in full_fieldnames:
                        full_fieldnames.append(k)

            with open(full_csv_filename, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=full_fieldnames, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(csv_rows)
            print(f"[OK] Generated Full Intelligence CSV Batch: {full_csv_filename}")

            try:
                excel_adapter = ExcelDossierAdapter()
                excel_adapter.export_prospects_xlsx(
                    rows=crm_rows,
                    output_path=xlsx_filename,
                    campaign_title=campaign_name
                )
                print(f"[OK] Generated Styled CRM XLSX Spreadsheet: {xlsx_filename}")
            except Exception as e:
                print(f"[WARN] Warning: Could not generate XLSX spreadsheet: {e}")

        # 7. Export Markdown Executive Dossier
        if output_format in ("markdown", "both", "all", "pdf"):
            if is_multi_country:
                country_flag = "🌎"
                country_name_title = "Cross-Border (Latam)"
                ground_truth_desc = (
                    "Verified Cross-Border B2B Ground Truth (SECOP II 🇨🇴 • DGCP 🇩🇴 • SERCOP / SuperCias 🇪🇨) • Zero-Bounce DNS MX • Real-Time Website Audit"
                )
            elif target_country == "EC":
                country_flag = "🇪🇨"
                country_name_title = "Ecuadorian"
                ground_truth_desc = "Verified Ecuadorian B2B Ground Truth (SERCOP / SuperCias) • Zero-Bounce DNS MX • Real-Time Website Audit"
            elif target_country == "DO":
                country_flag = "🇩🇴"
                country_name_title = "Dominican Republic"
                ground_truth_desc = (
                    "Verified Dominican Republic B2B Ground Truth (DGCP / RNC) • Zero-Bounce DNS MX • Real-Time Website Audit"
                )
            else:
                country_flag = "🇨🇴"
                country_name_title = "Colombian"
                ground_truth_desc = (
                    "Verified Colombian B2B Ground Truth (SECOP / RUES) • Zero-Bounce DNS MX • Real-Time Website Audit"
                )

            md_content = []
            md_content.append(f"# {country_flag} {country_name_title} B2B Qualified Prospect Batch — {campaign_name}")
            md_content.append(f"**Campaign ID:** `{campaign_id}` | **Date:** {now.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            md_content.append(f"**Total Qualified Accounts:** {len(csv_rows)} | **Batch Directory:** `{batch_dir}`")
            md_content.append(f"*{ground_truth_desc}*\n")
            md_content.append("---")
            md_content.append("\n## [PROFILE] Master Qualification Table with Expansion Intent Triggers\n")
            md_content.append(
                f"| # | Country | Company Name | Activity & Macro Sector | City | Decision Maker | Email & Phone | Website | Contracts Won (Trigger 1) | Expansion Flag (Trigger 3) |"
            )
            md_content.append(
                "| :-: | :---: | :--- | :--- | :---: | :--- | :--- | :--- | :--- | :--- |"
            )

            for r in csv_rows:
                c_icon = "🇪🇨" if r['Country'] == "EC" else ("🇩🇴" if r['Country'] == "DO" else "🇨🇴")
                web_display = f"[{r['Website']}]({r['Website']})" if r['Website'].startswith("http") else r['Website']
                phone_cell = f"`{r['Corporate Phone']}`"
                if r.get('WhatsApp Direct Link'):
                    phone_cell += "<br><small>Móvil / WhatsApp</small>"
                elif r.get('Phone Line Type'):
                    phone_cell += f"<br><small>{r['Phone Line Type']}</small>"

                md_content.append(
                    f"| {r['Index']} | {c_icon} `{r['Country']}` | **{r['Company Name']}**<br><small>{r['Tax ID Type']}: {r['Tax ID']}</small> | "
                    f"**{r['Activity Code']}**<br><small>{r['Sector Macro']}</small> | {r['City']} | "
                    f"**{r['Official Registered Contact']}**<br><small>{r['Official Statutory Title']}</small> | "
                    f"`{r['Verified Work Email']}`<br>{phone_cell} | "
                    f"{web_display} | **{r['Trigger 1: Total Contracts Won']}**<br><small>{r['Trigger 1: Top Contracting Entity'][:30]}</small> | "
                    f"<small>{r['Trigger 3: Regional Expansion Flag']}</small> |"
                )

            md_content.append("\n---\n")
            md_content.append("## Detailed Profiles & 5-Touch Cadence\n")

            for r in csv_rows:
                c_icon = "🇪🇨" if r['Country'] == "EC" else ("🇩🇴" if r['Country'] == "DO" else "🇨🇴")
                web_display = f"[{r['Website']}]({r['Website']})" if r['Website'].startswith("http") else r['Website']
                wa_link = f" • [WhatsApp Directo]({r['WhatsApp Direct Link']})" if r.get('WhatsApp Direct Link') else ""
                md_content.append(f"### {r['Index']}. {c_icon} {r['Company Name']} ({r['City']}, {r['Country Name']})")
                md_content.append(f"* **Actividad Económica**: **{r['Activity Code']}** — {r['Economic Activity']}")
                md_content.append(f"* **Sector Macro**: {r['Sector Macro']} | **Tamaño**: {r['Company Size']} ({r['Revenue Bracket']} • {r['Estimated Employees']})")
                md_content.append(f"* **Sitio Web**: {web_display} — *{r['Website Audit Status']}*")
                md_content.append(f"* **Firmante Estatutario Registrado**: **{r['Official Registered Contact']}** ({r['Official Statutory Title']})")
                md_content.append(f"* **Persona Objetivo de Campaña**: **{r['Targeted Campaign Persona']}**")
                md_content.append(f"* **Email Corporativo**: `{r['Verified Work Email']}` | **Teléfono ({r['Phone Line Type']})**: `{r['Corporate Phone']}`{wa_link} | **Servidor MX**: `{r['Mail Server (MX)']}`")
                md_content.append(f"* **Dirección Corporativa**: {r['Address']} | **{r['Tax ID Type']}**: `{r['Tax ID']}`")
                md_content.append(f"* **Trigger 1 (Contratos Ganados)**: **{r['Trigger 1: Total Contracts Won']}** — {r['Trigger 1: Top Contracting Entity']} (*{r['Trigger 1: Intent Score']}*)")
                if r['Trigger 1: Top Contract Object']:
                    md_content.append(f"  * *Objeto*: {r['Trigger 1: Top Contract Object']}")
                md_content.append(f"* **Trigger 2 (Búsqueda de Empleos / Vacantes)**: [ Ver Vacantes Activas en Google/LinkedIn]({r['Trigger 2: Hiring X-Ray Search URL']})")
                md_content.append(f"* **Trigger 3 (Expansión)**: {r['Trigger 3: Regional Expansion Flag']}")
                md_content.append(f"* [ Triangulación LinkedIn: Contacto Registrado & Directores de Área]({r['LinkedIn X-Ray URL']})\n")

                md_content.append("#### Touch 1: LinkedIn Connection Note (<300 chars)")
                md_content.append(f"> \"{r['Touch 1: LinkedIn Connection Note']}\"\n")

                md_content.append(f"#### Touch 2: Cold Email (Día 1) — Asunto: *{r['Touch 2: Cold Email Subject']}*")
                md_content.append("```text")
                md_content.append(r["Touch 2: Cold Email Body"])
                md_content.append("```\n")

                md_content.append(f"#### Touch 3: Operational Follow-up (Día 4) — Asunto: *{r['Touch 3: Operational Follow-up Subject']}*")
                md_content.append("```text")
                md_content.append(r["Touch 3: Operational Follow-up Body"])
                md_content.append("```\n")

                md_content.append(f"#### Touch 4: Social Proof / VIP Day Pass (Día 8) — Asunto: *{r['Touch 4: Social Proof / VIP Subject']}*")
                md_content.append("```text")
                md_content.append(r["Touch 4: Social Proof / VIP Body"])
                md_content.append("```\n")

                md_content.append(f"#### Touch 5: Breakup / Corporate Catalog (Día 14) — Asunto: *{r['Touch 5: Breakup / Catalog Subject']}*")
                md_content.append("```text")
                md_content.append(r["Touch 5: Breakup / Catalog Body"])
                md_content.append("```\n")

                if tier == 3 and "Underwriting Grade" in r:
                    md_content.append("#### Suscripción Financiera y Riesgo Legal (Tier 3)")
                    md_content.append(f"* **Calificación Integral**: **{r['Underwriting Grade']}** (Score: {r['Composite Quality Score (0-100)']}/100)")
                    md_content.append(f"* **Solvencia Operativa**: EBITDA Est.: **${r['Solvency: Estimated EBITDA (COP)']:,.0f} {r['Trigger 1: Currency']}** (Margen: **{r['Solvency: EBITDA Margin (%)']}%** — *Tier {r['Solvency: Tier']}*)")
                    md_content.append(f"* **Perfil Financiero**: {r['Solvency: Profile Summary']}")
                    md_content.append(f"* **Semáforo Legal**: **{r['Legal Risk: Litigation Status']}** — {r['Legal Risk: Dockets & Sanctions Summary']}")
                    md_content.append(f"* **Recomendación Comercial de Crédito**: {r['Credit Terms Recommendation']}\n")

                md_content.append("---\n")

            with open(md_filename, "w", encoding="utf-8") as f:
                f.write("\n".join(md_content))
            print(f"[OK] Generated Executive Dossier: {md_filename}")

            try:
                pdf_adapter = PdfDossierAdapter()
                pass_rate_pct = (len(csv_rows) / max(1, total_candidates_scanned)) * 100
                assert campaign_cfg is not None
                pdf_adapter.generate_dossier_pdf(
                    campaign_cfg=campaign_cfg,
                    leads=csv_rows,
                    output_path=pdf_filename,
                    tier=tier,
                    metrics={
                        "total_leads": len(csv_rows),
                        "candidates_evaluated": total_candidates_scanned,
                        "pipeline_pass_rate": f"{pass_rate_pct:.1f}%",
                    }
                )
                print(f"[OK] Generated Executive PDF Dossier: {pdf_filename}")
            except Exception as e:
                print(f"[WARN] Warning: Could not generate PDF dossier: {e}")

        # 8. Compile Teaser if enabled
        assert campaign_cfg is not None
        compiled_teaser = compile_teaser_html(campaign_cfg, teaser_filename)
        if compiled_teaser:
            print(f" Compiled 1-Page Institutional Teaser: {teaser_filename}")

        # 9. Save Deduplication Ledger
        if not dry_run:
            ledger.save_batch()
            print(f"[SAVED] Persistent Deduplication Ledger Updated: {len(csv_rows)} accounts recorded.")
        else:
            print(" Dry run active: Master ledger was NOT modified.")

        # 10. Performance & Execution Benchmark
        total_elapsed = time.time() - overall_start_time
        format_time_total = time.time() - format_start_time
        qualified_count = len(csv_rows)
        avg_speed = total_elapsed / max(1, qualified_count)
        throughput_cpm = (qualified_count / (total_elapsed / 60)) if total_elapsed > 0 else 0.0
        qual_rate = (qualified_count / max(1, total_candidates_scanned)) * 100

        print("\n" + "=" * 80)
        print("[BENCHMARK]  PERFORMANCE & HARVEST BENCHMARK")
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

        print(f"\n[COMPLETE] Batch Execution Complete! Deliverables saved to:\n   [DIR] {batch_dir}")
        print("=" * 80)

        teaser_selected = []
        represented_countries = set()
        for lead in all_selected:
            c = lead.get("country", target_country)
            if c not in represented_countries and len(teaser_selected) < 3:
                represented_countries.add(c)
                teaser_selected.append(lead)

        for lead in all_selected:
            if len(teaser_selected) >= 3:
                break
            if lead not in teaser_selected:
                teaser_selected.append(lead)

        teaser_list = []
        for lead in teaser_selected:
            raw_email = lead.get("email", "")
            raw_phone = lead.get("phone", "")
            raw_nit = lead.get("nit", "")
            rep_name = lead.get("decision_maker_name", "")
            rep_role = lead.get("decision_maker_title") or "Representante Legal (Firmante Estatutario)"
            contracts = lead.get("contracts_data", {})
            intent_msg = contracts.get("intent_level") or lead.get("expansion_flag") or "Adjudicación Contrato Reciente"
            lead_c = lead.get("country", target_country)

            t_item = {
                "company_name": lead.get("clean_name", lead.get("company_name", "")),
                "nit": mask_teaser_nit(raw_nit),
                "tax_id": mask_teaser_nit(raw_nit),
                "country": lead_c,
                "country_name": lead.get("country_name", "Colombia"),
                "flag": "🇪🇨" if lead_c == "EC" else ("🇩🇴" if lead_c == "DO" else "🇨🇴"),
                "city": lead.get("city", ""),
                "sector": getattr(lead.get("ciiu"), "sector_macro", str(lead.get("ciiu", ""))),
                "decision_maker_name": rep_name,
                "decision_maker_role": rep_role,
                "decision_maker_title": rep_role,
                "targeted_role": lead.get("targeted_campaign_persona", "Dirección General"),
                "email": mask_teaser_email(raw_email),
                "phone": mask_teaser_phone(raw_phone, country=lead_c),
                "phone_line_type": lead.get("phone_line_type", "Línea Corporativa"),
                "is_mobile": lead.get("is_mobile", False),
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
            "target_cities": scanned_cities,
            "territory_fulfillment": territory_fulfillment,
            "universal_request": universal_request.to_dict() if (universal_request and hasattr(universal_request, "to_dict")) else None,
            "batch_dir": batch_dir,
            "csv_path": csv_filename if output_format in ("csv", "both", "all") else None,
            "xlsx_path": xlsx_filename if (output_format in ("csv", "both", "all", "xlsx") and os.path.exists(xlsx_filename)) else None,
            "full_csv_path": full_csv_filename if output_format in ("csv", "both", "all") else None,
            "dossier_path": md_filename if output_format in ("markdown", "both", "all") else None,
            "pdf_path": pdf_filename if (output_format in ("markdown", "both", "all", "pdf") and os.path.exists(pdf_filename)) else None,
            "teaser_path": teaser_filename if compiled_teaser else None,
            "playbook_cadences": playbook_cadences,
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
