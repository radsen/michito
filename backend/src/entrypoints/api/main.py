import hashlib
import hmac
from fastapi import FastAPI, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
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
from campaign_loader import list_available_campaigns, load_campaign

logger = logging.getLogger(__name__)

app = FastAPI(title="Michito B2B Intelligence Engine API", version="2.0.0")

# Enable Cross-Origin Resource Sharing (CORS) for Firebase Hosting (:5000) & Local Dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
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
    campaign_id: str
    country: Optional[str] = "CO"
    country_allocations: Optional[Dict[str, int]] = None
    city: Optional[str] = "Medellín"
    limit: Optional[int] = 10
    tier: Optional[int] = 2
    segment: Optional[str] = None
    sector: Optional[str] = None
    keywords_include: Optional[List[str]] = None
    keywords_exclude: Optional[List[str]] = None
    exclusions: Optional[List[str]] = None

class CreateOrderRequest(BaseModel):
    client: ClientDto
    request: RequestDto

class IntentProfileRequest(BaseModel):
    query: str
    country: Optional[str] = "CO"

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
def profile_b2b_intent(payload: IntentProfileRequest):
    """
    Stage 1 Conversational & Search Intent Profiler (Zero Compute Cost).
    Analyzes natural language sales brief, extracts target geography and vertical,
    estimates match volume, and generates a verified preview card without incurring heavy scraping costs.
    """
    if not payload.query or not payload.query.strip():
        raise HTTPException(status_code=400, detail="Query must not be empty.")

    use_case = app_container.profile_b2b_intent_use_case
    result = use_case.execute(query=payload.query, country=payload.country or "CO")
    return result

@app.post("/api/v1/orders", status_code=201)
def create_prospecting_order(payload: CreateOrderRequest):
    """
    Ingests an on-demand prospecting order from Web Portal or WhatsApp,
    creates the client record, persists order in PostgreSQL, and queues it for the worker.
    """
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

        order = sql_adapter.create_order(
            client_name=payload.client.name,
            client_email=payload.client.email,
            client_phone=payload.client.phone,
            client_channel=payload.client.channel or "web_portal",
            referral_partner=payload.client.referral_partner or "direct",
            campaign_id=payload.request.campaign_id,
            city=payload.request.city or "Medellín",
            limit=payload.request.limit or 10,
            country=payload.request.country or "CO",
            currency=currency,
            segment=payload.request.segment,
            sector=payload.request.sector,
            keywords_include=payload.request.keywords_include,
            keywords_exclude=merged_exclusions or None,
            tier=payload.request.tier or 2,
            country_allocations=payload.request.country_allocations,
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
                    title="New Order Placed 🚀",
                    message=f"Order `{order['order_id']}` placed by *{payload.client.name}* ({payload.client.email}).",
                    details={
                        "order_id": order["order_id"],
                        "client": payload.client.name,
                        "campaign": payload.request.campaign_id,
                        "city": payload.request.city or "Medellín",
                        "requested_leads": payload.request.limit or 10,
                        "tier": f"Tier {payload.request.tier or 2}",
                    }
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

@app.post("/api/v1/orders/{order_id}/pay")
def pay_prospecting_order(order_id: str):
    """
    Confirms simulated or webhook payment, transitions status to 'paid', and unlocks downloads.
    """
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
                title="Payment Approved! 💳",
                message=f"Payment received for Order `{order_id}`! Deliverables unlocked for *{client_info.get('name', 'Client')}*.",
                details={
                    "order_id": order_id,
                    "amount": f"${amount // 100:,.0f} COP",
                    "transaction_id": tx_id,
                    "client": client_info.get("name"),
                }
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
    Serves the generated CSV or Markdown executive dossier.
    """
    order = sql_adapter.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    delivery = order.get("delivery", {})
    if file_type.lower() == "csv":
        file_path = delivery.get("csv_path")
        media_type = "text/csv"
        filename = f"{order_id}_prospects.csv"
    elif file_type.lower() in ("md", "dossier", "markdown"):
        file_path = delivery.get("dossier_path")
        media_type = "text/markdown"
        filename = f"{order_id}_executive_dossier.md"
    else:
        raise HTTPException(status_code=400, detail="Invalid file_type (must be 'csv' or 'md')")

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
    WOMPI_EVENTS_SECRET = "test_events_wmhM2301jwX2c9q8u4SofthtnAKUO7aK"
    
    signature = event_data.get("signature", {}).get("checksum", "")
    data = event_data.get("data", {})
    transaction = data.get("transaction", {})
    
    tx_id = transaction.get("id", "")
    status = transaction.get("status", "")
    amount_in_cents = transaction.get("amount_in_cents", "")
    timestamp = event_data.get("timestamp", "")
    
    raw_str = f"{tx_id}{status}{amount_in_cents}{timestamp}{WOMPI_EVENTS_SECRET}"
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
                    logger.info(f"[WompiWebhook] ✅ Order `{reference}` marked paid in PostgreSQL.")

                    try:
                        deliver_order_use_case.execute(reference)
                        logger.info(f"[WompiWebhook] ✅ Order `{reference}` dispatched via omnichannel delivery.")
                    except Exception as e:
                        logger.error(f"[WompiWebhook] Error during delivery dispatch for order {reference}: {e}")

                    try:
                        if hasattr(app_container, "alert_dispatcher"):
                            client_info = order.get("client", {})
                            app_container.alert_dispatcher.send_feed_event(
                                title="Wompi Payment Confirmed! 💳",
                                message=f"Webhook received! Order `{reference}` paid. Deliverables unlocked for *{client_info.get('name', 'Buyer')}*.",
                                details={
                                    "order_id": reference,
                                    "amount": f"${int(amount_in_cents) // 100:,.0f} COP",
                                    "transaction_id": str(tx_id),
                                    "provider": "Wompi Gateway",
                                }
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
    from clients.whatsapp.bot_service import WhatsAppBotService
    
    # Very basic parser for Meta Cloud API structure
    try:
        if "entry" in payload:
            for entry in payload["entry"]:
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    if "messages" in value:
                        for msg in value["messages"]:
                            from_number = msg.get("from")
                            text = msg.get("text", {}).get("body", "")
                            
                            bot = WhatsAppBotService()
                            response = bot.handle_incoming_message(from_number, text)
                            # In a real system, we'd send 'response' to Meta/Twilio API here
                            logger.info(f"Bot response: {response}")
    except Exception as e:
        logger.error(f"Error processing WhatsApp Webhook: {e}")
        
    return {"status": "ok"}
