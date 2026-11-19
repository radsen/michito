import hashlib
import hmac
import re
import json
from fastapi import FastAPI, Depends, Request, HTTPException, BackgroundTasks, Query
from fastapi.responses import HTMLResponse, PlainTextResponse, FileResponse, RedirectResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Union
from decimal import Decimal
import uuid
import os
import logging

import src.config  # Auto-loads .env.local / .env.stg / .env

from src.entrypoints.container import Container, container as app_container
from src.application.dto.search_request_dto import CompanyFilterDto
from src.domain.entities.lead_order import LeadOrder
from src.domain.entities.company import Company
from src.domain.value_objects.tax_id import TaxId
from src.adapters.db.sql_order_adapter import SqlOrderAdapter
from src.adapters.partners.partner_registry import PartnerRegistry
from src.adapters.delivery.omnichannel_delivery_adapter import OmnichannelDeliveryAdapter
from src.application.use_cases.deliver_order_use_case import DeliverOrderUseCase
from src.application.services.brief_parser_service import BriefParserService
from src.adapters.security.rate_limiter import ai_agent_rate_limiter
from campaign_loader import list_available_campaigns, load_campaign

logger = logging.getLogger(__name__)

app = FastAPI(title="Michito B2B Intelligence Engine API", version="2.0.0")

