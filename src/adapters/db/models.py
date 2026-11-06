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
    DateTime,
    Text,
    JSON,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class ClientModel(Base):
    __tablename__ = "clients"

    client_id = Column(String(64), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)
    phone = Column(String(64), nullable=True)
    channel = Column(String(32), default="web_portal")
    referral_partner = Column(String(64), nullable=True, default="direct")  # e.g. "tinkko", "direct"

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    orders = relationship("OrderModel", back_populates="client_entity")


class LeadModel(Base):
    """
    Verified Lead Asset Pool (Inventory).
    Every verified company is stored here as an indexed, reusable product.
    Can be served to multiple non-competing clients and cached across runs.
    """
    __tablename__ = "leads"

    # lead_id is composite e.g. "CO_900123456" or "DO_131999888"
    lead_id = Column(String(64), primary_key=True, index=True)
    tax_id = Column(String(64), nullable=False, index=True)  # NIT in CO, RNC in DO
    country = Column(String(4), nullable=False, default="CO", index=True)
    company_name = Column(String(255), nullable=False)
    clean_name = Column(String(255), nullable=False)
    city = Column(String(128), nullable=False, index=True)
    address = Column(Text, nullable=True)

    # Activity & Classification
    ciiu_code = Column(String(32), nullable=True, index=True)
    sector_macro = Column(String(128), nullable=True, index=True)
    activity_description = Column(Text, nullable=True)
    segment_name = Column(String(64), nullable=True)
    revenue_bracket = Column(String(64), nullable=True)
    employees_bracket = Column(String(64), nullable=True)

    # Digital Footprint & Verification
    website_url = Column(Text, nullable=True)
    website_audit_status = Column(String(255), nullable=True)
    mx_host = Column(String(255), nullable=True)

    # Decision Maker Profile
    decision_maker_name = Column(String(255), nullable=False)
    decision_maker_title = Column(String(255), nullable=False)
    first_name = Column(String(128), nullable=True)
    verified_email = Column(String(255), nullable=False, index=True)
    direct_mobile_phone = Column(String(64), nullable=False)

    # Expansion & Intent Signals
    contracts_data = Column(JSON, nullable=True)
    hiring_xray_url = Column(Text, nullable=True)
    expansion_flag = Column(Text, nullable=True)
    linkedin_xray_url = Column(Text, nullable=True)

    # Freshness / Cache Control
    verified_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    orders_assigned = relationship("OrderLeadModel", back_populates="lead")


class OrderModel(Base):
    __tablename__ = "prospecting_orders"

    order_id = Column(String(64), primary_key=True, index=True)

    # Client Reference
    client_id = Column(String(64), ForeignKey("clients.client_id"), nullable=True, index=True)
    client_name = Column(String(255), nullable=False)
    client_email = Column(String(255), nullable=False, index=True)
    client_phone = Column(String(64), nullable=True)
    client_channel = Column(String(32), default="web_portal")

    # Campaign & Geography
    campaign_id = Column(String(128), nullable=False, index=True)
    country = Column(String(4), default="CO")
    city = Column(String(128), default="Medellín")
    requested_limit = Column(Integer, default=10)
    segment = Column(String(64), nullable=True)
    sector = Column(String(128), nullable=True)
    keywords_include = Column(JSON, nullable=True)
    keywords_exclude = Column(JSON, nullable=True)

    # Lifecycle State: queued, processing, awaiting_payment, paid, completed, failed
    status = Column(String(32), default="queued", index=True)

    # Monetization & Payment (Wompi)
    payment_provider = Column(String(32), default="wompi")
    payment_status = Column(String(32), default="pending", index=True)
    payment_amount_in_cents = Column(BigInteger, default=0)
    payment_currency = Column(String(8), default="COP")
    payment_transaction_id = Column(String(128), nullable=True)
    payment_paid_at = Column(DateTime, nullable=True)

    # Deliverables & Quality Teaser
    delivery_total_qualified = Column(Integer, default=0)
    delivery_sample_teaser = Column(JSON, nullable=True)
    delivery_csv_path = Column(Text, nullable=True)
    delivery_dossier_path = Column(Text, nullable=True)
    delivery_delivered_at = Column(DateTime, nullable=True)

    # Benchmark & Errors
    metrics = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)

    # Audit Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    started_processing_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    client_entity = relationship("ClientModel", back_populates="orders")
    manifest_leads = relationship("OrderLeadModel", back_populates="order", cascade="all, delete-orphan")

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
                "city": self.city,
                "limit": self.requested_limit,
                "segment": self.segment,
                "sector": self.sector,
                "keywords_include": self.keywords_include,
                "keywords_exclude": self.keywords_exclude,
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
                "dossier_path": self.delivery_dossier_path,
                "delivered_at": self.delivery_delivered_at.isoformat() if self.delivery_delivered_at else None,
            },
            "metrics": self.metrics or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class OrderLeadModel(Base):
    """
    Products-by-Order Manifest.
    Links each delivered lead to the specific commercial order,
    storing the campaign-tailored 5-touch copy generated for this client.
    """
    __tablename__ = "order_leads"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String(64), ForeignKey("prospecting_orders.order_id"), nullable=False, index=True)
    lead_id = Column(String(64), ForeignKey("leads.lead_id"), nullable=False, index=True)

    # Tailored 5-Touch Copy for this specific client & campaign
    touch_1_linkedin = Column(Text, nullable=True)
    touch_2_cold_email_sub = Column(Text, nullable=True)
    touch_2_cold_email_body = Column(Text, nullable=True)
    touch_3_followup_sub = Column(Text, nullable=True)
    touch_3_followup_body = Column(Text, nullable=True)
    touch_4_social_proof_sub = Column(Text, nullable=True)
    touch_4_social_proof_body = Column(Text, nullable=True)
    touch_5_breakup_sub = Column(Text, nullable=True)
    touch_5_breakup_body = Column(Text, nullable=True)

    assigned_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("order_id", "lead_id", name="uq_order_lead"),
    )

    order = relationship("OrderModel", back_populates="manifest_leads")
    lead = relationship("LeadModel", back_populates="orders_assigned")
