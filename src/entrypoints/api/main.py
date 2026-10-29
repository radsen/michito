from fastapi import FastAPI, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from decimal import Decimal
import uuid
import os

from src.entrypoints.container import Container, container as app_container
from src.application.dto.search_request_dto import CompanyFilterDto
from src.domain.entities.lead_order import LeadOrder
from src.domain.entities.company import Company
from src.domain.value_objects.tax_id import TaxId
import logging

logger = logging.getLogger(__name__)

app = FastAPI(title="Michito API", version="1.0.0")

templates = Jinja2Templates(directory="templates")

def get_container() -> Container:
    return app_container

# Request Models
class SearchRequest(BaseModel):
    country_code: str
    min_revenue: Optional[Decimal] = None
    industry: Optional[str] = None
    city: Optional[str] = None

class VerificationRequest(BaseModel):
    email: str

class OrderRequest(BaseModel):
    tier: int
    company_id: str

class EbitdaRequest(BaseModel):
    operating_revenue: Decimal
    cost_of_sales: Decimal
    operating_expenses: Decimal
    depreciation: Decimal
    amortization: Decimal

@app.get("/", response_class=HTMLResponse)
def get_portal(request: Request):
    return templates.TemplateResponse(request, "teaser_one_pager_base.html")

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
def create_order(request: OrderRequest, container: Container = Depends(get_container)):
    try:
        # Placeholder company since we only have memory persistence for now
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
    signature = event_data.get("signature", {}).get("checksum", "")
    if not signature:
        # Fallback to header if signature not in body
        signature = request.headers.get("X-Signature", "")
        
    container.fulfill_webhook_use_case.execute(event_data, signature)
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
    return {"status": "ok"}
