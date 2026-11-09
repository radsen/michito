"""
SQL Order Adapter for Michito B2B Engine.
Implements the relational database order repository and inventory cache using SQLAlchemy.
Supports PostgreSQL (Local / Cloud SQL), MySQL, and SQLite.
"""

import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy import create_engine, select, update, and_, not_
from sqlalchemy.orm import sessionmaker, Session

from src.adapters.db.models import Base, ClientModel, LeadModel, OrderModel, OrderLeadModel
from src.adapters.partners.partner_registry import PartnerRegistry


class SqlOrderAdapter:
    """
    Relational Database Order & Lead Inventory Adapter.
    Implements the 4-table normalized commercial architecture:
    - clients
    - leads (Verified inventory asset pool / cache)
    - prospecting_orders
    - order_leads (Products by Order Manifest with 5-touch copy)
    """

    def __init__(self, database_url: Optional[str] = None, echo: bool = False):
        default_url = os.environ.get("DATABASE_URL") or "postgresql+psycopg://127.0.0.1:5432/michito"
        target_url = database_url or default_url

        try:
            if target_url.startswith("sqlite"):
                self.engine = create_engine(
                    target_url,
                    connect_args={"check_same_thread": False},
                    echo=echo,
                )
            else:
                self.engine = create_engine(
                    target_url,
                    pool_pre_ping=True,
                    pool_size=10,
                    max_overflow=20,
                    echo=echo,
                )
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            Base.metadata.create_all(bind=self.engine)
            self._ensure_schema()
            self.database_url = target_url
        except Exception:
            # If PostgreSQL is not reachable, fall back cleanly to SQLite for offline dev/test execution
            if not target_url.startswith("sqlite"):
                self.database_url = "sqlite:///michito_orders.db"
                self.engine = create_engine(
                    self.database_url,
                    connect_args={"check_same_thread": False},
                    echo=echo,
                )
                self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
                Base.metadata.create_all(bind=self.engine)
                self._ensure_schema()
            else:
                raise

    def _ensure_schema(self) -> None:
        """Lightweight schema compatibility checker for SQLite / PostgreSQL."""
        try:
            from sqlalchemy import inspect, text
            inspector = inspect(self.engine)
            table_names = inspector.get_table_names()
            if "prospecting_orders" in table_names:
                columns = [c["name"] for c in inspector.get_columns("prospecting_orders")]
                with self.engine.begin() as conn:
                    if "referral_partner" not in columns:
                        conn.execute(text("ALTER TABLE prospecting_orders ADD COLUMN referral_partner VARCHAR(64) DEFAULT 'direct'"))
                    if "partner_commission_rate" not in columns:
                        conn.execute(text("ALTER TABLE prospecting_orders ADD COLUMN partner_commission_rate FLOAT DEFAULT 0.0"))
                    if "partner_commission_cop" not in columns:
                        conn.execute(text("ALTER TABLE prospecting_orders ADD COLUMN partner_commission_cop BIGINT DEFAULT 0"))
                    if "partner_settled_at" not in columns:
                        conn.execute(text("ALTER TABLE prospecting_orders ADD COLUMN partner_settled_at TIMESTAMP NULL"))
                    if "partner_settlement_status" not in columns:
                        conn.execute(text("ALTER TABLE prospecting_orders ADD COLUMN partner_settlement_status VARCHAR(32) DEFAULT 'pending'"))
            if "clients" in table_names:
                client_columns = [c["name"] for c in inspector.get_columns("clients")]
                if "referral_partner" not in client_columns:
                    with self.engine.begin() as conn:
                        conn.execute(text("ALTER TABLE clients ADD COLUMN referral_partner VARCHAR(64) DEFAULT 'direct'"))
        except Exception:
            pass

    def _get_session(self) -> Session:
        return self.SessionLocal()

    def get_or_create_client(
        self,
        name: str,
        email: str,
        phone: Optional[str] = None,
        channel: str = "web_portal",
        referral_partner: str = "direct"
    ) -> ClientModel:
        """Finds or creates a client record by email."""
        with self._get_session() as session:
            stmt = select(ClientModel).where(ClientModel.email == email)
            client = session.scalars(stmt).first()
            if not client:
                client_id = f"cli_{uuid.uuid4().hex[:8]}"
                client = ClientModel(
                    client_id=client_id,
                    name=name,
                    email=email,
                    phone=phone,
                    channel=channel,
                    referral_partner=referral_partner,
                )
                session.add(client)
                session.commit()
                session.refresh(client)
            return client

    def create_order(
        self,
        client_name: str,
        client_email: str,
        campaign_id: str,
        city: str = "Medellín",
        limit: int = 10,
        country: str = "CO",
        currency: str = "COP",
        client_phone: Optional[str] = None,
        client_channel: str = "web_portal",
        client_id: Optional[str] = None,
        segment: Optional[str] = None,
        sector: Optional[str] = None,
        keywords_include: Optional[List[str]] = None,
        keywords_exclude: Optional[List[str]] = None,
        referral_partner: str = "direct",
        tier: int = 2,
    ) -> Dict[str, Any]:
        """
        Creates a new commercial prospecting order linked to the client account.
        """
        now = datetime.now(timezone.utc)
        date_str = now.strftime("%Y%m%d")
        random_suffix = uuid.uuid4().hex[:6]
        order_id = f"ord_{date_str}_{random_suffix}"

        # Resolve partner configuration
        partner = PartnerRegistry.get(referral_partner)
        resolved_partner_id = partner.partner_id
        partner_comm_rate = partner.commission_rate

        # Resolve or create Client
        client = self.get_or_create_client(
            name=client_name,
            email=client_email,
            phone=client_phone,
            channel=client_channel,
            referral_partner=resolved_partner_id
        )

        order_obj = OrderModel(
            order_id=order_id,
            client_id=client.client_id,
            client_name=client_name,
            client_email=client_email,
            client_phone=client_phone,
            client_channel=client_channel,
            referral_partner=resolved_partner_id,
            partner_commission_rate=partner_comm_rate,
            partner_commission_cop=0,
            partner_settlement_status="pending" if partner_comm_rate > 0 else "not_applicable",
            campaign_id=campaign_id,
            country=country.upper(),
            city=city,
            requested_limit=limit,
            tier=tier,
            segment=segment,
            sector=sector,
            keywords_include=keywords_include,
            keywords_exclude=keywords_exclude,
            status="queued",
            payment_provider="wompi",
            payment_status="pending",
            payment_amount_in_cents=0,
            payment_currency=currency.upper(),
            delivery_total_qualified=0,
            delivery_sample_teaser=[],
            created_at=now,
            updated_at=now,
        )

        with self._get_session() as session:
            session.add(order_obj)
            session.commit()
            session.refresh(order_obj)
            return order_obj.to_dict()

    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves order details by ID."""
        with self._get_session() as session:
            order_obj = session.get(OrderModel, order_id)
            if order_obj:
                return order_obj.to_dict()
            return None

    def fetch_queued_orders(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetches orders currently waiting to be processed."""
        with self._get_session() as session:
            stmt = select(OrderModel).where(OrderModel.status == "queued").limit(limit)
            results = session.scalars(stmt).all()
            return [ord.to_dict() for ord in results]

    def mark_processing(self, order_id: str) -> bool:
        """Transitions order from 'queued' to 'processing' atomically."""
        now = datetime.now(timezone.utc)
        with self._get_session() as session:
            order_obj = session.get(OrderModel, order_id)
            if not order_obj or order_obj.status != "queued":
                return False

            order_obj.status = "processing"
            order_obj.started_processing_at = now
            order_obj.updated_at = now
            session.commit()
            return True

    def get_cached_fresh_leads(
        self,
        city: str,
        country: str = "CO",
        limit: int = 10,
        client_id: Optional[str] = None,
        max_age_days: int = 45,
    ) -> List[Dict[str, Any]]:
        """
        Queries the reusable Lead Inventory for verified fresh leads that have NOT
        been delivered to this specific client yet.
        """
        now = datetime.now(timezone.utc)
        threshold_date = now - timedelta(days=max_age_days)

        with self._get_session() as session:
            stmt = select(LeadModel).where(
                and_(
                    LeadModel.city.ilike(city),
                    LeadModel.country == country.upper(),
                    LeadModel.verified_at >= threshold_date,
                )
            )

            # Exclude leads already sold to this client
            if client_id:
                subquery = (
                    select(OrderLeadModel.lead_id)
                    .join(OrderModel, OrderLeadModel.order_id == OrderModel.order_id)
                    .where(OrderModel.client_id == client_id)
                )
                stmt = stmt.where(not_(LeadModel.lead_id.in_(subquery)))

            stmt = stmt.limit(limit)
            leads = session.scalars(stmt).all()

            results = []
            for lead in leads:
                results.append({
                    "lead_id": lead.lead_id,
                    "tax_id": lead.tax_id,
                    "nit": lead.tax_id,
                    "company_name": lead.company_name,
                    "clean_name": lead.clean_name,
                    "city": lead.city,
                    "address": lead.address,
                    "ciiu_code": lead.ciiu_code,
                    "sector_macro": lead.sector_macro,
                    "activity_description": lead.activity_description,
                    "segment_name": lead.segment_name,
                    "revenue_bracket": lead.revenue_bracket,
                    "employees_bracket": lead.employees_bracket,
                    "website_url": lead.website_url,
                    "website_audit_status": lead.website_audit_status,
                    "decision_maker_name": lead.decision_maker_name,
                    "decision_maker_title": lead.decision_maker_title,
                    "first_name": lead.first_name,
                    "email": lead.verified_email,
                    "phone": lead.direct_mobile_phone,
                    "mx_host": lead.mx_host,
                    "contracts_data": lead.contracts_data,
                    "hiring_xray_url": lead.hiring_xray_url,
                    "expansion_flag": lead.expansion_flag,
                    "linkedin_xray_url": lead.linkedin_xray_url,
                    "verified_at": lead.verified_at.isoformat() if lead.verified_at else None,
                })
            return results

    def complete_order(
        self,
        order_id: str,
        worker_result: Optional[Dict[str, Any]] = None,
        amount_in_cents: int = 0,
        job_result: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Completes the order:
        1. Records generated leads in the `leads` table (reusable inventory pool).
        2. Links each lead to the order via `order_leads` (Products by Order manifest).
        3. Updates order status to 'awaiting_payment'.
        """
        res = worker_result or job_result or {}
        now = datetime.now(timezone.utc)
        leads_data = res.get("leads", [])

        with self._get_session() as session:
            order_obj = session.get(OrderModel, order_id)
            if not order_obj:
                return False

            # 1. Upsert Leads into the Master Inventory Pool
            for lead in leads_data:
                country = lead.get("country", order_obj.country).upper()
                tax_id = str(lead.get("nit") or lead.get("rnc") or lead.get("tax_id") or "")
                lead_id = f"{country}_{tax_id.replace('.', '').replace('-', '').strip()}"

                # Check if lead already exists
                existing_lead = session.get(LeadModel, lead_id)
                ciiu_obj = lead.get("ciiu")
                ciiu_code = getattr(ciiu_obj, "code", lead.get("ciiu_code"))
                sector_macro = getattr(ciiu_obj, "sector_macro", lead.get("sector_macro"))
                desc = getattr(ciiu_obj, "description", lead.get("activity_description"))

                if not existing_lead:
                    existing_lead = LeadModel(
                        lead_id=lead_id,
                        tax_id=tax_id,
                        country=country,
                        company_name=lead.get("company_name", ""),
                        clean_name=lead.get("clean_name", ""),
                        city=lead.get("city", order_obj.city),
                        address=lead.get("address", ""),
                        ciiu_code=ciiu_code,
                        sector_macro=sector_macro,
                        activity_description=desc,
                        segment_name=lead.get("segment_name"),
                        revenue_bracket=lead.get("revenue_bracket"),
                        employees_bracket=lead.get("employees_bracket"),
                        website_url=lead.get("website_url"),
                        website_audit_status=lead.get("website_audit_status"),
                        decision_maker_name=lead.get("decision_maker_name", "Gerente General"),
                        decision_maker_title=lead.get("decision_maker_title", "Representante Legal"),
                        first_name=lead.get("first_name", "Líder"),
                        verified_email=lead.get("email", ""),
                        direct_mobile_phone=lead.get("phone", ""),
                        mx_host=lead.get("mx_host"),
                        contracts_data=lead.get("contracts_data"),
                        hiring_xray_url=lead.get("hiring_xray_url"),
                        expansion_flag=lead.get("expansion_flag"),
                        linkedin_xray_url=lead.get("linkedin_xray_url"),
                        verified_at=now,
                        created_at=now,
                        updated_at=now,
                    )
                    session.add(existing_lead)
                else:
                    # Refresh freshness timestamp & contact details
                    existing_lead.verified_at = now
                    existing_lead.updated_at = now
                    if lead.get("email"):
                        existing_lead.verified_email = lead["email"]
                    if lead.get("phone"):
                        existing_lead.direct_mobile_phone = lead["phone"]

                # 2. Add to Order Manifest (Products by Order)
                manifest_entry = OrderLeadModel(
                    order_id=order_id,
                    lead_id=lead_id,
                    touch_1_linkedin=lead.get("touch1_copy"),
                    touch_2_cold_email_sub=lead.get("touch2_sub"),
                    touch_2_cold_email_body=lead.get("touch2_body"),
                    touch_3_followup_sub=lead.get("touch3_sub"),
                    touch_3_followup_body=lead.get("touch3_body"),
                    touch_4_social_proof_sub=lead.get("touch4_sub"),
                    touch_4_social_proof_body=lead.get("touch4_body"),
                    touch_5_breakup_sub=lead.get("touch5_sub"),
                    touch_5_breakup_body=lead.get("touch5_body"),
                    assigned_at=now,
                )
                session.add(manifest_entry)

            # 3. Update Order Summary
            order_obj.status = "awaiting_payment" if amount_in_cents > 0 else "completed"
            order_obj.delivery_total_qualified = res.get("total_qualified", len(leads_data))
            order_obj.delivery_sample_teaser = res.get("sample_teaser", [])
            order_obj.delivery_csv_path = res.get("csv_path")
            order_obj.delivery_dossier_path = res.get("dossier_path")
            order_obj.metrics = res.get("metrics", {})
            order_obj.completed_at = now
            order_obj.updated_at = now

            if amount_in_cents > 0:
                order_obj.payment_amount_in_cents = amount_in_cents

            if amount_in_cents == 0:
                order_obj.delivery_delivered_at = now

            session.commit()
            return True

    def mark_failed(self, order_id: str, error_message: str) -> bool:
        """Transitions order to 'failed' if an unrecoverable worker error occurs."""
        now = datetime.now(timezone.utc)
        with self._get_session() as session:
            order_obj = session.get(OrderModel, order_id)
            if not order_obj:
                return False
            order_obj.status = "failed"
            order_obj.updated_at = now
            session.commit()
            return True

    def mark_order_paid(
        self,
        order_id: str,
        transaction_id: str,
        amount_in_cents: int,
    ) -> bool:
        """
        Transitions order to 'paid' when payment webhook verifies funds.
        """
        now = datetime.now(timezone.utc)
        with self._get_session() as session:
            order_obj = session.get(OrderModel, order_id)
            if not order_obj:
                return False

            order_obj.status = "paid"
            order_obj.payment_status = "approved"
            order_obj.payment_transaction_id = transaction_id
            order_obj.payment_amount_in_cents = amount_in_cents
            order_obj.payment_paid_at = now
            order_obj.delivery_delivered_at = now
            order_obj.updated_at = now

            # Calculate partner commission if applicable
            if order_obj.partner_commission_rate and order_obj.partner_commission_rate > 0:
                paid_cop = amount_in_cents / 100.0
                order_obj.partner_commission_cop = int(round(paid_cop * order_obj.partner_commission_rate))
                order_obj.partner_settlement_status = "pending"
            else:
                order_obj.partner_commission_cop = 0
                order_obj.partner_settlement_status = "not_applicable"

            session.commit()
            return True

    def get_partner_statement(self, partner_id: str) -> Dict[str, Any]:
        """
        Generates a consolidated affiliate settlement statement for a commercial partner.
        Returns total approved orders, gross revenue, and total commission owed.
        """
        partner = PartnerRegistry.get(partner_id)
        with self._get_session() as session:
            stmt = select(OrderModel).where(
                and_(
                    OrderModel.referral_partner == partner.partner_id,
                    OrderModel.payment_status == "approved"
                )
            )
            orders = session.scalars(stmt).all()

            total_orders = len(orders)
            total_gross_cop = sum(int(o.payment_amount_in_cents or 0) // 100 for o in orders)
            total_comm_cop = sum(int(o.partner_commission_cop or 0) for o in orders)
            pending_comm_cop = sum(int(o.partner_commission_cop or 0) for o in orders if o.partner_settlement_status == "pending")

            return {
                "partner_id": partner.partner_id,
                "partner_name": partner.name,
                "commission_rate": partner.commission_rate,
                "total_orders": total_orders,
                "total_gross_revenue_cop": total_gross_cop,
                "total_commission_owed_cop": total_comm_cop,
                "pending_commission_cop": pending_comm_cop,
                "orders": [
                    {
                        "order_id": o.order_id,
                        "client_name": o.client_name,
                        "client_email": o.client_email,
                        "paid_at": o.payment_paid_at.isoformat() if o.payment_paid_at else None,
                        "gross_amount_cop": int(o.payment_amount_in_cents or 0) // 100,
                        "commission_cop": int(o.partner_commission_cop or 0),
                        "settlement_status": o.partner_settlement_status or "pending",
                    }
                    for o in orders
                ]
            }

    def get_order_manifest(self, order_id: str) -> List[Dict[str, Any]]:
        """Returns the full product manifest of leads assigned to an order."""
        with self._get_session() as session:
            stmt = (
                select(OrderLeadModel, LeadModel)
                .join(LeadModel, OrderLeadModel.lead_id == LeadModel.lead_id)
                .where(OrderLeadModel.order_id == order_id)
            )
            results = session.execute(stmt).all()

            manifest = []
            for order_lead, lead in results:
                manifest.append({
                    "lead_id": lead.lead_id,
                    "company_name": lead.company_name,
                    "city": lead.city,
                    "decision_maker_name": lead.decision_maker_name,
                    "decision_maker_title": lead.decision_maker_title,
                    "verified_email": lead.verified_email,
                    "direct_mobile_phone": lead.direct_mobile_phone,
                    "touches": {
                        "touch1_linkedin": order_lead.touch_1_linkedin,
                        "touch2_cold_email_sub": order_lead.touch_2_cold_email_sub,
                        "touch2_cold_email_body": order_lead.touch_2_cold_email_body,
                        "touch3_followup_sub": order_lead.touch_3_followup_sub,
                        "touch3_followup_body": order_lead.touch_3_followup_body,
                        "touch4_social_proof_sub": order_lead.touch_4_social_proof_sub,
                        "touch4_social_proof_body": order_lead.touch_4_social_proof_body,
                        "touch5_breakup_sub": order_lead.touch_5_breakup_sub,
                        "touch5_breakup_body": order_lead.touch_5_breakup_body,
                    }
                })
            return manifest
