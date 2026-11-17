import hashlib
import hmac
from fastapi import FastAPI, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse, FileResponse, RedirectResponse
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
    "https://michito-web-limgi3puaq-uc.a.run.app,http://localhost:5000,http://localhost:5173,http://localhost:8080,http://localhost:3000,http://127.0.0.1:5000,http://127.0.0.1:5173,http://127.0.0.1:8080,http://127.0.0.1:3000"
)
allowed_origins = [o.strip() for o in allowed_origins_raw.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if allowed_origins else ["*"],
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

        order = sql_adapter.create_order(
            client_name=payload.client.name,
            client_email=payload.client.email,
            client_phone=payload.client.phone,
            client_channel=payload.client.channel or "web_portal",
            referral_partner=payload.client.referral_partner or "direct",
            campaign_id=payload.request.campaign_id or "universal_prospecting",
            city=payload.request.city or "Medellín",
            limit=payload.request.limit or 10,
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
        )

        try:
            queue_adapter = app_container.queue_adapter
            if queue_adapter:
                queue_adapter.publish_order({"order_id": order["order_id"]})
            else:
                logger.warning("Queue adapter not initialized. Order saved to DB but not published to Pub/Sub.")
        except Exception as e:
            logger.error(f"Failed to publish order {order['order_id']} to queue: {e}")

        try:
            if hasattr(app_container, "alert_dispatcher"):
                app_container.alert_dispatcher.send_feed_event(
                    "New Order Placed",
                    f"Order `{order['order_id']}` placed by *{payload.client.name}* ({payload.client.email}).",
                    details={
                        "order_id": order["order_id"],
                        "client": payload.client.name,
                        "campaign": payload.request.campaign_id,
                        "city": payload.request.city or "Medellín",
                        "requested_leads": payload.request.limit or 10,
                        "tier": f"Tier {payload.request.tier or 2}",
                    },
                )
        except Exception as e:
            logger.warning(f"Could not dispatch order feed event: {e}")

        return {
            "status": "success",
            "order_id": order["order_id"],
            "order_status": order["status"],
            "estimated_processing_seconds": max(15, int((payload.request.limit or 10) * (3.5 if (payload.request.tier or 2) == 3 else 1.8 if (payload.request.tier or 2) == 2 else 0.8))),
            "message": "Order successfully queued for asynchronous intelligence extraction.",
            "order": order
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
    return order

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
        file_path = delivery.get("csv_path")
        media_type = "text/csv"
        filename = f"{order_id}_prospects.csv"
    elif ft in ("full_csv", "full-csv", "intelligence", "full"):
        file_path = delivery.get("full_csv_path")
        media_type = "text/csv"
        filename = f"{order_id}_prospects_full_intelligence.csv"
    elif ft in ("xlsx", "excel"):
        file_path = delivery.get("xlsx_path")
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"{order_id}_prospects.xlsx"
    elif ft in ("pdf",):
        file_path = delivery.get("pdf_path")
        media_type = "application/pdf"
        filename = f"{order_id}_dossier_ejecutivo.pdf"
    elif ft in ("md", "dossier", "markdown"):
        file_path = delivery.get("dossier_path")
        media_type = "text/markdown"
        filename = f"{order_id}_executive_dossier.md"
    else:
        raise HTTPException(status_code=400, detail="Invalid file_type (must be 'csv', 'full_csv', 'xlsx', 'pdf', or 'md')")

    if not file_path:
        raise HTTPException(status_code=404, detail="No deliverable file path recorded for this order.")

    # 1. Cloud Storage or Firebase Emulator gs:// path -> redirect to secure download URL
    if file_path.startswith("gs://"):
        try:
            from src.adapters.storage.gcs_storage_adapter import GcsStorageAdapter
            gcs = GcsStorageAdapter()
            parts = file_path.replace("gs://", "").split("/", 1)
            dest_blob = parts[1] if len(parts) > 1 else parts[0]
            download_url = gcs.generate_download_url(dest_blob)
            return RedirectResponse(url=download_url, status_code=307)
        except Exception as e:
            logger.warning(f"Failed to generate GCS signed URL for {file_path}: {e}")

    # 2. Local disk file fallback
    if os.path.exists(file_path):
        return FileResponse(path=file_path, media_type=media_type, filename=filename)

    raise HTTPException(status_code=404, detail=f"Deliverable file not found at {file_path}")

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

                    try:
                        deliver_order_use_case.execute(reference)
                        logger.info(f"[WompiWebhook] Order `{reference}` dispatched via omnichannel delivery.")
                    except Exception as e:
                        logger.error(f"[WompiWebhook] Error during delivery dispatch for order {reference}: {e}")

                    try:
                        if hasattr(app_container, "alert_dispatcher"):
                            client_info = order.get("client", {})
                            app_container.alert_dispatcher.send_feed_event(
                                "Wompi Payment Confirmed!",
                                f"Webhook received! Order `{reference}` paid. Deliverables unlocked for *{client_info.get('name', 'Buyer')}*.",
                                details={
                                    "order_id": reference,
                                    "amount": f"${int(amount_in_cents) // 100:,.0f} COP",
                                    "transaction_id": str(tx_id),
                                    "provider": "Wompi Gateway",
                                },
                            )
                    except Exception as e:
                        logger.warning(f"Could not dispatch webhook payment feed event: {e}")
            except Exception as e:
                logger.error(f"[WompiWebhook] Error updating order in database: {e}")

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
async def pubsub_order_handler(request: Request):
    """
    Intakes Google Cloud Pub/Sub push messages containing orders for asynchronous fulfillment.
    Standard Cloud Run Pub/Sub push event intake pattern.
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

    daemon = OrderWorkerDaemon(order_repository=sql_adapter)
    success = daemon.process_order(order)
    return {"status": "processed" if success else "failed", "order_id": order_id}


@app.post("/api/v1/orders/{order_id}/process")
def trigger_order_processing(order_id: str, request: Request):
    """
    Manual webhook or background trigger to process a pending order immediately.
    Protected: Restricted to local/test environments or requests with authorized internal admin keys.
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
    success = daemon.process_order(order)
    return {"status": "success" if success else "failed", "order_id": order_id}