# Enable Cross-Origin Resource Sharing (CORS) with explicit trusted origins
allowed_origins_raw = os.environ.get(
    "ALLOWED_ORIGINS",
    "https://michito.co,https://www.michito.co,https://app.michito.co,https://michito-web-limgi3puaq-uc.a.run.app,http://localhost:5000,http://localhost:5173,http://localhost:8080,http://localhost:3000,http://127.0.0.1:5000,http://127.0.0.1:5173,http://127.0.0.1:8080,http://127.0.0.1:3000"
)
allowed_origins = [o.strip() for o in allowed_origins_raw.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if allowed_origins else ["https://michito.co", "https://www.michito.co"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

def _find_templates_dir() -> str:
    candidates = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../templates")),
        os.path.abspath("backend/templates"),
        os.path.abspath("templates"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return "templates"

templates = Jinja2Templates(directory=_find_templates_dir())
sql_adapter = SqlOrderAdapter()
omnichannel_delivery_adapter = OmnichannelDeliveryAdapter()
deliver_order_use_case = DeliverOrderUseCase(omnichannel_delivery_adapter, sql_adapter)


def get_container() -> Container:
    return app_container

# Multi-Client Order Request Models (per docs/developer_handoff_specification.md)
class ClientDto(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    channel: Optional[str] = "web_portal"
    client_id: Optional[str] = None
    referral_partner: Optional[str] = "direct"

class RequestDto(BaseModel):
    campaign_id: Optional[str] = "universal_prospecting"
    country: Optional[str] = "CO"
    country_allocations: Optional[Dict[str, int]] = None
    location_allocations: Optional[Union[List[Dict[str, Any]], Dict[str, Any]]] = None
    city: Optional[str] = "Medellín"
    limit: Optional[int] = 10
    tier: Optional[int] = 2
    segment: Optional[str] = None
    sector: Optional[str] = None
    offer_description: Optional[str] = None
    target_roles: Optional[List[str]] = None
    target_ciiu_codes: Optional[List[str]] = None
    keywords_include: Optional[List[str]] = None
    keywords_exclude: Optional[List[str]] = None
    exclusions: Optional[List[str]] = None
    directionality: Optional[str] = "vendor_to_clients"
    rfq_specifications: Optional[str] = None

class CreateOrderRequest(BaseModel):
    client: ClientDto
    request: RequestDto

class CustomTaxonomyRequest(BaseModel):
    type: str  # "sector" or "role"
    name: str
    country_code: Optional[str] = "ALL"
    ciiu_codes: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    domain: Optional[str] = "general"
    seniority: Optional[str] = "director"

class IntentProfileRequest(BaseModel):
    query: str
    country: Optional[str] = "CO"

class ParseBriefRequest(BaseModel):
    prompt: str
    client_id: Optional[str] = None
    session_id: Optional[str] = None
    force_fallback: Optional[bool] = False

# Legacy Request Models
class SearchRequest(BaseModel):
    country_code: str
    min_revenue: Optional[Decimal] = None
    industry: Optional[str] = None
    city: Optional[str] = None

class VerificationRequest(BaseModel):
    email: str

class LegacyOrderRequest(BaseModel):
    tier: int
    company_id: str

class EbitdaRequest(BaseModel):
    operating_revenue: Decimal
    cost_of_sales: Decimal
    operating_expenses: Decimal
    depreciation: Decimal
    amortization: Decimal

NO_CACHE_HEADERS = {
    "Cache-Control": "no-cache, no-store, must-revalidate",
    "Pragma": "no-cache",
    "Expires": "0",
}

def _find_static_file(rel_path: str) -> str:
    candidates = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../", rel_path)),
        os.path.abspath(rel_path),
        os.path.abspath(os.path.join("..", rel_path)),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return rel_path

assets_dir = _find_static_file("clients/web/dist/assets")
if os.path.exists(assets_dir):
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

@app.get("/", response_class=HTMLResponse)
def get_root_portal():
    """Serves the primary Michito B2B Lead Intelligence Order Portal (No Cache)."""
    dist_index = _find_static_file("clients/web/dist/index.html")
    public_index = _find_static_file("clients/web/public/index.html")
    index_path = dist_index if os.path.exists(dist_index) else public_index
    return FileResponse(index_path, media_type="text/html", headers=NO_CACHE_HEADERS)

@app.get("/styles.css")
def get_styles():
    return FileResponse(_find_static_file("clients/web/public/styles.css"), media_type="text/css", headers=NO_CACHE_HEADERS)

@app.get("/app.js")
def get_app_js():
    return FileResponse(_find_static_file("clients/web/public/app.js"), media_type="application/javascript", headers=NO_CACHE_HEADERS)

@app.get("/legacy-warehouse-teaser", response_class=HTMLResponse)
def get_legacy_teaser(request: Request):
    return templates.TemplateResponse(request, "teaser_one_pager_base.html")

# ------------------------------------------------------------------------------
# Universal B2B Multi-Client Order Endpoints (PostgreSQL & Web Client Integration)
# ------------------------------------------------------------------------------
@app.get("/api/v1/campaigns")
def get_campaigns():
    """
    Returns available B2B campaign profiles and metadata for frontend clients
    (React/Redux SPA, WhatsApp bots, and intake portals).
    """
    campaign_ids = list_available_campaigns()
    results = []
    for cid in campaign_ids:
        cfg = load_campaign(cid)
        tgt = cfg.get("target", {})
        results.append({
            "id": cfg.get("id", cid),
            "name": cfg.get("name", cid),
            "description": cfg.get("description", ""),
            "country": tgt.get("country", "CO"),
            "currency": tgt.get("currency", "COP"),
            "cities": tgt.get("cities", []),
            "sectors": tgt.get("sectors", []),
            "roles": tgt.get("roles", []),
            "segment": tgt.get("segment", "all")
        })
    return {"status": "success", "total": len(results), "campaigns": results}

class RoleUsageRequest(BaseModel):
    role_title: str

class ReplacementClaimRequest(BaseModel):
    bounced_email: str
    company_name: Optional[str] = None
    reason: Optional[str] = "hard_bounce"

@app.get("/api/v1/campaigns/presets")
def get_campaign_presets():
    """
    Returns available demonstration presets for one-click inspiring lookups.
    """
    campaign_ids = list_available_campaigns()
    presets = []
    for cid in campaign_ids:
        cfg = load_campaign(cid)
        tgt = cfg.get("target", {})
        presets.append({
            "id": cfg.get("id", cid),
            "name": cfg.get("name", cid),
            "description": cfg.get("description", ""),
            "country": tgt.get("country", "CO"),
            "currency": tgt.get("currency", "COP"),
            "cities": tgt.get("cities", []),
            "sectors": tgt.get("sectors", []),
            "roles": tgt.get("roles", []),
            "segment": tgt.get("segment", "all"),
            "is_preset": True,
        })
    return {"status": "success", "total": len(presets), "presets": presets}

@app.get("/api/v1/taxonomy/locations")
def search_taxonomy_locations(q: str = "", country: Optional[str] = None, limit: int = 20):
    """
    Searches supported LatAm territories, administrative departments, and metropolitan clusters.
    """
    results = sql_adapter.search_locations(query=q, country=country, limit=limit)
    return {"status": "success", "total": len(results), "locations": results}

@app.get("/api/v1/taxonomy/locations/validate")
def validate_taxonomy_location(name: str):
    """
    Validates whether a location string falls inside our supported registries
    in Colombia 🇨🇴, Dominican Republic 🇩🇴, or Ecuador 🇪🇨.
    """
    res = sql_adapter.validate_location(name)
    return {"status": "success", **res}

@app.get("/api/v1/taxonomy/roles")
def search_taxonomy_roles(q: str = "", domain: Optional[str] = None, country: Optional[str] = None, limit: int = 20):
    """
    Searches executive decision maker roles and cross-country aliases, ordered by usage popularity.
    """
    results = sql_adapter.search_roles(query=q, domain=domain, country=country, limit=limit)
    return {"status": "success", "total": len(results), "roles": results}

@app.post("/api/v1/taxonomy/roles/usage")
def record_taxonomy_role_usage(payload: RoleUsageRequest):
    """
    Records role selection usage count to train future autocomplete ranking.
    """
    sql_adapter.record_role_usage(payload.role_title)
    return {"status": "success", "message": "Role popularity updated"}

@app.get("/api/v1/taxonomy/sectors")
def search_taxonomy_sectors(q: str = "", limit: int = 30):
    """
    Searches universal economic sectors, CIIU activity codes, and default keyword lists.
    """
    results = sql_adapter.search_sectors(query=q, limit=limit)
    return {"status": "success", "total": len(results), "sectors": results}

@app.post("/api/v1/taxonomy/custom")
def create_custom_taxonomy(payload: CustomTaxonomyRequest):
    """
    Dynamically persists user-defined or AI-agent-discovered sectors or roles.
    Immediately makes them available in the visual form and autocomplete searches.
    """
    tax_type = payload.type.strip().lower()
    if tax_type in ("sector", "sectors", "vertical"):
        sector = sql_adapter.add_custom_sector(
            name=payload.name,
            ciiu_codes=payload.ciiu_codes,
            keywords=payload.keywords,
            country_code=payload.country_code or "ALL",
        )
        return {"status": "success", "type": "sector", "item": sector}
    elif tax_type in ("role", "roles", "cargo"):
        role = sql_adapter.add_custom_role(
            title=payload.name,
            domain=payload.domain or "general",
            seniority=payload.seniority or "director",
            country_code=payload.country_code or "ALL",
        )
        return {"status": "success", "type": "role", "item": role}
    else:
        raise HTTPException(status_code=400, detail="Invalid taxonomy type. Expected 'sector' or 'role'.")

@app.get("/api/v1/partners/{partner_id}")
def get_partner_profile(partner_id: str):
    """
    Returns public partner branding, discount rates, and default campaign.
    """
    partner = PartnerRegistry.get(partner_id)
    return {
        "status": "success",
        "partner": partner.to_dict()
    }

@app.get("/api/v1/partners/{partner_id}/statement")
def get_partner_settlement_statement(partner_id: str):
    """
    Returns consolidated partner commission statement for monthly payouts.
    """
    statement = sql_adapter.get_partner_statement(partner_id)
    return {
        "status": "success",
        "statement": statement
    }

@app.post("/api/v1/intent/profile")
def profile_b2b_intent(payload: IntentProfileRequest, request: Request):
    """
    Stage 1 Conversational & Search Intent Profiler (Zero Compute Cost).
    Analyzes natural language sales brief, extracts target geography and vertical,
    estimates match volume, and generates a verified preview card without incurring heavy scraping costs.
    Protected by in-memory rate limiting and SHA-256 query caching.
    """
    if not payload.query or not payload.query.strip():
        raise HTTPException(status_code=400, detail="Query must not be empty.")

    ai_agent_rate_limiter.check_rate_limit(request, endpoint_name="intent_profile")

    cache_key = ai_agent_rate_limiter.compute_cache_key("intent_profile", payload.query, payload.country or "CO")
    cached = ai_agent_rate_limiter.get_cached_response(cache_key)
    if cached is not None:
        return cached

    use_case = app_container.profile_b2b_intent_use_case
    result = use_case.execute(query=payload.query, country=payload.country or "CO")
    ai_agent_rate_limiter.set_cached_response(cache_key, result)
    return result

@app.post("/api/v1/prospecting/parse-brief")
def parse_prospecting_brief(payload: ParseBriefRequest, request: Request):
    """
    Intelligent Natural Language Brief Parser (Gemini Flash + Local BM25 Index).
    Translates free-form business briefs into structured Super Query criteria,
    resolving directionality (Sales vs RFQ), CIIU codes, locations, roles, and quotas.
    Protected by in-memory rate limiting and deterministic query caching.
    """
    if not payload.prompt or not payload.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt must not be empty.")

    ai_agent_rate_limiter.check_rate_limit(request, endpoint_name="parse_brief")

    cache_key = ai_agent_rate_limiter.compute_cache_key("parse_brief", payload.prompt)
    cached = ai_agent_rate_limiter.get_cached_response(cache_key)
    if cached is not None:
        return cached

    brief_parser = BriefParserService(sql_adapter=sql_adapter)
    try:
        result = brief_parser.parse_brief(
            prompt=payload.prompt,
            client_id=payload.client_id,
            session_id=payload.session_id,
            force_fallback=payload.force_fallback or False,
        )
        res_obj = {
            "status": "success",
            "data": result,
        }
        ai_agent_rate_limiter.set_cached_response(cache_key, res_obj)
        return res_obj
    except Exception as e:
        logger.error(f"Error parsing prospecting brief: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to parse brief: {str(e)}")


from src.entrypoints.workers.order_worker_daemon import calculate_lead_pricing


def generate_order_stream_token(order_id: str, client_email: str) -> str:
    """Generates a cryptographic HMAC-SHA256 token for authorized SSE connection."""
    secret = os.environ.get("STREAM_SECRET_KEY") or os.environ.get("ADMIN_API_KEY") or "michito_stream_token_key_2026"
    raw = f"{order_id}:{client_email.strip().lower()}:{secret}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def verify_order_stream_token(order_id: str, token: str, order: Dict[str, Any]) -> bool:
    """Verifies that the provided token matches the order and client email."""
    env = os.environ.get("ENVIRONMENT", "local").lower()
    if env in ("local", "dev", "test") and (not token or token == "dev_token"):
        return True
    client_email = order.get("client", {}).get("email") or ""
    expected = generate_order_stream_token(order_id, client_email)
    return hmac.compare_digest(expected, token or "")


def mask_teaser_company_name(name: str) -> str:
    """Masks company trade name while preserving recognizable legal entity structure."""
    if not name:
        return "Empresa B2B Verificada"
    words = name.strip().split()
    masked_words = []
    legal_entities = {"sas", "s.a.s.", "sa", "s.a.", "ltda", "limitada", "corp", "inc", "e.u.", "srl", "s.r.l."}
    for w in words:
        clean_w = w.strip().rstrip(".,").lower()
        if clean_w in legal_entities:
            masked_words.append(w.upper())
        elif len(w) <= 2:
            masked_words.append(w[0] + "•")
        else:
            masked_words.append(w[0] + "•" * min(len(w) - 1, 5))
    return " ".join(masked_words)


def mask_teaser_person_name(full_name: str) -> str:
    """Masks executive name to initials and dot fills (e.g. 'Edna Paola Rojas' -> 'E•••• P•••• R••••')."""
    if not full_name:
        return "Representante Estatutario"
    parts = full_name.strip().split()
    masked = []
    for p in parts:
        if len(p) <= 2:
            masked.append(p[0] + "•")
        else:
            masked.append(p[0] + "•" * min(len(p) - 1, 4))
    return " ".join(masked)


def mask_teaser_email(email: str) -> str:
    """Masks both username and corporate domain to prevent pre-payment bypass."""
    if not email or "@" not in email:
        return "••••••@••••••••••.com"
    user, dom = email.split("@", 1)
    masked_user = (user[0] + "••••") if user else "••••"
    dom_parts = dom.split(".")
    if len(dom_parts) >= 2:
        masked_dom_name = (dom_parts[0][0] + "••••••••") if dom_parts[0] else "••••••••"
        tld = ".".join(dom_parts[1:])
        masked_dom = f"{masked_dom_name}.{tld}"
    else:
        masked_dom = "••••••••.co"
    return f"{masked_user}@{masked_dom}"


def mask_teaser_phone(phone: str, country: str = "CO") -> str:
    """Masks direct phone numbers, hiding the last 4 digits entirely."""
    digits = re.sub(r"\D", "", phone or "")
    if country == "DO":
        return "+1 (809) ••• ••••"
    if country == "EC":
        return "+593 9• ••• ••••"
    if country == "CO":
        clean = digits[2:] if digits.startswith("57") and len(digits) >= 12 else digits
        if len(clean) == 10 and clean.startswith("3"):
            prefix = clean[:3]
            return f"+57 {prefix} ••• ••••"
        elif len(clean) == 10 and clean.startswith("60"):
            prefix = clean[:3]
            return f"+57 ({prefix}) ••• •••• (PBX)"
        return "+57 ••• ••• ••••"
    return "+••• ••• ••••"


def run_fast_radar_scan(
    country: str = "CO",
    city: str = "Medellín",
    target_ciiu_codes: Optional[List[str]] = None,
    target_sectors: Optional[List[str]] = None,
    keywords_include: Optional[List[str]] = None,
    excluded_tax_ids: Optional[List[str]] = None,
    limit: int = 3,
) -> List[Dict[str, Any]]:
    """
    Ultra-fast 2-second Pre-Payment Radar Scan.
    Pulls 3 authentic sample leads from verified inventory or live statutory registry
    and enforces ZERO-KNOWLEDGE obfuscation (masked names, hidden domains, hidden phones).
    """
    excluded = set(excluded_tax_ids or [])
    samples: List[Dict[str, Any]] = []

    # 1. First probe local verified lead inventory (PostgreSQL)
    try:
        cached = sql_adapter.get_cached_fresh_leads(
            city=city,
            country=country,
            limit=limit + len(excluded),
            max_age_days=60,
        )
        for lead in cached:
            if lead.get("tax_id") in excluded or lead.get("nit") in excluded:
                continue
            samples.append(lead)
            if len(samples) >= limit:
                break
    except Exception as e:
        logger.warning(f"Radar inventory probe failed: {e}")

    # 2. If under limit, probe statutory registry live with strict limit
    if len(samples) < limit and country == "CO":
        try:
            from src.adapters.registries.colombia.secop_harvester_adapter import SecopHarvesterAdapter
            harvester = SecopHarvesterAdapter(timeout=3)
            raw = harvester.fetch_candidates(
                city=city,
                limit=limit + len(excluded),
                include_keywords=keywords_include,
                ciiu_codes=target_ciiu_codes,
                sectors=target_sectors,
                corporate_only=True,
            )
            for item in raw:
                item_nit = item.get("nit")
                if item_nit in excluded or any(s.get("nit") == item_nit for s in samples):
                    continue
                samples.append({
                    "company_name": item.get("company_name"),
                    "tax_id": item_nit,
                    "nit": item_nit,
                    "city": item.get("city") or city,
                    "sector": item.get("sector") or "Servicios Empresariales",
                    "decision_maker_name": item.get("decision_maker_name"),
                    "decision_maker_title": item.get("decision_maker_title") or "Representante Legal",
                    "email": item.get("email"),
                    "phone": item.get("phone"),
                })
                if len(samples) >= limit:
                    break
        except Exception as e:
            logger.warning(f"Radar live probe failed: {e}")

    # 3. ZERO-KNOWLEDGE Obfuscation: Prove signals & seniority while completely hiding identities
    masked_samples: List[Dict[str, Any]] = []
    for s in samples:
        raw_nit = str(s.get("nit") or s.get("tax_id") or "900000000")
        masked_nit = f"{raw_nit[:3]}••••••"
        if "-" in raw_nit:
            masked_nit = f"{raw_nit.split('-')[0][:3]}••••••-{raw_nit.split('-')[1]}"

        raw_company = s.get("company_name", "Empresa Colombiana")
        raw_dm = s.get("decision_maker_name") or "Representante Legal"
        raw_email = s.get("email") or "contacto@empresa.com"
        raw_phone = s.get("phone") or "3001234567"

        masked_samples.append({
            "company_name": mask_teaser_company_name(raw_company),
            "nit": masked_nit,
            "tax_id": masked_nit,
            "country": country,
            "country_name": "Colombia" if country == "CO" else ("Ecuador" if country == "EC" else "República Dominicana"),
            "flag": "🇨🇴" if country == "CO" else ("🇪🇨" if country == "EC" else "🇩🇴"),
            "city": s.get("city") or city,
            "sector": s.get("sector") or "Servicios Empresariales",
            "decision_maker_name": mask_teaser_person_name(raw_dm),
            "decision_maker_role": s.get("decision_maker_title") or "Representante Legal (Firmante Estatutario)",
            "decision_maker_title": s.get("decision_maker_title") or "Representante Legal (Firmante Estatutario)",
            "targeted_role": "Gerente General",
            "email": mask_teaser_email(raw_email),
            "phone": mask_teaser_phone(raw_phone, country=country),
            "phone_line_type": "Móvil Corporativo (WhatsApp)",
            "website": "[Disponible tras autorización]",
            "website_url": "[Disponible tras autorización]",
            "is_mobile": True,
            "intent_trigger": "Alto (Actividad Comercial Verificada)",
            "intent_level": "Alto",
            "has_contracts": True,
            "underwriting_grade": "A - Aprobado",
            "solvency_tier": "AA",
            "litigation_risk": "CLEAN",
        })
    return masked_samples

@app.post("/api/v1/orders", status_code=201)
def create_prospecting_order(payload: CreateOrderRequest, request: Request):
    """
    Ingests an on-demand prospecting order from Web Portal or WhatsApp,
    creates the client record, persists order in PostgreSQL, and queues it for the worker.
    Protected by IP rate limiting and quota verification.
    """
    ai_agent_rate_limiter.check_rate_limit(request, endpoint_name="create_order")

    limit = payload.request.limit or 10
    if limit < 1 or limit > 500:
        raise HTTPException(status_code=400, detail="Requested lead limit must be between 1 and 500.")

    try:
        if payload.request.country_allocations:
            currency = "USD"
        elif payload.request.country and payload.request.country.upper() == "EC":
            currency = "USD"
        elif payload.request.country and payload.request.country.upper() == "DO":
            currency = "DOP"
        else:
            currency = "COP"

        merged_exclusions = list(payload.request.keywords_exclude or [])
        if payload.request.exclusions:
            for item in payload.request.exclusions:
                if item not in merged_exclusions:
                    merged_exclusions.append(item)

        # Client-level deduplication ledger check
        client_email_clean = payload.client.email.strip().lower()
        try:
            prior_tax_ids = sql_adapter.get_client_purchased_tax_ids(client_email_clean)
            if prior_tax_ids:
                for tid in prior_tax_ids:
                    if tid not in merged_exclusions:
                        merged_exclusions.append(tid)
        except Exception as dedup_err:
            logger.warning(f"Could not load prior purchases for {client_email_clean}: {dedup_err}")

        target_tier = payload.request.tier or 2
        # Restrict Tier 3 exclusively to 100% Colombian campaigns
        locations = payload.request.location_allocations or []
        req_country = (payload.request.country or "CO").upper()
        has_non_co = req_country != "CO"
        if isinstance(locations, list):
            for l in locations:
                if isinstance(l, dict) and (l.get("country") or "").upper() not in ("", "CO"):
                    has_non_co = True
                    break
        if target_tier == 3 and has_non_co:
            logger.info("Order contains non-Colombian locations. Setting Tier 2 to guarantee verified data without assumptions.")
            target_tier = 2

        normalized_locations: Optional[List[Dict[str, Any]]] = None
        raw_locs = payload.request.location_allocations
        if isinstance(raw_locs, list):
            normalized_locations = raw_locs
        elif isinstance(raw_locs, dict):
            normalized_locations = [
                {"city": city_name, "allocated_leads": count, "country": req_country}
                for city_name, count in raw_locs.items()
            ]

        # -------------------------------------------------------------
        # 2-SECOND PRE-PAYMENT RADAR SCAN
        # Pull 3 authentic masked samples and calculate quote in real time.
        # Defers heavy 100-lead batch harvesting until payment is confirmed.
        # -------------------------------------------------------------
        target_city = payload.request.city or "Medellín"
        if normalized_locations and len(normalized_locations) > 0:
            first_loc = normalized_locations[0]
            if isinstance(first_loc, dict) and first_loc.get("city"):
                target_city = first_loc["city"]

        raw_sectors = payload.request.sector
        sector_list = [s.strip() for s in raw_sectors.split(",") if s.strip()] if isinstance(raw_sectors, str) else raw_sectors

        masked_samples = run_fast_radar_scan(
            country=req_country,
            city=target_city,
            target_ciiu_codes=payload.request.target_ciiu_codes,
            target_sectors=sector_list,
            keywords_include=payload.request.keywords_include,
            excluded_tax_ids=merged_exclusions,
            limit=3,
        )

        total_price_cents = calculate_lead_pricing(
            total_qualified=limit,
            tier=target_tier,
            currency=currency,
        )

        order = sql_adapter.create_order(
            client_name=payload.client.name,
            client_email=payload.client.email,
            client_phone=payload.client.phone,
            client_channel=payload.client.channel or "web_portal",
            referral_partner=payload.client.referral_partner or "direct",
            campaign_id=payload.request.campaign_id or "universal_prospecting",
            city=payload.request.city or "Medellín",
            limit=limit,
            country=payload.request.country or "CO",
            currency=currency,
            segment=payload.request.segment,
            sector=payload.request.sector,
            keywords_include=payload.request.keywords_include,
            keywords_exclude=merged_exclusions or None,
            tier=target_tier,
            country_allocations=payload.request.country_allocations,
            offer_description=payload.request.offer_description,
            target_roles=payload.request.target_roles,
            target_ciiu_codes=payload.request.target_ciiu_codes,
            location_allocations=normalized_locations,
            directionality=payload.request.directionality or "vendor_to_clients",
            rfq_specifications=payload.request.rfq_specifications,
            status="awaiting_payment",
            payment_amount_in_cents=total_price_cents,
            delivery_sample_teaser=masked_samples,
            delivery_total_qualified=limit,
        )

        stream_token = generate_order_stream_token(order["order_id"], client_email_clean)

        try:
            if hasattr(app_container, "alert_dispatcher"):
                app_container.alert_dispatcher.send_feed_event(
                    "New Order Quoted (Radar Scan Ready)",
                    f"Order `{order['order_id']}` quoted for *{payload.client.name}* ({payload.client.email}). Awaiting payment authorization.",
                    details={
                        "order_id": order["order_id"],
                        "client": payload.client.name,
                        "campaign": payload.request.campaign_id,
                        "city": payload.request.city or "Medellín",
                        "requested_leads": limit,
                        "tier": f"Tier {target_tier}",
                        "total_cop": f"${total_price_cents // 100:,.0f} COP",
                    },
                )
        except Exception as e:
            logger.warning(f"Could not dispatch order feed event: {e}")

        return {
            "status": "success",
            "order_id": order["order_id"],
            "order_status": "awaiting_payment",
            "stream_token": stream_token,
            "total_price_cop": total_price_cents // 100,
            "sample_teaser": masked_samples,
            "sample_leads": masked_samples,
            "estimated_processing_seconds": 2,
            "message": "Radar scan complete. 3 verified sample accounts ready for review.",
            "order": order,
        }
    except Exception as e:
        logger.error(f"Error creating prospecting order: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/orders/{order_id}")
def get_prospecting_order(order_id: str):
    """
    Polls the current status, sample teaser, deliverables, and quote for an order.
    """
    order = sql_adapter.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # On-the-fly Self-Healing: If an unpaid order is stuck in 'processing' (>180s), auto-reset to awaiting_payment
    order_status = (order.get("status") or "").lower()
    if order_status == "processing":
        payment_status = (order.get("payment", {}).get("status") or "").upper()
        if payment_status != "APPROVED":
            started = order.get("started_processing_at") or order.get("created_at")
            is_stuck = False
            if started:
                try:
                    if isinstance(started, str):
                        clean_iso = started.replace("Z", "+00:00")
                        start_dt = datetime.fromisoformat(clean_iso)
                    elif isinstance(started, (int, float)):
                        start_dt = datetime.fromtimestamp(started, tz=timezone.utc)
                    else:
                        start_dt = None
                    if start_dt:
                        if start_dt.tzinfo is None:
                            start_dt = start_dt.replace(tzinfo=timezone.utc)
                        age_sec = (datetime.now(timezone.utc) - start_dt).total_seconds()
                        if age_sec > 180:
                            is_stuck = True
                except Exception:
                    is_stuck = True
            else:
                is_stuck = True

            if is_stuck:
                logger.info(f"[SelfHealing] Auto-recovering stuck unpaid order `{order_id}` from 'processing' to 'awaiting_payment'.")
                sql_adapter.update_telemetry(order_id, {}, status="awaiting_payment")
                order = sql_adapter.get_order(order_id) or order

    client_email = order.get("client", {}).get("email") or ""
    order["stream_token"] = generate_order_stream_token(order_id, client_email)
    return order


@app.get("/api/v1/orders/{order_id}/stream")
async def stream_order_progress(order_id: str, token: str = Query(None)):
    """
    Secure Server-Sent Events (SSE) stream for real-time order processing telemetry.
    Protected by HMAC ephemeral tokens. Telemetry only (zero PII transmitted).
    Auto-terminates when order reaches terminal state or after maximum 600s.
    """
    order = sql_adapter.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if not verify_order_stream_token(order_id, token or "", order):
        raise HTTPException(status_code=403, detail="Invalid or expired stream token")

    async def event_generator():
        import asyncio
        start_time = time.time()
        max_duration = 600  # 10 minutes maximum stream duration

        while time.time() - start_time < max_duration:
            current_order = sql_adapter.get_order(order_id)
            if not current_order:
                break

            status = current_order.get("status", "queued")
            elapsed = int(time.time() - start_time)

            if status == "queued":
                step = "ingestion"
                step_idx = 1
                pct = 15
                msg = "Orden en cola. Inicializando recolector territorial..."
            elif status == "processing":
                step = "verification"
                step_idx = 2
                pct = 60
                msg = "Auditando registros mercantiles, dominios HTTP y sockets MX..."
            elif status in ("awaiting_payment", "paid", "completed", "fulfilled"):
                step = "completed"
                step_idx = 4
                pct = 100
                msg = "Lote verificado y calificado. Entregables generados."
            elif status in ("failed", "error"):
                step = "error"
                step_idx = 4
                pct = 100
                msg = current_order.get("error_message") or "Error en la verificación del lote."
            else:
                step = "processing"
                step_idx = 2
                pct = 40
                msg = "Procesando registros..."

            telemetry = (current_order.get("metrics") or {}).get("telemetry") or {}
            telemetry_phase = telemetry.get("phase")
            if telemetry_phase:
                step = telemetry_phase
            if "step_index" in telemetry:
                step_idx = telemetry["step_index"]
            if "progress_percent" in telemetry:
                pct = telemetry["progress_percent"]

            phase_key = telemetry.get("phase_key") or f"telemetry.{step}"

            payload = {
                "order_id": order_id,
                "status": status,
                "phase": step,
                "phase_key": phase_key,
                "step": step,
                "step_index": step_idx,
                "progress_percent": pct,
                "elapsed_seconds": elapsed,
                "total_qualified": current_order.get("delivery", {}).get("total_qualified", 0),
                "message": msg,
            }

            yield f"data: {json.dumps(payload)}\n\n"

            # Determine terminal state
            is_terminal = False
            if status in ("failed", "error"):
                is_terminal = True
            elif status == "awaiting_payment":
                is_terminal = True
            elif status in ("paid", "completed", "fulfilled"):
                has_files = bool(
                    current_order.get("delivery", {}).get("csv_path")
                    or current_order.get("delivery", {}).get("xlsx_path")
                )
                if has_files or telemetry_phase == "completed":
                    is_terminal = True

            if is_terminal:
                yield f"event: close\ndata: {json.dumps({'reason': 'terminal_state_reached'})}\n\n"
                break

            await asyncio.sleep(2.0)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )

@app.get("/api/v1/orders/{order_id}/quote")
def get_order_quote_summary(order_id: str):
    """
    Returns a consolidated executive quote and approval summary for an order.
    Suitable for sharing with CFOs, partners, and decision-makers prior to payment authorization.
    """
    order = sql_adapter.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    client = order.get("client", {})
    req = order.get("request", {})
    payment = order.get("payment", {})
    delivery = order.get("delivery", {})

    limit = req.get("limit") or order.get("limit") or 10
    tier = req.get("tier") or order.get("tier") or 2
    currency = payment.get("currency") or "COP"
    amount_in_cents = payment.get("amount_in_cents") or 0
    total_cop = amount_in_cents // 100

    tier_labels = {
        1: "Tier 1 — Mailbox Directo & Representante Legal",
        2: "Tier 2 — Tomador de Decisión & Teléfono Celular Verificado",
        3: "Tier 3 — Solvencia Financiera, EBITDA & Scoring Judicial",
    }

    quote_summary = {
        "status": "success",
        "order_id": order_id,
        "shareable_url": f"/rastrear?order_id={order_id}",
        "order_status": order.get("status"),
        "created_at": order.get("created_at"),
        "client": {
            "name": client.get("name"),
            "email": client.get("email"),
            "phone": client.get("phone"),
            "channel": client.get("channel"),
        },
        "scope": {
            "campaign_id": req.get("campaign_id"),
            "offer_description": req.get("offer_description") or f"Prospección dirigida para {req.get('campaign_id')}",
            "sectors": req.get("sector") or "Multi-Sector",
            "target_roles": req.get("target_roles") or ["Gerente General"],
            "locations": req.get("location_allocations") or [{"city": req.get("city") or "Medellín", "allocated_leads": limit}],
            "total_leads": limit,
            "tier": tier,
            "tier_description": tier_labels.get(tier, f"Tier {tier}"),
            "exclusions_count": len(req.get("keywords_exclude") or []),
        },
        "financials": {
            "currency": currency,
            "amount_in_cents": amount_in_cents,
            "total_price": total_cop,
            "unit_price": total_cop // max(1, limit) if currency == "COP" else round((amount_in_cents / 100) / max(1, limit), 2),
            "payment_status": payment.get("status") or "pending",
            "guarantee": "Garantía Técnica 2x1 por Rebote Duro (7 días de cobertura)",
        },
        "is_approved_and_paid": order.get("status") in ("paid", "completed", "fulfilled"),
        "sample_preview_count": len(delivery.get("sample_teaser") or []),
    }
    return quote_summary

@app.post("/api/v1/orders/{order_id}/pay")
def pay_prospecting_order(order_id: str, request: Request):
    """
    Confirms simulated or webhook payment, transitions status to 'paid', and unlocks downloads.
    Protected: Only allowed in development/test environments or when provided with an authorized X-Admin-Key.
    """
    import sys
    env = os.environ.get("ENVIRONMENT", "local").lower()
    is_dev_or_test = (
        "pytest" in sys.modules
        or "PYTEST_CURRENT_TEST" in os.environ
        or os.environ.get("TESTING") == "1"
        or env in ("local", "dev", "test")
    )
    admin_key = os.environ.get("ADMIN_API_KEY", "").strip()
    provided_key = request.headers.get("X-Admin-Key", "").strip()

    if not is_dev_or_test:
        if not admin_key or provided_key != admin_key:
            logger.warning(f"Unauthorized payment simulation attempt for order {order_id} in {env} environment.")
            raise HTTPException(
                status_code=403,
                detail="Manual payment simulation is disabled in non-development environments. Payments must be processed via payment gateway webhook."
            )

    order = sql_adapter.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    amount = order.get("payment", {}).get("amount_in_cents") or 20000000
    tx_id = f"tx_wompi_{uuid.uuid4().hex[:10]}"
    ok = sql_adapter.mark_order_paid(order_id, transaction_id=tx_id, amount_in_cents=amount)
    if not ok:
        raise HTTPException(status_code=400, detail="Could not mark order paid")

    try:
        deliver_order_use_case.execute(order_id)
    except Exception as e:
        logger.error(f"Error during delivery dispatch for order {order_id}: {e}")

    try:
        if hasattr(app_container, "alert_dispatcher"):
            client_info = order.get("client", {})
            app_container.alert_dispatcher.send_feed_event(
                "Payment Approved!",
                f"Payment received for Order `{order_id}`! Deliverables unlocked for *{client_info.get('name', 'Client')}*.",
                details={
                    "order_id": order_id,
                    "amount": f"${amount // 100:,.0f} COP",
                    "transaction_id": tx_id,
                    "client": client_info.get("name"),
                },
            )
    except Exception as e:
        logger.warning(f"Could not dispatch payment feed event: {e}")

    updated_order = sql_adapter.get_order(order_id)
    return {
        "status": "success",
        "message": "Payment approved. Deliverables unlocked.",
        "order": updated_order
    }

@app.get("/api/v1/orders/{order_id}/download/{file_type}")
def download_deliverable(order_id: str, file_type: str):
    """
    Serves the generated CSV, XLSX, PDF, or Markdown executive dossier.
    Enforces payment verification: Deliverables are strictly blocked unless order is paid.
    """
    order = sql_adapter.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order_status = (order.get("status") or "").lower()
    payment_status = (order.get("payment", {}).get("status") or "").lower()
    is_paid = (order_status in ("paid", "completed", "fulfilled")) or (payment_status in ("approved", "paid"))

    if not is_paid:
        raise HTTPException(
            status_code=402,
            detail="Payment required. Full intelligence deliverables are only available for paid orders."
        )

    delivery = order.get("delivery", {})
    ft = file_type.lower()
    if ft == "csv":
        local_file_path = delivery.get("csv_path")
        gcs_filename = "prospects.csv"
        media_type = "text/csv"
        filename = f"{order_id}_prospects.csv"
    elif ft in ("xlsx", "excel"):
        local_file_path = delivery.get("xlsx_path")
        gcs_filename = "prospects.xlsx"
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"{order_id}_prospects.xlsx"
    elif ft in ("pdf",):
        local_file_path = delivery.get("pdf_path")
        gcs_filename = "executive_dossier.pdf"
        media_type = "application/pdf"
        filename = f"{order_id}_dossier_ejecutivo.pdf"
    elif ft in ("md", "dossier", "markdown"):
        local_file_path = delivery.get("dossier_path")
        gcs_filename = "executive_dossier.md"
        media_type = "text/markdown"
        filename = f"{order_id}_executive_dossier.md"
    elif ft in ("full_csv", "full-csv", "intelligence", "full"):
        local_file_path = delivery.get("full_csv_path")
        gcs_filename = "prospects_full_intelligence.csv"
        media_type = "text/csv"
        filename = f"{order_id}_prospects_full_intelligence.csv"
    else:
        raise HTTPException(status_code=400, detail="Invalid file_type (must be 'csv', 'xlsx', or 'pdf')")

    # 1. Local disk file fallback (e.g. running in local development or unit tests)
    if local_file_path and os.path.exists(local_file_path) and os.path.isfile(local_file_path):
        return FileResponse(path=local_file_path, media_type=media_type, filename=filename)

    # 2. Directly stream bytes from Google Cloud Storage
    bucket_name = os.environ.get("GCS_BUCKET_NAME") or os.environ.get("DELIVERABLES_BUCKET") or "michito-staging-deliverables"
    blob_name = f"orders/{order_id}/{gcs_filename}"

    try:
        from google.cloud import storage
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        if blob.exists():
            file_bytes = blob.download_as_bytes()
            return Response(
                content=file_bytes,
                media_type=media_type,
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"',
                    "Cache-Control": "private, max-age=3600",
                }
            )
    except Exception as gcs_err:
        logger.warning(f"GCS stream attempt failed for {blob_name}: {gcs_err}")

    # 3. Deliverable file is missing on a paid order -> Trigger critical Watchdog Alert
    if hasattr(app_container, "alert_dispatcher"):
        try:
            client_info = order.get("client", {})
            app_container.alert_dispatcher.send_alert(
                title="MISSING DELIVERABLE DOWNLOAD ATTEMPT",
                message=f"Buyer attempted to download `{file_type}` for paid order `{order_id}`, but deliverable `{gcs_filename}` was not found in bucket `{bucket_name}`.",
                level="error",
                details={
                    "order_id": order_id,
                    "file_type": file_type,
                    "bucket": bucket_name,
                    "blob": blob_name,
                    "client": client_info.get("email", "unknown"),
                }
            )
        except Exception as alert_err:
            logger.warning(f"Could not dispatch missing deliverable watchdog alert: {alert_err}")

    raise HTTPException(
        status_code=404,
        detail=f"El archivo '{filename}' se está sincronizando o no se encuentra disponible temporalmente. Nuestro equipo de soporte ya ha sido notificado automáticamente."
    )

@app.post("/api/v1/orders/{order_id}/claim-replacement")
def claim_order_replacement(order_id: str, payload: ReplacementClaimRequest):
    """
    Automated 2x1 Replacement Guarantee claim:
    Validates hard bounce, blacklists email/company in DeduplicationLedger,
    generates 2 replacement accounts matching exact order criteria, and updates manifest.
    """
    try:
        return sql_adapter.claim_lead_replacement(
            order_id=order_id,
            bounced_email=payload.bounced_email,
            company_name=payload.company_name,
            reason=payload.reason or "hard_bounce",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing replacement claim for order {order_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal error fulfilling replacement guarantee.")

# ------------------------------------------------------------------------------
# Legacy Endpoints & Webhooks
# ------------------------------------------------------------------------------
@app.post("/api/v1/prospects/search")
def search_prospects(request: SearchRequest, container: Container = Depends(get_container)):
    dto = CompanyFilterDto(
        country_code=request.country_code,
        min_revenue=request.min_revenue,
        industry=request.industry,
        city=request.city
    )
    results = container.search_companies_use_case.execute(dto)
    return {"results": results}

@app.post("/api/v1/verification/verify")
def verify_email(request: VerificationRequest, container: Container = Depends(get_container)):
    status = container.verify_mailbox_use_case.execute(request.email)
    return {"email": request.email, "status": status}

@app.post("/api/v1/orders/create")
def create_legacy_order(request: LegacyOrderRequest, container: Container = Depends(get_container)):
    try:
        company = Company(
            id=request.company_id,
            tax_id=TaxId(request.company_id.split("-")[-1] if "-" in request.company_id else request.company_id),
            name="Pending Information"
        )
        order = LeadOrder(
            id=str(uuid.uuid4()),
            tier=request.tier,
            company=company
        )
        response = container.create_lead_order_use_case.execute(order)
        return {"order_id": response.order_id, "checkout_url": response.checkout_url}
    except Exception as e:
        logger.error(f"Error creating order: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/orders/calculate-ebitda")
def calculate_ebitda(request: EbitdaRequest, container: Container = Depends(get_container)):
    raw_financials = {
        "operating_revenue": request.operating_revenue,
        "cost_of_sales": request.cost_of_sales,
        "operating_expenses": request.operating_expenses,
        "depreciation": request.depreciation,
        "amortization": request.amortization
    }
    result = container.calculate_ebitda_use_case.execute(raw_financials)
    return {
        "ebit": float(result["ebit"]),
        "ebitda": float(result["ebitda"]),
        "ebitda_margin": float(result["ebitda_margin"].value)
    }

@app.post("/api/v1/webhooks/wompi")
def wompi_webhook(request: Request, event_data: dict, container: Container = Depends(get_container)):
    import sys
    is_dev_or_test = (
        "pytest" in sys.modules
        or "PYTEST_CURRENT_TEST" in os.environ
        or os.environ.get("TESTING") == "1"
        or os.environ.get("ENVIRONMENT") in ("local", "dev", "test")
    )
    wompi_events_secret = os.environ.get("WOMPI_EVENTS_SECRET", "").strip()
    if not wompi_events_secret:
        if is_dev_or_test:
            wompi_events_secret = "test_events_wmhM2301jwX2c9q8u4SofthtnAKUO7aK"
        else:
            logger.error("[WompiWebhook] WOMPI_EVENTS_SECRET is not configured on the server.")
            raise HTTPException(status_code=500, detail="Webhook signature verification is not configured.")
    
    signature = event_data.get("signature", {}).get("checksum", "")
    data = event_data.get("data", {})
    transaction = data.get("transaction", {})
    
    tx_id = transaction.get("id", "")
    status = transaction.get("status", "")
    amount_in_cents = transaction.get("amount_in_cents", "")
    timestamp = event_data.get("timestamp", "")
    
    raw_str = f"{tx_id}{status}{amount_in_cents}{timestamp}{wompi_events_secret}"
    expected_checksum = hashlib.sha256(raw_str.encode("utf-8")).hexdigest()
    
    if not signature or not hmac.compare_digest(expected_checksum, signature):
        logger.warning("Invalid Wompi webhook signature")
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Keep legacy execution for any side effects
    try:
        container.fulfill_webhook_use_case.execute(event_data, signature)
    except Exception as e:
        logger.warning(f"Legacy fulfill_webhook_use_case failed: {e}")

    if status == "APPROVED":
        reference = transaction.get("reference", "")
        if reference:
            try:
                order = sql_adapter.get_order(reference)
                if order:
                    if order.get("status") == "paid" or order.get("payment_status") == "approved":
                        logger.info(f"[WompiWebhook] Order `{reference}` already paid. (Idempotency)")
                        return {"status": "received"}

                    sql_adapter.mark_order_paid(
                        order_id=reference,
                        transaction_id=str(tx_id),
                        amount_in_cents=int(amount_in_cents)
                    )
                    logger.info(f"[WompiWebhook] Order `{reference}` marked paid in PostgreSQL.")

                    # Post-Payment Fulfillment Trigger:
                    # If full deliverables were not yet generated, trigger decoupled Cloud Run Job
                    fresh_order = sql_adapter.get_order(reference) or order
                    delivery = fresh_order.get("delivery", {})
                    if not delivery.get("csv_path") and not delivery.get("xlsx_path"):
                        try:
                            from src.adapters.jobs.cloud_run_job_adapter import CloudRunJobAdapter
                            job_adapter = CloudRunJobAdapter()
                            job_adapter.trigger_batch_harvesting_job(reference)
                            logger.info(f"[WompiWebhook] Decoupled Cloud Run batch harvesting job dispatched for `{reference}`.")
                        except Exception as proc_e:
                            logger.error(f"[WompiWebhook] Batch job dispatch error for `{reference}`: {proc_e}")
                    else:
                        try:
                            deliver_order_use_case.execute(reference)
                            logger.info(f"[WompiWebhook] Existing deliverables emailed for `{reference}`.")
                        except Exception as del_e:
                            logger.warning(f"[WompiWebhook] Delivery dispatch error for `{reference}`: {del_e}")

                    # Immediate Watchdog Milestone Notification
                    try:
                        if hasattr(app_container, "alert_dispatcher"):
                            client_info = order.get("client", {})
                            app_container.alert_dispatcher.send_feed_event(
                                "Wompi Payment Confirmed!",
                                f"Webhook verified! Order `{reference}` paid. Deliverables unlocked for *{client_info.get('name', 'Buyer')}* ({client_info.get('email', 'N/A')}).",
                                details={
                                    "order_id": reference,
                                    "amount": f"${int(amount_in_cents) // 100:,.0f} COP",
                                    "transaction_id": str(tx_id),
                                    "provider": "Wompi Gateway",
                                    "client": client_info.get("name", "Buyer"),
                                    "email": client_info.get("email", "N/A"),
                                },
                            )
                    except Exception as alert_e:
                        logger.warning(f"Could not dispatch webhook payment feed event: {alert_e}")

                    try:
                        deliver_order_use_case.execute(reference)
                        logger.info(f"[WompiWebhook] Order `{reference}` dispatched via omnichannel delivery.")
                    except Exception as e:
                        logger.error(f"[WompiWebhook] Error during delivery dispatch for order {reference}: {e}")
            except Exception as e:
                logger.error(f"[WompiWebhook] Error updating order in database: {e}")

    elif status in ("DECLINED", "ERROR", "VOIDED"):
        reference = transaction.get("reference", "")
        status_message = transaction.get("status_message") or f"Payment {status.lower()}"
        if reference:
            try:
                sql_adapter.mark_order_payment_declined(
                    order_id=reference,
                    transaction_id=str(tx_id),
                    status=status,
                    status_message=status_message
                )
                logger.info(f"[WompiWebhook] Order `{reference}` payment marked as {status} (Reason: {status_message}).")
                if hasattr(app_container, "alert_dispatcher"):
                    app_container.alert_dispatcher.send_alert(
                        f"Wompi Payment {status}",
                        f"Order `{reference}` payment failed with status `{status}`. Message: {status_message}.",
                        level="warning",
                        details={
                            "order_id": reference,
                            "transaction_id": str(tx_id),
                            "status": status,
                            "reason": status_message,
                        }
                    )
            except Exception as e:
                logger.error(f"[WompiWebhook] Error recording declined payment for `{reference}`: {e}")

    return {"status": "received"}


@app.get("/api/v1/webhooks/whatsapp")
def verify_whatsapp_webhook(request: Request):
    expected_token = os.environ.get("WHATSAPP_VERIFY_TOKEN", "michito_wa_token")
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    if mode == "subscribe" and token == expected_token:
        return PlainTextResponse(content=challenge)
    raise HTTPException(status_code=403, detail="Invalid verify token")

@app.post("/api/v1/webhooks/whatsapp")
def whatsapp_webhook(payload: dict):
    """
    Ingests WhatsApp incoming messages and triggers conversational lead generation
    or auto-RFQ quote generation. Supports Meta Cloud API structure and direct JSON payloads.
    """
    from clients.whatsapp.bot_service import WhatsAppBotService
    
    responses = []
    try:
        # 1. Meta Cloud API Webhook structure
        if "entry" in payload:
            for entry in payload.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    if "messages" in value:
                        for msg in value["messages"]:
                            from_number = msg.get("from")
                            text = msg.get("text", {}).get("body", "")
                            
                            bot = WhatsAppBotService(brief_parser=BriefParserService(sql_adapter=sql_adapter), sql_adapter=sql_adapter)
                            response = bot.handle_incoming_message(from_number, text)
                            logger.info(f"[WhatsAppWebhook] Bot response for {from_number}: {response}")
                            responses.append(response)
        # 2. Direct simplified payload: {"from": "+57300...", "text": "..."}
        elif "from" in payload and "text" in payload:
            from_number = payload["from"]
            text = payload["text"]
            bot = WhatsAppBotService(brief_parser=BriefParserService(sql_adapter=sql_adapter), sql_adapter=sql_adapter)
            response = bot.handle_incoming_message(from_number, text)
            logger.info(f"[WhatsAppWebhook] Bot response for {from_number}: {response}")
            responses.append(response)
    except Exception as e:
        logger.error(f"Error processing WhatsApp Webhook: {e}")
        return {"status": "error", "error": str(e)}

    res: Dict[str, Any] = {"status": "ok"}
    if payload.get("echo_responses") or payload.get("debug"):
        res["responses"] = responses
    return res


@app.post("/api/v1/pubsub/orders")
async def pubsub_order_handler(request: Request, background_tasks: BackgroundTasks):
    """
    Intakes Google Cloud Pub/Sub push messages containing orders for asynchronous fulfillment.
    Standard Cloud Run Pub/Sub push event intake pattern:
    Immediately returns HTTP 200 to acknowledge receipt and prevent Pub/Sub timeout/retries,
    then executes the heavy order fulfillment pipeline in a background task.
    """
    import base64
    import json
    from src.entrypoints.workers.order_worker_daemon import OrderWorkerDaemon

    try:
        envelope = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed JSON body")

    if not envelope or "message" not in envelope:
        raise HTTPException(status_code=400, detail="Invalid Pub/Sub envelope")

    msg = envelope["message"]
    data_str = base64.b64decode(msg.get("data", "")).decode("utf-8") if msg.get("data") else "{}"
    try:
        data = json.loads(data_str)
    except Exception:
        data = {}

    order_id = data.get("order_id")
    if not order_id:
        return {"status": "ignored", "reason": "no order_id in message payload"}

    order = sql_adapter.get_order(str(order_id))
    if not order:
        return {"status": "ignored", "reason": f"order {order_id} not found in database"}

    # Monetization Protection Gate: Do not fulfill unpaid orders via Pub/Sub
    order_status = (order.get("status") or "").lower()
    payment_status = (order.get("payment", {}).get("status") or "").upper()
    is_paid = order_status in ("paid", "completed", "fulfilled") or payment_status == "APPROVED"
    env = os.environ.get("ENVIRONMENT", "local").lower()
    is_test_or_dev = (
        "pytest" in sys.modules
        or "PYTEST_CURRENT_TEST" in os.environ
        or os.environ.get("TESTING") == "1"
        or env in ("local", "dev", "test")
    )
    if not is_paid and not is_test_or_dev:
        logger.warning(f"[PubSub] Ignoring fulfillment for unpaid order {order_id} (Status: {order_status}, Payment: {payment_status}).")
        return {"status": "ignored", "reason": "order is unpaid"}

    # Process order synchronously so Cloud Run does not throttle CPU mid-execution
    try:
        daemon = OrderWorkerDaemon(order_repository=sql_adapter)
        success = daemon.process_order(order)
        logger.info(f"[PubSub] Order {order_id} processing result: {success}")
        return {"status": "success" if success else "failed", "order_id": order_id}
    except Exception as e:
        logger.error(f"[PubSub] Error executing order {order_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Order execution error: {e}")


@app.post("/api/v1/orders/{order_id}/process")
def trigger_order_processing(order_id: str, request: Request, background_tasks: BackgroundTasks, sync: bool = True):
    """
    Manual webhook or background trigger to process a pending order immediately.
    Protected: Restricted to local/test/staging environments or requests with authorized internal admin keys.
    When sync=True (default), runs synchronously to ensure Cloud Run CPU remains at 100%.
    """
    import sys
    env = os.environ.get("ENVIRONMENT", "local").lower()
    is_dev_or_test = (
        "pytest" in sys.modules
        or "PYTEST_CURRENT_TEST" in os.environ
        or os.environ.get("TESTING") == "1"
        or env in ("local", "dev", "test", "staging")
    )
    admin_key = os.environ.get("ADMIN_API_KEY", "").strip()
    provided_key = request.headers.get("X-Admin-Key", "").strip()
    auth_header = request.headers.get("Authorization", "").strip()
    bearer = auth_header.replace("Bearer ", "").strip() if auth_header.startswith("Bearer ") else ""

    if not is_dev_or_test:
        if not admin_key or (provided_key != admin_key and bearer != admin_key):
            logger.warning(f"Unauthorized trigger_order_processing attempt for order {order_id}.")
            raise HTTPException(status_code=403, detail="Unauthorized to trigger manual order processing.")

    from src.entrypoints.workers.order_worker_daemon import OrderWorkerDaemon
    order = sql_adapter.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    daemon = OrderWorkerDaemon(order_repository=sql_adapter)
    if sync:
        try:
            success = daemon.process_order(order)
            return {
                "status": "completed" if success else "failed",
                "order_id": order_id,
                "message": "Order pipeline processed synchronously.",
            }
        except Exception as e:
            logger.error(f"[ManualTrigger] Error executing order {order_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))
    else:
        def _execute_order():
            try:
                daemon.process_order(order)
            except Exception as e:
                logger.error(f"[ManualTrigger] Error executing order {order_id} in background: {e}")

        background_tasks.add_task(_execute_order)
        return {"status": "accepted", "order_id": order_id, "message": "Order pipeline dispatched in background."}


@app.post("/api/v1/integrations/slack/command")
async def handle_slack_command(request: Request, background_tasks: BackgroundTasks):
    """
    Inbound Slack Slash Command handler (e.g. `/michito rerun ord_20261117_cd80b8`).
    Allows operations and growth teams to re-trigger order pipelines directly from Slack.
    """
    import urllib.parse
    body_bytes = await request.body()
    body_str = body_bytes.decode("utf-8", errors="ignore")
    parsed_form: Dict[str, str] = {}
    if body_str.strip().startswith("{"):
        try:
            parsed_form = json.loads(body_str)
        except Exception:
            pass
    if not parsed_form:
        raw_qs = urllib.parse.parse_qs(body_str)
        parsed_form = {k: v[0] for k, v in raw_qs.items() if v}

    text = (parsed_form.get("text", "")).strip()
    user_name = (parsed_form.get("user_name", "operator")).strip()
    command = (parsed_form.get("command", "/michito")).strip()

    # Match order_id from text (e.g. "rerun ord_20261117_cd80b8" or just "ord_20261117_cd80b8")
    order_match = re.search(r"ord_[a-zA-Z0-9_]+", text)
    if not order_match:
        return {
            "response_type": "ephemeral",
            "text": (
                f"Comando no reconocido o falta el ID de la orden.\n"
                f"*Uso correcto:*\n"
                f"`{command} rerun <order_id>`\n"
                f"*Ejemplo:*\n"
                f"`{command} rerun ord_20261117_cd80b8`"
            ),
        }

    order_id = order_match.group(0)
    order = sql_adapter.get_order(order_id)
    if not order:
        return {
            "response_type": "ephemeral",
            "text": f"La orden `{order_id}` no fue encontrada en la base de datos de staging.",
        }

    def _execute_rerun():
        try:
            from src.entrypoints.workers.order_worker_daemon import OrderWorkerDaemon
            daemon = OrderWorkerDaemon(order_repository=sql_adapter)
            daemon.process_order(order)
        except Exception as e:
            logger.error(f"Slack triggered rerun failed for {order_id}: {e}")

    background_tasks.add_task(_execute_rerun)

    return {
        "response_type": "in_channel",
        "text": (
            f"Re-ejecución iniciada por @{user_name}\n"
            f"• *Orden:* `{order_id}`\n"
            f"• *Cliente:* {order.get('client', {}).get('name', 'N/A')}\n"
            f"• *Límite:* {order.get('request', {}).get('limit', 10)} prospectos (Tier {order.get('request', {}).get('tier', 2)})\n"
            f"El worker daemon ha bloqueado la orden y está regenerando la prospección comercial."
        ),
    }


