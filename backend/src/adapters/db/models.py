"""
SQLAlchemy Relational Models for Michito B2B Engine.
Implements the 4-table normalized commercial architecture:
1. clients (Buyer / Account entities)
2. leads (Verified reusable product inventory pool)
3. prospecting_orders (Commercial order transactions)
4. order_leads (Products by Order / Manifest with campaign-tailored 5 touches)
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy import (
    Column,
    String,
    Integer,
    BigInteger,
    Float,
    DateTime,
    Text,
    JSON,
    Boolean,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()
Base.__allow_unmapped__ = True


class ClientModel(Base):
    __tablename__ = "clients"

    client_id: Any = Column(String(64), primary_key=True, index=True)
    name: Any = Column(String(255), nullable=False)
    email: Any = Column(String(255), nullable=False, unique=True, index=True)
    phone: Any = Column(String(64), nullable=True)
    channel: Any = Column(String(32), default="web_portal")
    referral_partner: Any = Column(String(64), nullable=True, default="direct")  # e.g. "tinkko", "direct"

    created_at: Any = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Any = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    orders: Any = relationship("OrderModel", back_populates="client_entity")


class LeadModel(Base):
    """
    Verified Lead Asset Pool (Inventory).
    Every verified company is stored here as an indexed, reusable product.
    Can be served to multiple non-competing clients and cached across runs.
    """
    __tablename__ = "leads"

    # lead_id is composite e.g. "CO_900123456" or "DO_131999888"
    lead_id: Any = Column(String(64), primary_key=True, index=True)
    tax_id: Any = Column(String(64), nullable=False, index=True)  # NIT in CO, RNC in DO
    country: Any = Column(String(4), nullable=False, default="CO", index=True)
    company_name: Any = Column(String(255), nullable=False)
    clean_name: Any = Column(String(255), nullable=False)
    city: Any = Column(String(128), nullable=False, index=True)
    address: Any = Column(Text, nullable=True)

    # Activity & Classification
    ciiu_code: Any = Column(String(32), nullable=True, index=True)
    sector_macro: Any = Column(String(128), nullable=True, index=True)
    activity_description: Any = Column(Text, nullable=True)
    segment_name: Any = Column(String(64), nullable=True)
    revenue_bracket: Any = Column(String(64), nullable=True)
    employees_bracket: Any = Column(String(64), nullable=True)

    # Digital Footprint & Verification
    website_url: Any = Column(Text, nullable=True)
    website_audit_status: Any = Column(String(255), nullable=True)
    mx_host: Any = Column(String(255), nullable=True)

    # Decision Maker Profile
    decision_maker_name: Any = Column(String(255), nullable=False)
    decision_maker_title: Any = Column(String(255), nullable=False)
    first_name: Any = Column(String(128), nullable=True)
    verified_email: Any = Column(String(255), nullable=False, index=True)
    direct_mobile_phone: Any = Column(String(64), nullable=False)

    # Expansion & Intent Signals
    contracts_data: Any = Column(JSON, nullable=True)
    hiring_xray_url: Any = Column(Text, nullable=True)
    expansion_flag: Any = Column(Text, nullable=True)
    linkedin_xray_url: Any = Column(Text, nullable=True)

    # Freshness / Cache Control
    verified_at: Any = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    created_at: Any = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Any = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    orders_assigned: Any = relationship("OrderLeadModel", back_populates="lead")


class OrderModel(Base):
    __tablename__ = "prospecting_orders"

    order_id: Any = Column(String(64), primary_key=True, index=True)

    # Client Reference
    client_id: Any = Column(String(64), ForeignKey("clients.client_id"), nullable=True, index=True)
    client_name: Any = Column(String(255), nullable=False)
    client_email: Any = Column(String(255), nullable=False, index=True)
    client_phone: Any = Column(String(64), nullable=True)
    client_channel: Any = Column(String(32), default="web_portal")

    # Multi-Partner Affiliate & Commission Tracking (v1.2)
    referral_partner: Any = Column(String(64), nullable=False, default="direct", index=True)
    partner_commission_rate: Any = Column(Float, default=0.0)
    partner_commission_cop: Any = Column(BigInteger, default=0)
    partner_settled_at: Any = Column(DateTime, nullable=True)
    partner_settlement_status: Any = Column(String(32), default="pending", index=True)

    # Campaign & Geography
    campaign_id: Any = Column(String(128), nullable=False, index=True)
    country: Any = Column(String(8), default="CO")
    country_allocations: Any = Column(JSON, nullable=True)
    location_allocations: Any = Column(JSON, nullable=True)
    city: Any = Column(String(128), default="Medellín")
    requested_limit: Any = Column(Integer, default=10)
    tier: Any = Column(Integer, default=2)
    segment: Any = Column(String(64), nullable=True)
    sector: Any = Column(String(128), nullable=True)
    offer_description: Any = Column(Text, nullable=True)
    target_roles: Any = Column(JSON, nullable=True)
    target_ciiu_codes: Any = Column(JSON, nullable=True)
    keywords_include: Any = Column(JSON, nullable=True)
    keywords_exclude: Any = Column(JSON, nullable=True)

    # Bidirectional Commercial Directionality & RFQ Specs
    directionality: Any = Column(String(32), default="vendor_to_clients", index=True)
    rfq_specifications: Any = Column(Text, nullable=True)

    # Lifecycle State: queued, processing, awaiting_payment, paid, completed, failed
    status: Any = Column(String(32), default="queued", index=True)

    # Monetization & Payment (Wompi)
    payment_provider: Any = Column(String(32), default="wompi")
    payment_status: Any = Column(String(32), default="pending", index=True)
    payment_amount_in_cents: Any = Column(BigInteger, default=0)
    payment_currency: Any = Column(String(8), default="COP")
    payment_transaction_id: Any = Column(String(128), nullable=True)
    payment_paid_at: Any = Column(DateTime, nullable=True)

    # Deliverables & Quality Teaser
    delivery_total_qualified: Any = Column(Integer, default=0)
    delivery_sample_teaser: Any = Column(JSON, nullable=True)
    delivery_csv_path: Any = Column(Text, nullable=True)
    delivery_xlsx_path: Any = Column(Text, nullable=True)
    delivery_dossier_path: Any = Column(Text, nullable=True)
    delivery_pdf_path: Any = Column(Text, nullable=True)
    delivery_playbook: Any = Column(JSON, nullable=True)
    delivery_delivered_at: Any = Column(DateTime, nullable=True)

    # Benchmark & Errors
    metrics: Any = Column(JSON, nullable=True)
    error_message: Any = Column(Text, nullable=True)
    replacement_claims: Any = Column(JSON, nullable=True, default=list)

    # Reliability & DLQ Retries
    retry_count: Any = Column(Integer, default=0, nullable=False)
    max_retries: Any = Column(Integer, default=3, nullable=False)
    last_retried_at: Any = Column(DateTime, nullable=True)

    # Audit Timestamps
    created_at: Any = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Any = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    started_processing_at: Any = Column(DateTime, nullable=True)
    completed_at: Any = Column(DateTime, nullable=True)

    client_entity: Any = relationship("ClientModel", back_populates="orders")
    manifest_leads: Any = relationship("OrderLeadModel", back_populates="order", cascade="all, delete-orphan")

    def to_dict(self) -> Dict[str, Any]:
        """Serializes model instance into standard Michito order dictionary format."""
        return {
            "order_id": self.order_id,
            "client": {
                "client_id": self.client_id,
                "name": self.client_name,
                "email": self.client_email,
                "phone": self.client_phone,
                "channel": self.client_channel,
            },
            "request": {
                "campaign_id": self.campaign_id,
                "country": self.country,
                "country_allocations": self.country_allocations,
                "location_allocations": self.location_allocations,
                "city": self.city,
                "limit": self.requested_limit,
                "tier": self.tier or 2,
                "segment": self.segment,
                "sector": self.sector,
                "offer_description": self.offer_description,
                "target_roles": self.target_roles,
                "target_ciiu_codes": self.target_ciiu_codes,
                "directionality": self.directionality or "vendor_to_clients",
                "rfq_specifications": self.rfq_specifications,
                "keywords_include": self.keywords_include,
                "keywords_exclude": self.keywords_exclude,
                "exclusions": self.keywords_exclude,
            },
            "status": self.status,
            "payment": {
                "provider": self.payment_provider,
                "status": self.payment_status,
                "amount_in_cents": self.payment_amount_in_cents,
                "currency": self.payment_currency,
                "transaction_id": self.payment_transaction_id,
                "paid_at": self.payment_paid_at.isoformat() if self.payment_paid_at else None,
            },
            "delivery": {
                "total_qualified": self.delivery_total_qualified,
                "sample_teaser": self.delivery_sample_teaser or [],
                "csv_path": self.delivery_csv_path,
                "xlsx_path": self.delivery_xlsx_path,
                "dossier_path": self.delivery_dossier_path,
                "pdf_path": self.delivery_pdf_path,
                "playbook": self.delivery_playbook or [],
                "delivered_at": self.delivery_delivered_at.isoformat() if self.delivery_delivered_at else None,
            },
            "metrics": self.metrics or {},
            "error_message": self.error_message,
            "replacement_claims": self.replacement_claims or [],
            "retry_count": self.retry_count or 0,
            "max_retries": self.max_retries or 3,
            "last_retried_at": self.last_retried_at.isoformat() if self.last_retried_at else None,
            "partner": {
                "referral_partner": self.referral_partner or "direct",
                "commission_rate": self.partner_commission_rate or 0.0,
                "commission_cop": self.partner_commission_cop or 0,
                "settlement_status": self.partner_settlement_status or "pending",
                "settled_at": self.partner_settled_at.isoformat() if self.partner_settled_at else None,
            },
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_processing_at": self.started_processing_at.isoformat() if self.started_processing_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class OrderLeadModel(Base):
    """
    Products-by-Order Manifest.
    Links each delivered lead to the specific commercial order,
    storing the campaign-tailored 5-touch copy generated for this client.
    """
    __tablename__ = "order_leads"

    id: Any = Column(Integer, primary_key=True, autoincrement=True)
    order_id: Any = Column(String(64), ForeignKey("prospecting_orders.order_id"), nullable=False, index=True)
    lead_id: Any = Column(String(64), ForeignKey("leads.lead_id"), nullable=False, index=True)

    # Tailored 5-Touch Copy for this specific client & campaign
    touch_1_linkedin: Any = Column(Text, nullable=True)
    touch_2_cold_email_sub: Any = Column(Text, nullable=True)
    touch_2_cold_email_body: Any = Column(Text, nullable=True)
    touch_3_followup_sub: Any = Column(Text, nullable=True)
    touch_3_followup_body: Any = Column(Text, nullable=True)
    touch_4_social_proof_sub: Any = Column(Text, nullable=True)
    touch_4_social_proof_body: Any = Column(Text, nullable=True)
    touch_5_breakup_sub: Any = Column(Text, nullable=True)
    touch_5_breakup_body: Any = Column(Text, nullable=True)

    assigned_at: Any = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("order_id", "lead_id", name="uq_order_lead"),
    )

    order: Any = relationship("OrderModel", back_populates="manifest_leads")
    lead: Any = relationship("LeadModel", back_populates="orders_assigned")


class TaxonomyLocationModel(Base):
    """
    Supported Administrative Territory & Registry Hierarchy.
    Houses all active departments, provinces, and metropolitan clusters for 🇨🇴, 🇩🇴, and 🇪🇨.
    """
    __tablename__ = "taxonomy_locations"

    location_id: Any = Column(String(64), primary_key=True, index=True)
    country_code: Any = Column(String(4), nullable=False, index=True)  # CO, DO, EC
    country_name: Any = Column(String(64), nullable=False)
    region_name: Any = Column(String(128), nullable=False, index=True)  # Department / Province / State
    city_name: Any = Column(String(128), nullable=False, index=True)    # City / Metro center
    aliases: Any = Column(JSON, nullable=True)  # List of municipalities, metropolitan areas, vernacular names
    registry_sources: Any = Column(JSON, nullable=True)  # Sources: ["rues", "camara_medellin", "secop", "dgcp", "sercop"]
    is_active: Any = Column(Boolean, default=True, index=True)
    created_at: Any = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "location_id": self.location_id,
            "country_code": self.country_code,
            "country_name": self.country_name,
            "region_name": self.region_name,
            "city_name": self.city_name,
            "aliases": self.aliases or [],
            "registry_sources": self.registry_sources or [],
            "is_active": bool(self.is_active),
        }


class TaxonomyRoleModel(Base):
    """
    Executive Decision Maker Hierarchy & Cross-Country Professional Synonyms.
    """
    __tablename__ = "taxonomy_roles"

    role_id: Any = Column(String(64), primary_key=True, index=True)
    canonical_title: Any = Column(String(128), nullable=False, index=True)  # Standardized Spanish title
    seniority_level: Any = Column(String(32), nullable=False, index=True)   # c_level, vp, director, gerente, jefe, coordinador
    functional_domain: Any = Column(String(64), nullable=False, index=True) # operations, procurement, finance, tech, commercial, hr, legal
    country_code: Any = Column(String(4), default="ALL", index=True)        # CO, DO, EC, or ALL
    aliases: Any = Column(JSON, nullable=True)                              # Synonyms, cross-border titles, English equivalents
    applicable_sectors: Any = Column(JSON, nullable=True)                   # Applicable industries: ["logistics", "manufacturing", "all"]
    usage_count: Any = Column(Integer, default=0, index=True)              # Incremented on selections/searches to rank autocomplete
    is_active: Any = Column(Boolean, default=True, index=True)
    created_at: Any = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role_id": self.role_id,
            "canonical_title": self.canonical_title,
            "role_title": self.canonical_title,
            "seniority_level": self.seniority_level,
            "functional_domain": self.functional_domain,
            "country_code": self.country_code,
            "aliases": self.aliases or [],
            "applicable_sectors": self.applicable_sectors or ["all"],
            "usage_count": self.usage_count or 0,
            "is_active": bool(self.is_active),
        }


class TaxonomySectorModel(Base):
    """
    Universal Economic Sectors, CIIU Classifications & Positive/Negative Keyword Sets.
    """
    __tablename__ = "taxonomy_sectors"

    sector_id: Any = Column(String(64), primary_key=True, index=True)
    sector_name: Any = Column(String(128), nullable=False)                  # Display title e.g. "Alimentos & Agroindustria"
    country_code: Any = Column(String(4), default="ALL", index=True)        # CO, DO, EC, or ALL
    ciiu_codes: Any = Column(JSON, nullable=True)                           # Official 4-digit CIIU codes e.g. ["C1011", "C1012"]
    keywords_include: Any = Column(JSON, nullable=True)                     # Positive high-intent keyword matches
    keywords_exclude_defaults: Any = Column(JSON, nullable=True)            # Default negative filters to avoid junk leads
    is_active: Any = Column(Boolean, default=True, index=True)
    usage_count: Any = Column(Integer, default=0, index=True)
    created_at: Any = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sector_id": self.sector_id,
            "sector_name": self.sector_name,
            "country_code": self.country_code,
            "ciiu_codes": self.ciiu_codes or [],
            "keywords_include": self.keywords_include or [],
            "keywords_exclude_defaults": self.keywords_exclude_defaults or [],
            "is_active": bool(self.is_active),
            "usage_count": self.usage_count or 0,
        }


class SearchIntentQueryModel(Base):
    """
    AI Agent Search Intent Memory Bank & Agent Training Log.
    Records natural language briefs, parsed parameters, and user modifications.
    """
    __tablename__ = "search_intent_queries"

    query_id: Any = Column(String(64), primary_key=True, index=True)
    client_id: Any = Column(String(64), ForeignKey("clients.client_id"), nullable=True, index=True)
    raw_prompt: Any = Column(Text, nullable=False)
    parsed_criteria: Any = Column(JSON, nullable=False)
    user_modifications: Any = Column(JSON, nullable=True)
    discovered_tokens: Any = Column(JSON, nullable=True)
    session_id: Any = Column(String(128), nullable=True, index=True)
    created_at: Any = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query_id": self.query_id,
            "client_id": self.client_id,
            "raw_prompt": self.raw_prompt,
            "parsed_criteria": self.parsed_criteria or {},
            "user_modifications": self.user_modifications or {},
            "discovered_tokens": self.discovered_tokens or {},
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
