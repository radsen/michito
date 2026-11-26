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


# ==============================================================================
# Normalized Multi-Contact Enterprise Architecture (v2.0)
# Decouples Companies, Individuals, Roles, and Canonical Contact Channels (N:M Graph)
# ==============================================================================

class CompanyModel(Base):
    """
    Canonical Corporate Entity.
    Represents an incorporated legal person (S.A.S., S.A., S.R.L., SpA) or formal merchant.
    """
    __tablename__ = "companies"

    company_id: Any = Column(String(64), primary_key=True, index=True)  # e.g. "CO_900123456"
    tax_id: Any = Column(String(64), nullable=False, index=True)  # NIT in CO, RNC in DO, RUC in EC, RUT in CL
    country: Any = Column(String(4), nullable=False, default="CO", index=True)
    legal_name: Any = Column(String(255), nullable=False)
    clean_name: Any = Column(String(255), nullable=False, index=True)
    trade_name: Any = Column(String(255), nullable=True)  # Nombre Comercial / Rótulo
    department: Any = Column(String(128), nullable=True, index=True)
    municipality: Any = Column(String(128), nullable=False, index=True)
    address: Any = Column(Text, nullable=True)

    # Activity & Classification (DANE / UN ISIC Rev. 4)
    primary_ciiu: Any = Column(String(32), nullable=True, index=True)
    secondary_ciius: Any = Column(JSON, nullable=True)
    macrosector: Any = Column(String(128), nullable=True, index=True)
    corporate_type: Any = Column(String(128), nullable=True)
    revenue_bracket: Any = Column(String(64), nullable=True)
    employees_bracket: Any = Column(String(64), nullable=True)

    # Digital Footprint & Attributed Presence
    website_url: Any = Column(Text, nullable=True)
    website_status: Any = Column(String(64), default="UNVERIFIED", index=True)  # ONLINE_ACTIVE_HTTP200, OFFLINE_STATUTORY_ACTIVE, NO_INDEXED_PRESENCE

    created_at: Any = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Any = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    roles = relationship("CompanyIndividualRoleModel", back_populates="company", cascade="all, delete-orphan")
    channel_links = relationship("CompanyChannelLinkModel", back_populates="company", cascade="all, delete-orphan")


class IndividualModel(Base):
    """
    Canonical Human Decision Maker / Executive.
    Can hold roles across multiple sister companies, holdings, or statutory proxies.
    """
    __tablename__ = "individuals"

    individual_id: Any = Column(String(64), primary_key=True, index=True)  # e.g. "IND_CO_1017263720" or UUID
    national_id: Any = Column(String(64), nullable=True, index=True)  # Cédula de Ciudadanía, Pasaporte, DNI
    country: Any = Column(String(4), default="CO", index=True)
    full_name: Any = Column(String(255), nullable=False, index=True)
    first_name: Any = Column(String(128), nullable=True)
    last_name: Any = Column(String(128), nullable=True)
    linkedin_url: Any = Column(Text, nullable=True)

    created_at: Any = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Any = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    roles = relationship("CompanyIndividualRoleModel", back_populates="individual", cascade="all, delete-orphan")
    channel_links = relationship("IndividualChannelLinkModel", back_populates="individual", cascade="all, delete-orphan")


class CompanyIndividualRoleModel(Base):
    """
    Associative Junction Table: Links an Individual to a Company with Role Nuance.
    Differentiates internal operational directors from external law firms and accounting proxies.
    """
    __tablename__ = "company_individual_roles"

    role_id: Any = Column(String(64), primary_key=True, index=True)
    company_id: Any = Column(String(64), ForeignKey("companies.company_id"), nullable=False, index=True)
    individual_id: Any = Column(String(64), ForeignKey("individuals.individual_id"), nullable=False, index=True)
    title: Any = Column(String(255), nullable=False)  # e.g. "Gerente General", "Director de Operaciones", "Apoderado General"
    role_category: Any = Column(String(64), default="statutory_signer", index=True)  # internal_c_level, statutory_signer, external_counsel, fiscal_auditor, procurement_chief, plant_director
    is_operational_decision_maker: Any = Column(Boolean, default=True, index=True)  # TRUE for plant/commercial managers; FALSE for external law firms & auditors
    tenure_status: Any = Column(String(32), default="active", index=True)  # active, revoked, former
    verified_at: Any = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    created_at: Any = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Any = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    company = relationship("CompanyModel", back_populates="roles")
    individual = relationship("IndividualModel", back_populates="roles")


