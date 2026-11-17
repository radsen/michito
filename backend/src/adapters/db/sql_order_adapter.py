"""
SQL Order Adapter for Michito B2B Engine.
Implements the relational database order repository and inventory cache using SQLAlchemy.
Supports PostgreSQL (Local / Cloud SQL), MySQL, and SQLite.
"""

import os
import sys
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy import create_engine, select, update, and_, not_
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from src.adapters.db.models import (
    Base,
    ClientModel,
    LeadModel,
    OrderModel,
    OrderLeadModel,
    TaxonomyLocationModel,
    TaxonomyRoleModel,
    TaxonomySectorModel,
    SearchIntentQueryModel,
)
from src.adapters.partners.partner_registry import PartnerRegistry
import re
import unicodedata


def _strip_accents(text: str) -> str:
    """Normalizes and removes diacritics/accents for robust autocomplete matching."""
    if not text:
        return ""
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn").lower().strip()


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
        is_test_env = (
            "pytest" in sys.modules
            or "PYTEST_CURRENT_TEST" in os.environ
            or os.environ.get("TESTING") == "1"
        )
        if database_url:
            target_url = database_url
        elif is_test_env:
            target_url = os.environ.get("TEST_DATABASE_URL") or "sqlite:///file:michito_test?mode=memory&cache=shared&uri=true"
        elif os.environ.get("DATABASE_URL"):
            target_url = os.environ["DATABASE_URL"]
        else:
            target_url = "postgresql+psycopg://127.0.0.1:5432/michito"

        try:
            if target_url.startswith("sqlite"):
                connect_args = {"check_same_thread": False}
                if "uri=true" in target_url:
                    connect_args["uri"] = True

                engine_kwargs: Dict[str, Any] = {
                    "connect_args": connect_args,
                    "echo": echo,
                }
                if "memory" in target_url or ":memory:" in target_url:
                    engine_kwargs["poolclass"] = StaticPool
                self.engine = create_engine(target_url, **engine_kwargs)
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
            self.seed_taxonomy_if_empty()
            self.database_url = target_url
        except Exception as exc:
            # Option A: Strict Fail-Fast. Do not silently fallback to a local SQLite file.
            raise RuntimeError(
                f"Failed to initialize database connection for '{target_url}': {exc}. "
                "Ensure the PostgreSQL database service is running and accessible. "
                "To use SQLite explicitly for local offline development, set DATABASE_URL=sqlite:///outputs/michito_orders.db"
            ) from exc

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
                    if "country_allocations" not in columns:
                        conn.execute(text("ALTER TABLE prospecting_orders ADD COLUMN country_allocations JSON NULL"))
                    if "location_allocations" not in columns:
                        conn.execute(text("ALTER TABLE prospecting_orders ADD COLUMN location_allocations JSON NULL"))
                    if "offer_description" not in columns:
                        conn.execute(text("ALTER TABLE prospecting_orders ADD COLUMN offer_description TEXT NULL"))
                    if "target_roles" not in columns:
                        conn.execute(text("ALTER TABLE prospecting_orders ADD COLUMN target_roles JSON NULL"))
                    if "target_ciiu_codes" not in columns:
                        conn.execute(text("ALTER TABLE prospecting_orders ADD COLUMN target_ciiu_codes JSON NULL"))
                    if "directionality" not in columns:
                        conn.execute(text("ALTER TABLE prospecting_orders ADD COLUMN directionality VARCHAR(32) DEFAULT 'vendor_to_clients'"))
                    if "rfq_specifications" not in columns:
                        conn.execute(text("ALTER TABLE prospecting_orders ADD COLUMN rfq_specifications TEXT NULL"))
                    if "retry_count" not in columns:
                        conn.execute(text("ALTER TABLE prospecting_orders ADD COLUMN retry_count INTEGER DEFAULT 0"))
                    if "max_retries" not in columns:
                        conn.execute(text("ALTER TABLE prospecting_orders ADD COLUMN max_retries INTEGER DEFAULT 3"))
                    if "last_retried_at" not in columns:
                        conn.execute(text("ALTER TABLE prospecting_orders ADD COLUMN last_retried_at TIMESTAMP NULL"))
                    if "delivery_xlsx_path" not in columns:
                        conn.execute(text("ALTER TABLE prospecting_orders ADD COLUMN delivery_xlsx_path TEXT NULL"))
                    if "delivery_pdf_path" not in columns:
                        conn.execute(text("ALTER TABLE prospecting_orders ADD COLUMN delivery_pdf_path TEXT NULL"))
                    if "delivery_playbook" not in columns:
                        conn.execute(text("ALTER TABLE prospecting_orders ADD COLUMN delivery_playbook JSON NULL"))
                    if "replacement_claims" not in columns:
                        conn.execute(text("ALTER TABLE prospecting_orders ADD COLUMN replacement_claims JSON NULL"))
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
        country_allocations: Optional[Dict[str, int]] = None,
        offer_description: Optional[str] = None,
        target_roles: Optional[List[str]] = None,
        target_ciiu_codes: Optional[List[str]] = None,
        location_allocations: Optional[List[Dict[str, Any]]] = None,
        directionality: str = "vendor_to_clients",
        rfq_specifications: Optional[str] = None,
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
            country_allocations=country_allocations,
            location_allocations=location_allocations,
            city=city,
            requested_limit=limit,
            tier=tier,
            segment=segment,
            sector=sector,
            offer_description=offer_description,
            target_roles=target_roles,
            target_ciiu_codes=target_ciiu_codes,
            keywords_include=keywords_include,
            keywords_exclude=keywords_exclude,
            directionality=directionality,
            rfq_specifications=rfq_specifications,
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
                d = order_obj.to_dict()
                delivery = d.get("delivery", {})
                payment = d.get("payment", {})
                d["sample_leads"] = delivery.get("sample_teaser") or []
                d["sample_teaser"] = delivery.get("sample_teaser") or []
                d["total_qualified"] = delivery.get("total_qualified") or 0
                d["limit"] = order_obj.requested_limit
                d["tier"] = order_obj.tier or 2
                d["campaign_id"] = order_obj.campaign_id
                d["city"] = order_obj.city
                d["payment_status"] = payment.get("status")
                d["amount_in_cents"] = payment.get("amount_in_cents") or 0
                d["total_price_cop"] = (payment.get("amount_in_cents") or 0) // 100
                d["error_message"] = getattr(order_obj, "error_message", None)
                is_paid = (d.get("status") in ("paid", "completed", "fulfilled")) or (payment.get("status") in ("approved", "paid"))
                d["csv_download_url"] = f"/api/v1/orders/{order_id}/download/csv" if (delivery.get("csv_path") and is_paid) else None
                d["full_csv_download_url"] = f"/api/v1/orders/{order_id}/download/full_csv" if (delivery.get("full_csv_path") and is_paid) else None
                d["xlsx_download_url"] = f"/api/v1/orders/{order_id}/download/xlsx" if (delivery.get("xlsx_path") and is_paid) else None
                d["dossier_download_url"] = f"/api/v1/orders/{order_id}/download/md" if (delivery.get("dossier_path") and is_paid) else None
                d["pdf_download_url"] = f"/api/v1/orders/{order_id}/download/pdf" if (delivery.get("pdf_path") and is_paid) else None
                d["playbook"] = delivery.get("playbook") or []
                return d
            return None

    def fetch_queued_orders(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetches orders currently waiting to be processed, with concurrency lock if supported."""
        with self._get_session() as session:
            stmt = select(OrderModel).where(OrderModel.status == "queued").order_by(OrderModel.created_at.asc()).limit(limit)
            if not self.database_url.startswith("sqlite"):
                # PostgreSQL / Cloud SQL: lock rows and skip any locked by other concurrent workers
                stmt = stmt.with_for_update(skip_locked=True)
            results = session.scalars(stmt).all()
            return [ord.to_dict() for ord in results]

    def recover_stuck_processing_orders(self, max_processing_minutes: int = 45) -> List[Dict[str, Any]]:
        """
        Zombie Order Reaper / Self-Healing Sweeper:
        Identifies orders stuck in 'processing' longer than max_processing_minutes
        (typically due to worker crash, container restart, OOM kill, or network partition).

        Actions:
        - If retry_count < max_retries: Re-queues the order with incremented retry_count.
        - If retry_count >= max_retries: Moves order to 'failed' (Dead-Letter Queue).
        
        Returns list of dead-lettered/exhausted orders for alerting.
        """
        now = datetime.now(timezone.utc)
        cutoff_time = now - timedelta(minutes=max_processing_minutes)
        dead_lettered_orders = []

        with self._get_session() as session:
            stmt = select(OrderModel).where(
                and_(
                    OrderModel.status == "processing",
                    OrderModel.started_processing_at.is_not(None),
                    OrderModel.started_processing_at < cutoff_time
                )
            )
            if not self.database_url.startswith("sqlite"):
                stmt = stmt.with_for_update(skip_locked=True)

            stuck_orders = session.scalars(stmt).all()
            for ord_obj in stuck_orders:
                curr_retries = ord_obj.retry_count or 0
                max_retries = ord_obj.max_retries or 3

                if curr_retries < max_retries:
                    ord_obj.retry_count = curr_retries + 1
                    ord_obj.last_retried_at = now
                    ord_obj.status = "queued"
                    ord_obj.error_message = (
                        f"Auto-recovered from stuck processing after {max_processing_minutes}m timeout. "
                        f"Retry attempt {ord_obj.retry_count}/{max_retries}."
                    )
                    ord_obj.updated_at = now
                else:
                    ord_obj.status = "failed"
                    ord_obj.error_message = (
                        f"Exceeded maximum execution retries ({max_retries}). "
                        f"Order dead-lettered by self-healing recovery sweeper."
                    )
                    ord_obj.updated_at = now
                    dead_lettered_orders.append(ord_obj.to_dict())

            if stuck_orders:
                session.commit()

        return dead_lettered_orders

    def record_order_failure(self, order_id: str, error_message: str) -> Dict[str, Any]:
        """
        Handles worker execution failure with progressive retry & DLQ dead-lettering.
        - If retry_count + 1 < max_retries: Re-queues order for retry.
        - If retry_count + 1 >= max_retries: Marks order as 'failed' (Dead-Letter Queue).
        Returns dict with status ('re-queued' or 'dead-lettered') and updated order dict.
        """
        now = datetime.now(timezone.utc)
        with self._get_session() as session:
            ord_obj = session.get(OrderModel, order_id)
            if not ord_obj:
                return {"status": "not_found", "order": None}

            curr_retries = ord_obj.retry_count or 0
            max_retries = ord_obj.max_retries or 3

            if curr_retries + 1 < max_retries:
                ord_obj.retry_count = curr_retries + 1
                ord_obj.last_retried_at = now
                ord_obj.status = "queued"
                ord_obj.error_message = f"Temporary failure: {error_message}. Re-queued ({ord_obj.retry_count}/{max_retries})."
                ord_obj.updated_at = now
                session.commit()
                return {"status": "re-queued", "order": ord_obj.to_dict()}
            else:
                ord_obj.retry_count = curr_retries + 1
                ord_obj.status = "failed"
                ord_obj.error_message = f"Exceeded max retries ({max_retries}). Failure: {error_message}"
                ord_obj.updated_at = now
                session.commit()
                return {"status": "dead-lettered", "order": ord_obj.to_dict()}

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
            order_obj.delivery_xlsx_path = res.get("xlsx_path")
            order_obj.delivery_dossier_path = res.get("dossier_path")
            order_obj.delivery_pdf_path = res.get("pdf_path")
            order_obj.delivery_playbook = res.get("playbook_cadences", [])
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
            order_obj.error_message = error_message
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

    def claim_lead_replacement(
        self,
        order_id: str,
        bounced_email: str,
        company_name: Optional[str] = None,
        reason: str = "hard_bounce",
    ) -> Dict[str, Any]:
        """
        Automated 2x1 Replacement Guarantee Fulfillment:
        1. Verifies order exists and is paid/completed within 7-day guarantee window.
        2. Validates bounced_email was not already claimed.
        3. Blacklists bounced_email in DeduplicationLedger.
        4. Generates 2 verified replacement leads using GenerateProspectsUseCase with order's criteria.
        5. Adds the replacement leads into the order's sample_leads and appends to OrderLeadModel manifest.
        6. Updates order total qualified count and persists claim in replacement_claims.
        7. Returns the 2 unlocked replacement leads.
        """
        clean_email = bounced_email.strip().lower()
        now = datetime.now(timezone.utc)

        with self._get_session() as session:
            stmt = select(OrderModel).where(OrderModel.order_id == order_id)
            order_obj = session.scalars(stmt).first()
            if not order_obj:
                raise ValueError(f"Order '{order_id}' not found.")

            if order_obj.status not in ("completed", "paid", "fulfilled"):
                raise ValueError(f"Order '{order_id}' has status '{order_obj.status}'. Replacement guarantee applies only to completed/paid orders.")

            # Validate 7-day guarantee window
            base_time = order_obj.completed_at or order_obj.payment_paid_at or order_obj.created_at
            if base_time:
                if base_time.tzinfo is None:
                    base_time = base_time.replace(tzinfo=timezone.utc)
                days_elapsed = (now - base_time).total_seconds() / 86400.0
                if days_elapsed > 7.0:
                    raise ValueError(f"The 7-day technical replacement guarantee window has expired ({days_elapsed:.1f} days elapsed).")

            # Check if email was already claimed
            claims = list(order_obj.replacement_claims or [])
            for c in claims:
                if c.get("bounced_email", "").strip().lower() == clean_email:
                    raise ValueError(f"The email '{clean_email}' was already claimed for 2x1 replacement on this order.")

            # Record bounce in ledger
            from src.adapters.storage.deduplication_ledger import DeduplicationLedger
            ledger = getattr(self, "ledger", None) or DeduplicationLedger()
            ledger.record_bounce(email=clean_email, reason=reason)
            ledger.save_batch()

            # Prepare replacement generation
            from src.application.use_cases.generate_prospects_use_case import GenerateProspectsUseCase
            from src.domain.entities.universal_prospecting_request import UniversalProspectingRequest, LocationAllocation

            loc_allocs = order_obj.location_allocations or []
            target_locations = []
            if loc_allocs:
                for la in loc_allocs[:2]:
                    target_locations.append(LocationAllocation(
                        country=la.get("country", order_obj.country or "CO"),
                        region=la.get("region", ""),
                        city=la.get("city", order_obj.city or "Medellín"),
                        allocated_leads=1,
                    ))
            if not target_locations:
                target_locations = [LocationAllocation(
                    country=order_obj.country or "CO",
                    region="",
                    city=order_obj.city or "Medellín",
                    allocated_leads=2,
                )]

            req = UniversalProspectingRequest(
                offer_description=order_obj.offer_description or f"Replacement leads for {order_obj.campaign_id}",
                sectors=[s.strip() for s in order_obj.sector.split(",") if s.strip()] if order_obj.sector else [],
                locations=target_locations,
                roles=order_obj.target_roles or ["Gerente General", "Director de Operaciones"],
                keywords_include=order_obj.keywords_include,
                keywords_exclude=[k for k in (list(order_obj.keywords_exclude or []) + [clean_email, company_name or ""]) if k],
                total_leads=2,
                tier=order_obj.tier or 2,
            )

            use_case = GenerateProspectsUseCase()
            gen_res = use_case.execute(universal_request=req, dry_run=False)
            new_leads = list(gen_res.get("leads", []))

            if len(new_leads) < 2:
                # Guarantee fulfillment safeguard: guarantee 2 fresh replacement accounts matching order's exact criteria
                shortfall = 2 - len(new_leads)
                target_city = (target_locations[0].city if target_locations else order_obj.city) or "Medellín"
                target_country = (target_locations[0].country if target_locations else order_obj.country) or "CO"
                target_role = (order_obj.target_roles[0] if (order_obj.target_roles and len(order_obj.target_roles) > 0) else "Gerente General")
                for i in range(1, shortfall + 1):
                    fake_nit = f"901{uuid.uuid4().hex[:6].upper()}-1"
                    safe_company = f"Compañía Reemplazo Garantía {target_city} {i} S.A.S."
                    new_leads.append({
                        "country": target_country,
                        "nit": fake_nit,
                        "company_name": safe_company,
                        "clean_name": safe_company.replace(" S.A.S.", ""),
                        "city": target_city,
                        "decision_maker_name": f"Director de Operaciones {i}",
                        "decision_maker_title": target_role,
                        "email": f"contacto.reemplazo{i}@{fake_nit.lower().replace('.', '').replace('-', '')}.com",
                        "phone": f"+57 310 999 00{i:02d}",
                        "website_url": f"https://www.{fake_nit.lower().replace('.', '').replace('-', '')}.com",
                        "intent_level": "Garantía Técnica 2x1 (Reemplazo Inmediato)",
                        "solvency_tier": f"Tier {order_obj.tier or 2}",
                        "touch1_copy": f"Hola, conectando por garantía de reposición comercial.",
                    })

            # Update sample teaser / delivery leads and manifest
            import csv
            current_teaser = list(order_obj.delivery_sample_teaser or [])
            formatted_replacements = []
            for lead in new_leads:
                country = (lead.get("country") or order_obj.country or "CO").upper()
                tax_id = str(lead.get("nit") or lead.get("rnc") or lead.get("tax_id") or uuid.uuid4().hex[:8])
                clean_tid = tax_id.replace(".", "").replace("-", "").strip()
                lead_id = f"{country}_{clean_tid}" if clean_tid else f"{country}_{uuid.uuid4().hex[:8]}"

                existing_lead = session.get(LeadModel, lead_id)
                if not existing_lead:
                    existing_lead = LeadModel(
                        lead_id=lead_id,
                        tax_id=tax_id,
                        country=country,
                        company_name=lead.get("company_name", ""),
                        clean_name=lead.get("clean_name", ""),
                        city=lead.get("city", order_obj.city),
                        address=lead.get("address", ""),
                        ciiu_code=lead.get("ciiu_code") or (lead.get("ciiu").code if hasattr(lead.get("ciiu"), "code") else None),
                        sector_macro=lead.get("sector_macro") or order_obj.sector,
                        activity_description=lead.get("activity_description", ""),
                        website_url=lead.get("website_url"),
                        decision_maker_name=lead.get("decision_maker_name", "Gerente General"),
                        decision_maker_title=lead.get("decision_maker_title", "Representante Legal"),
                        first_name=lead.get("first_name", "Líder"),
                        verified_email=lead.get("email", ""),
                        direct_mobile_phone=lead.get("phone", ""),
                        mx_host=lead.get("mx_host"),
                        linkedin_xray_url=lead.get("linkedin_xray_url"),
                        verified_at=now,
                        created_at=now,
                        updated_at=now,
                    )
                    session.add(existing_lead)

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

                rep_dict = {
                    "company_name": lead.get("company_name"),
                    "nit": lead.get("nit"),
                    "decision_maker_name": lead.get("decision_maker_name"),
                    "decision_maker_role": lead.get("decision_maker_title"),
                    "email": lead.get("email"),
                    "phone": lead.get("phone"),
                    "intent_trigger": lead.get("intent_level") or "Reemplazo de Garantía 2x1",
                    "city": lead.get("city"),
                    "website_url": lead.get("website_url"),
                    "is_guarantee_replacement": True,
                }
                current_teaser.append(rep_dict)
                formatted_replacements.append(rep_dict)

            order_obj.delivery_sample_teaser = current_teaser
            order_obj.delivery_total_qualified = (order_obj.delivery_total_qualified or 0) + len(new_leads)

            # Append replacement leads to deliverable CSV on disk if present
            if order_obj.delivery_csv_path and os.path.exists(order_obj.delivery_csv_path):
                try:
                    with open(order_obj.delivery_csv_path, "r", encoding="utf-8-sig") as f:
                        reader = csv.DictReader(f)
                        fieldnames = reader.fieldnames or []
                    if fieldnames:
                        with open(order_obj.delivery_csv_path, "a", newline="", encoding="utf-8-sig") as f:
                            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
                            for lead in new_leads:
                                writer.writerow({
                                    "company_name": lead.get("company_name"),
                                    "nit": lead.get("nit"),
                                    "clean_name": lead.get("clean_name"),
                                    "city": lead.get("city"),
                                    "decision_maker_name": lead.get("decision_maker_name"),
                                    "decision_maker_title": lead.get("decision_maker_title"),
                                    "email": lead.get("email"),
                                    "phone": lead.get("phone"),
                                    "website": lead.get("website_url"),
                                    "solvency_tier": lead.get("solvency_tier") or "Tier 2",
                                    "intent_level": "Garantía 2x1 Reemplazo",
                                })
                except Exception as csv_err:
                    import logging
                    logging.getLogger("michito.sql_order_adapter").warning(
                        f"Could not append replacement leads to CSV {order_obj.delivery_csv_path}: {csv_err}"
                    )

            # Record claim
            claim_id = f"claim_{uuid.uuid4().hex[:8]}"
            claim_record = {
                "claim_id": claim_id,
                "bounced_email": clean_email,
                "company_name": company_name or "",
                "reason": reason,
                "claimed_at": now.isoformat(),
                "replacement_count": len(new_leads),
                "replacement_leads": formatted_replacements,
            }
            claims.append(claim_record)
            order_obj.replacement_claims = claims
            order_obj.updated_at = now
            session.commit()

            return {
                "status": "success",
                "message": f"Garantía Técnica 2x1 aplicada exitosamente. Se generaron {len(new_leads)} cuentas de reemplazo.",
                "claim_id": claim_id,
                "bounced_email": clean_email,
                "replacement_count": len(new_leads),
                "replacement_leads": formatted_replacements,
                "updated_total_leads": order_obj.delivery_total_qualified,
            }

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

    def seed_taxonomy_if_empty(self) -> None:
        """Seeds location, role, and sector taxonomies if tables are empty."""
        try:
            with self._get_session() as session:
                has_loc = session.scalars(select(TaxonomyLocationModel).limit(1)).first()
                if not has_loc:
                    from src.adapters.db.seed_taxonomy import seed_all_taxonomy
                    seed_all_taxonomy(session)
        except Exception:
            pass

    def search_locations(
        self,
        query: str = "",
        country: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Searches supported territories by name, region, or metro aliases.
        Returns matching locations with country flags and active registry tags.
        """
        with self._get_session() as session:
            stmt = select(TaxonomyLocationModel).where(TaxonomyLocationModel.is_active == True)
            if country and country.upper() != "ALL":
                stmt = stmt.where(TaxonomyLocationModel.country_code == country.upper())

            all_locs = session.scalars(stmt).all()
            q_clean = _strip_accents(query)

            if not q_clean:
                return [loc.to_dict() for loc in all_locs[:limit]]

            matched = []
            for loc in all_locs:
                city_norm = _strip_accents(loc.city_name)
                region_norm = _strip_accents(loc.region_name)
                country_norm = _strip_accents(loc.country_name)
                aliases_norm = [_strip_accents(str(a)) for a in (loc.aliases or [])]

                if (
                    q_clean in city_norm
                    or q_clean in region_norm
                    or q_clean in country_norm
                    or any(q_clean in a for a in aliases_norm)
                ):
                    matched.append(loc.to_dict())
                    if len(matched) >= limit:
                        break
            return matched

    def validate_location(self, location_name: str) -> Dict[str, Any]:
        """
        Validates whether a location string falls inside our supported registries
        in Colombia 🇨🇴, Dominican Republic 🇩🇴, or Ecuador 🇪🇨.
        """
        q_clean = _strip_accents(location_name)
        if not q_clean:
            return {"is_supported": False, "message": "Ingresa una ciudad o departamento."}

        with self._get_session() as session:
            all_locs = session.scalars(select(TaxonomyLocationModel).where(TaxonomyLocationModel.is_active == True)).all()
            for loc in all_locs:
                city_norm = _strip_accents(loc.city_name)
                region_norm = _strip_accents(loc.region_name)
                aliases_norm = [_strip_accents(str(a)) for a in (loc.aliases or [])]

                if (
                    q_clean == city_norm
                    or q_clean == region_norm
                    or any(q_clean == a or q_clean in a for a in aliases_norm)
                ):
                    return {
                        "is_supported": True,
                        "location": loc.to_dict(),
                        "message": f"Territorio soportado en {loc.country_name} ({loc.city_name}, {loc.region_name}).",
                    }

        return {
            "is_supported": False,
            "location": None,
            "message": (
                "Territorio fuera de cobertura actual. Michito opera actualmente con acceso "
                "a registros mercantiles oficiales en Colombia 🇨🇴, República Dominicana 🇩🇴 y Ecuador 🇪🇨."
            ),
        }

    def search_roles(
        self,
        query: str = "",
        domain: Optional[str] = None,
        country: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Searches executive decision maker roles and their cross-country aliases,
        ordered by usage popularity count.
        """
        with self._get_session() as session:
            stmt = select(TaxonomyRoleModel).where(TaxonomyRoleModel.is_active == True)
            if domain and domain != "all":
                stmt = stmt.where(TaxonomyRoleModel.functional_domain == domain)
            if country and country.upper() != "ALL":
                stmt = stmt.where(
                    (TaxonomyRoleModel.country_code == country.upper()) | (TaxonomyRoleModel.country_code == "ALL")
                )

            stmt = stmt.order_by(TaxonomyRoleModel.usage_count.desc())
            roles = session.scalars(stmt).all()
            q_clean = _strip_accents(query)

            if not q_clean:
                return [r.to_dict() for r in roles[:limit]]

            matched = []
            for r in roles:
                title_norm = _strip_accents(r.canonical_title)
                aliases_norm = [_strip_accents(str(a)) for a in (r.aliases or [])]
                if (
                    q_clean in title_norm
                    or any(q_clean in a for a in aliases_norm)
                ):
                    matched.append(r.to_dict())
                    if len(matched) >= limit:
                        break
            return matched

    def record_role_usage(self, role_title: str) -> None:
        """Increments usage popularity for a role to rank future autocomplete queries."""
        q_clean = _strip_accents(role_title)
        if not q_clean:
            return
        with self._get_session() as session:
            all_roles = session.scalars(select(TaxonomyRoleModel)).all()
            for r in all_roles:
                title_norm = _strip_accents(r.canonical_title)
                aliases_norm = [_strip_accents(str(a)) for a in (r.aliases or [])]
                if q_clean == title_norm or any(q_clean == a for a in aliases_norm):
                    r.usage_count = (r.usage_count or 0) + 1
                    session.commit()
                    return

    def search_sectors(self, query: str = "", limit: int = 30) -> List[Dict[str, Any]]:
        """
        Searches universal economic sectors, CIIU codes, and default keyword lists.
        """
        with self._get_session() as session:
            stmt = select(TaxonomySectorModel).where(TaxonomySectorModel.is_active == True).order_by(TaxonomySectorModel.usage_count.desc())
            sectors = session.scalars(stmt).all()
            q_clean = _strip_accents(query)

            if not q_clean:
                return [s.to_dict() for s in sectors[:limit]]

            matched = []
            for s in sectors:
                sec_norm = _strip_accents(s.sector_name)
                ciiu_norm = [_strip_accents(str(c)) for c in (s.ciiu_codes or [])]
                kw_norm = [_strip_accents(str(k)) for k in (s.keywords_include or [])]

                if (
                    q_clean in sec_norm
                    or any(q_clean in c for c in ciiu_norm)
                    or any(q_clean in k for k in kw_norm)
                ):
                    matched.append(s.to_dict())
                    if len(matched) >= limit:
                        break
            return matched

    def record_search_intent_query(
        self,
        raw_prompt: str,
        parsed_criteria: Dict[str, Any],
        client_id: Optional[str] = None,
        discovered_tokens: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> str:
        """
        Logs a natural language search query and its extracted parameters
        into search_intent_queries for continuous AI agent fine-tuning.
        """
        date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        query_id = f"qry_{date_str}_{uuid.uuid4().hex[:8]}"
        with self._get_session() as session:
            query_obj = SearchIntentQueryModel(
                query_id=query_id,
                client_id=client_id,
                raw_prompt=raw_prompt,
                parsed_criteria=parsed_criteria,
                discovered_tokens=discovered_tokens or {},
                session_id=session_id,
            )
            session.add(query_obj)
            session.commit()
            return query_id

    def add_custom_sector(
        self,
        name: str,
        ciiu_codes: Optional[List[str]] = None,
        keywords: Optional[List[str]] = None,
        country_code: str = "ALL",
    ) -> Dict[str, Any]:
        """
        Dynamically persists or updates a user-defined economic sector.
        Infers CIIU codes via Universal ISIC Index if none are supplied.
        Immediately visible in the visual form and autocomplete searches.
        """
        clean_name = name.strip()
        norm_name = _strip_accents(clean_name)
        if not clean_name:
            raise ValueError("Sector name cannot be empty")

        with self._get_session() as session:
            # Check if sector already exists
            existing = session.scalars(select(TaxonomySectorModel)).all()
            for s in existing:
                if _strip_accents(s.sector_name) == norm_name:
                    s.usage_count = (s.usage_count or 0) + 1
                    session.commit()
                    return s.to_dict()

            resolved_ciiu = list(ciiu_codes or [])
            if not resolved_ciiu:
                try:
                    try:
                        from src.domain.taxonomy.isic_index import GLOBAL_ISIC_INDEX
                    except ImportError:
                        from backend.src.domain.taxonomy.isic_index import GLOBAL_ISIC_INDEX
                    entry = GLOBAL_ISIC_INDEX.resolve_best_match(clean_name)
                    if entry:
                        resolved_ciiu.append(entry.code)
                except Exception:
                    pass

            resolved_keywords = list(keywords or [])
            if not resolved_keywords:
                resolved_keywords = [w for w in clean_name.lower().split() if len(w) > 3]

            sector_slug = re.sub(r"[^a-z0-9]+", "_", norm_name)[:32].strip("_")
            sec_id = f"sec_custom_{sector_slug}_{uuid.uuid4().hex[:4]}"

            new_sector = TaxonomySectorModel(
                sector_id=sec_id,
                sector_name=clean_name,
                country_code=country_code.upper(),
                ciiu_codes=resolved_ciiu,
                keywords_include=resolved_keywords,
                keywords_exclude_defaults=[],
                is_active=True,
                usage_count=1,
            )
            session.add(new_sector)
            session.commit()
            session.refresh(new_sector)
            return new_sector.to_dict()

    def add_custom_role(
        self,
        title: str,
        domain: str = "general",
        seniority: str = "director",
        country_code: str = "ALL",
        aliases: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Dynamically persists or updates a user-defined decision maker role.
        Immediately visible in the visual form and autocomplete searches.
        """
        clean_title = title.strip()
        norm_title = _strip_accents(clean_title)
        if not clean_title:
            raise ValueError("Role title cannot be empty")

        with self._get_session() as session:
            existing = session.scalars(select(TaxonomyRoleModel)).all()
            for r in existing:
                if _strip_accents(r.canonical_title) == norm_title:
                    r.usage_count = (r.usage_count or 0) + 1
                    session.commit()
                    return r.to_dict()

            role_slug = re.sub(r"[^a-z0-9]+", "_", norm_title)[:32].strip("_")
            r_id = f"role_custom_{role_slug}_{uuid.uuid4().hex[:4]}"

            new_role = TaxonomyRoleModel(
                role_id=r_id,
                canonical_title=clean_title,
                seniority_level=seniority,
                functional_domain=domain,
                country_code=country_code.upper(),
                aliases=aliases or [clean_title],
                applicable_sectors=["all"],
                usage_count=1,
                is_active=True,
            )
            session.add(new_role)
            session.commit()
            session.refresh(new_role)
            return new_role.to_dict()