class ContactChannelModel(Base):
    """
    Canonical Communication Channel.
    Stores a unique normalized phone number or email address with deliverability state
    and global network footprint count across companies.
    """
    __tablename__ = "contact_channels"

    channel_id: Any = Column(String(64), primary_key=True, index=True)
    channel_type: Any = Column(String(32), nullable=False, index=True)  # mobile_phone, landline_pbx, corporate_email, statutory_email
    normalized_value: Any = Column(String(255), nullable=False, unique=True, index=True)  # E.164 phone or lowercase email
    raw_value: Any = Column(String(255), nullable=True)
    verification_state: Any = Column(String(32), default="unverified", index=True)  # mx_valid, smtp_deliverable, whatsapp_active, unverified, invalid_bounce
    mx_host: Any = Column(String(255), nullable=True)
    network_footprint_count: Any = Column(Integer, default=1, index=True)  # Distinct companies linked to this channel
    suppressed_opt_out: Any = Column(Boolean, default=False, index=True)  # Habeas Data compliance
    verified_at: Any = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    created_at: Any = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Any = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    company_links = relationship("CompanyChannelLinkModel", back_populates="channel", cascade="all, delete-orphan")
    individual_links = relationship("IndividualChannelLinkModel", back_populates="channel", cascade="all, delete-orphan")


class CompanyChannelLinkModel(Base):
    """
    Links a Company directly to a Channel (e.g. Headquarters PBX, Main Administrative Email).
    """
    __tablename__ = "company_channel_links"

    link_id: Any = Column(String(64), primary_key=True, index=True)
    company_id: Any = Column(String(64), ForeignKey("companies.company_id"), nullable=False, index=True)
    channel_id: Any = Column(String(64), ForeignKey("contact_channels.channel_id"), nullable=False, index=True)
    channel_usage: Any = Column(String(64), default="general_inbox", index=True)  # headquarters_pbx, legal_notification_inbox, general_inbox, plant_switchboard, shared_holding_line
    is_primary_switchboard: Any = Column(Boolean, default=False, index=True)

    created_at: Any = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    company = relationship("CompanyModel", back_populates="channel_links")
    channel = relationship("ContactChannelModel", back_populates="company_links")


class IndividualChannelLinkModel(Base):
    """
    Links an Individual to a Channel (e.g. Direct Mobile Phone, Direct Executive Email).
    """
    __tablename__ = "individual_channel_links"

    link_id: Any = Column(String(64), primary_key=True, index=True)
    individual_id: Any = Column(String(64), ForeignKey("individuals.individual_id"), nullable=False, index=True)
    channel_id: Any = Column(String(64), ForeignKey("contact_channels.channel_id"), nullable=False, index=True)
    channel_ownership: Any = Column(String(64), default="direct_mobile", index=True)  # direct_mobile, direct_executive_email, external_firm_email, whatsapp_direct

    created_at: Any = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    individual = relationship("IndividualModel", back_populates="channel_links")
    channel = relationship("ContactChannelModel", back_populates="individual_links")


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
    geographic_scope: Any = Column(String(32), default="metro_area", index=True)  # strict_city, metro_area, regional_corridor, national

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
    verified_yield: Any = Column(Integer, nullable=True, default=0)
    ready_notified_at: Any = Column(DateTime, nullable=True)
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

    @staticmethod
    def _to_iso_utc(dt: Optional[datetime]) -> Optional[str]:
        if not dt:
            return None
        iso = dt.isoformat()
        if not iso.endswith("Z") and "+" not in iso:
            iso += "Z"
        return iso

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
                "geographic_scope": self.geographic_scope or "metro_area",
            },
            "status": self.status,
            "verified_yield": self.verified_yield or 0,
            "ready_notified_at": OrderModel._to_iso_utc(self.ready_notified_at),
            "payment": {
                "provider": self.payment_provider,
                "status": self.payment_status,
                "amount_in_cents": self.payment_amount_in_cents,
                "currency": self.payment_currency,
                "transaction_id": self.payment_transaction_id,
                "paid_at": OrderModel._to_iso_utc(self.payment_paid_at),
            },
            "delivery": {
                "total_qualified": self.delivery_total_qualified or self.verified_yield or 0,
                "verified_yield": self.verified_yield or self.delivery_total_qualified or 0,
                "ready_notified_at": OrderModel._to_iso_utc(self.ready_notified_at),
                "sample_teaser": self.delivery_sample_teaser or [],
                "csv_path": self.delivery_csv_path,
                "xlsx_path": self.delivery_xlsx_path,
                "dossier_path": self.delivery_dossier_path,
                "pdf_path": self.delivery_pdf_path,
                "playbook": self.delivery_playbook or [],
                "delivered_at": OrderModel._to_iso_utc(self.delivery_delivered_at),
            },
            "metrics": self.metrics or {},
            "error_message": self.error_message,
            "replacement_claims": self.replacement_claims or [],
            "retry_count": self.retry_count or 0,
            "max_retries": self.max_retries or 3,
            "last_retried_at": OrderModel._to_iso_utc(self.last_retried_at),
            "partner": {
                "referral_partner": self.referral_partner or "direct",
                "commission_rate": self.partner_commission_rate or 0.0,
                "commission_cop": self.partner_commission_cop or 0,
                "settlement_status": self.partner_settlement_status or "pending",
                "settled_at": OrderModel._to_iso_utc(self.partner_settled_at),
            },
            "created_at": OrderModel._to_iso_utc(self.created_at),
            "started_processing_at": OrderModel._to_iso_utc(self.started_processing_at),
            "completed_at": OrderModel._to_iso_utc(self.completed_at),
            "updated_at": OrderModel._to_iso_utc(self.updated_at),
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
    concentric_rings: Any = Column(JSON, nullable=False, default=dict)  # {"ring_0": [...], "ring_1": [...], "ring_2": [...]}
    expansion_rules: Any = Column(JSON, nullable=False, default=dict)   # {"default_scope": "metro_area", "max_allowed_ring": 1}
    registry_sources: Any = Column(JSON, nullable=True)  # Sources: ["rues", "camara_medellin", "secop", "supersociedades", "dgcp", "sercop"]
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
            "concentric_rings": self.concentric_rings or {},
            "expansion_rules": self.expansion_rules or {},
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
    allowed_isic_divisions: Any = Column(JSON, nullable=True)               # e.g. ["62", "63", "58", "46"]
    forbidden_isic_divisions: Any = Column(JSON, nullable=True)             # e.g. ["24", "38", "41", "42", "71", "79", "85", "86"]
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
            "allowed_isic_divisions": self.allowed_isic_divisions or [],
            "forbidden_isic_divisions": self.forbidden_isic_divisions or [],
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


# ==============================================================================
# CHIKETTO UNIVERSAL PRODUCT & PRICING CATALOG (DYNAMIC PIM ENGINE)
# ==============================================================================

class ProductCatalogModel(Base):
    """
    Master product definitions supporting Michito B2B data tiers now,
    and Zebra Print-on-Demand (CR80/NFC) & Digital Wallet Passes in the future.
    """
    __tablename__ = "pricing_catalog"

    id: Any = Column(String(64), primary_key=True, index=True)  # e.g. "michito_tier_1", "michito_tier_2", "michito_tier_3"
    category: Any = Column(String(32), nullable=False, default="data_intelligence", index=True)
    tier: Any = Column(Integer, nullable=True, index=True)  # 1, 2, 3 for data intelligence
    name: Any = Column(String(128), nullable=False)
    description: Any = Column(Text, nullable=True)
    fulfillment_type: Any = Column(String(32), nullable=False, default="data_harvest")  # data_harvest, print_spool, wallet_signer
    is_active: Any = Column(Boolean, nullable=False, default=True, index=True)
    created_at: Any = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Any = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    regional_prices: Any = relationship("ProductRegionalPriceModel", back_populates="product", cascade="all, delete-orphan", uselist=True)
    volume_discounts: Any = relationship("ProductVolumeDiscountModel", back_populates="product", cascade="all, delete-orphan", uselist=True)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category,
            "tier": self.tier,
            "name": self.name,
            "description": self.description,
            "fulfillment_type": self.fulfillment_type,
            "is_active": bool(self.is_active),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ProductRegionalPriceModel(Base):
    """
    Territory-specific price books decoupling products from local currency and tax rates.
    """
    __tablename__ = "product_regional_prices"

    id: Any = Column(String(64), primary_key=True, index=True)  # e.g. "michito_t2_cop", "michito_t2_usd"
    product_id: Any = Column(String(64), ForeignKey("pricing_catalog.id"), nullable=False, index=True)
    country_code: Any = Column(String(8), nullable=False, default="CO", index=True)  # CO, DO, EC, MULTI
    currency: Any = Column(String(8), nullable=False, default="COP", index=True)      # COP, DOP, USD
    base_unit_price_cents: Any = Column(Integer, nullable=False)                      # In cents e.g. 620000 = $6.200 COP
    min_order_quantity: Any = Column(Integer, nullable=False, default=25)
    max_order_quantity: Any = Column(Integer, nullable=False, default=1000)
    tax_rate_percent: Any = Column(Float, nullable=False, default=19.0)               # 19% IVA CO, 18% DO, 0% EC
    is_active: Any = Column(Boolean, nullable=False, default=True, index=True)
    created_at: Any = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    product: Any = relationship("ProductCatalogModel", back_populates="regional_prices")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "product_id": self.product_id,
            "country_code": self.country_code,
            "currency": self.currency,
            "base_unit_price_cents": self.base_unit_price_cents,
            "min_order_quantity": self.min_order_quantity,
            "max_order_quantity": self.max_order_quantity,
            "tax_rate_percent": self.tax_rate_percent,
            "is_active": bool(self.is_active),
        }


class ProductVolumeDiscountModel(Base):
    """
    Progressive volume discount curves per product.
    """
    __tablename__ = "product_volume_discounts"

    id: Any = Column(Integer, primary_key=True, autoincrement=True)
    product_id: Any = Column(String(64), ForeignKey("pricing_catalog.id"), nullable=False, index=True)
    min_quantity: Any = Column(Integer, nullable=False, index=True)                   # 50, 100, 250, 500, 1000
    discount_percentage: Any = Column(Float, nullable=False)                          # 5.0, 10.0, 18.0, 25.0, 32.0

    product: Any = relationship("ProductCatalogModel", back_populates="volume_discounts")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "product_id": self.product_id,
            "min_quantity": self.min_quantity,
            "discount_percentage": self.discount_percentage,
        }


class AffiliateModel(Base):
    """
    Commercial affiliate / partner directory (e.g. Tinkko).
    """
    __tablename__ = "affiliates"

    partner_id: Any = Column(String(32), primary_key=True, index=True)  # "tinkko", "direct"
    name: Any = Column(String(128), nullable=False)
    tax_id: Any = Column(String(32), nullable=True)
    contact_email: Any = Column(String(255), nullable=True)
    is_active: Any = Column(Boolean, nullable=False, default=True)
    created_at: Any = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    commission_rules: Any = relationship("AffiliateCommissionRuleModel", back_populates="affiliate", cascade="all, delete-orphan")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "partner_id": self.partner_id,
            "name": self.name,
            "tax_id": self.tax_id,
            "contact_email": self.contact_email,
            "is_active": bool(self.is_active),
        }


class AffiliateCommissionRuleModel(Base):
    """
    Specific revenue share and customer discount rules per partner and product/category.
    """
    __tablename__ = "affiliate_commission_rules"

    id: Any = Column(Integer, primary_key=True, autoincrement=True)
    partner_id: Any = Column(String(32), ForeignKey("affiliates.partner_id"), nullable=False, index=True)
    product_id: Any = Column(String(64), ForeignKey("pricing_catalog.id"), nullable=True, index=True)
    commission_percentage: Any = Column(Float, nullable=False, default=25.0)          # 25% for Michito
    customer_discount_percentage: Any = Column(Float, nullable=False, default=10.0)   # 10% tenant discount

    affiliate: Any = relationship("AffiliateModel", back_populates="commission_rules")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "partner_id": self.partner_id,
            "product_id": self.product_id,
            "commission_percentage": self.commission_percentage,
            "customer_discount_percentage": self.customer_discount_percentage,
        }
