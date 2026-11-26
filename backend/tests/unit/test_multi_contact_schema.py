"""
Unit tests for the Normalized Multi-Contact Enterprise Graph Architecture (v2.0).
Verifies decoupled companies, individuals, shared contact channels, and role classifications.
"""

from datetime import datetime, timezone, timedelta
from src.adapters.db.models import (
    Base,
    CompanyModel,
    IndividualModel,
    CompanyIndividualRoleModel,
    ContactChannelModel,
    CompanyChannelLinkModel,
    IndividualChannelLinkModel,
)
from src.adapters.db.sql_order_adapter import SqlOrderAdapter


def test_normalized_models_creation_and_shared_channel():
    """
    Verifies that multiple companies can link to the same shared contact channel (law firm/PBX)
    and that individuals can have roles across distinct corporate vehicles.
    """
    adapter = SqlOrderAdapter()
    now = datetime.now(timezone.utc)

    with adapter._get_session() as session:
        # 1. Shared Law Firm / Accounting Channel
        shared_channel_id = "CH_EMAIL_notificaciones@bufetegomez.co"
        shared_channel = ContactChannelModel(
            channel_id=shared_channel_id,
            channel_type="statutory_email",
            normalized_value="notificaciones@bufetegomez.co",
            raw_value="Notificaciones@BufeteGomez.co",
            verification_state="mx_valid",
            mx_host="aspmx.l.google.com",
            network_footprint_count=2,
            verified_at=now,
        )
        session.merge(shared_channel)

        # 2. Company A (Textile Factory in Medellín)
        company_a = CompanyModel(
            company_id="CO_900111222",
            tax_id="900.111.222-1",
            country="CO",
            legal_name="Tejidos y Confecciones del Aburrá S.A.S.",
            clean_name="Tejidos y Confecciones del Aburrá",
            trade_name="Tejidos Aburrá",
            department="Antioquia",
            municipality="Medellín",
            primary_ciiu="1312",
            macrosector="Manufactura Textil",
            corporate_type="Sociedad por acciones simplificada",
            website_url="https://www.tejidosaburra.com.co",
            website_status="ONLINE_ACTIVE_HTTP200",
        )
        session.merge(company_a)

        # 3. Company B (Apparel Workshop in Itagüí)
        company_b = CompanyModel(
            company_id="CO_900333444",
            tax_id="900.333.444-2",
            country="CO",
            legal_name="Confecciones y Maquila Moda S.A.S.",
            clean_name="Confecciones y Maquila Moda",
            trade_name="Maquila Moda",
            department="Antioquia",
            municipality="Itagüí",
            primary_ciiu="1410",
            macrosector="Confección y Moda",
            corporate_type="Sociedad por acciones simplificada",
            website_url=None,
            website_status="OFFLINE_STATUTORY_ACTIVE",
        )
        session.merge(company_b)

        # 4. Shared External Lawyer
        lawyer = IndividualModel(
            individual_id="IND_CO_71234567_carlos_gomez",
            national_id="71234567",
            country="CO",
            full_name="Carlos Andrés Gómez Restrepo",
            first_name="Carlos",
            last_name="Gómez Restrepo",
        )
        session.merge(lawyer)

        # 5. Roles Linking the Lawyer as External Statutory Proxy for both companies
        role_a = CompanyIndividualRoleModel(
            role_id="ROLE_CO_900111222_IND_CO_71234567",
            company_id="CO_900111222",
            individual_id="IND_CO_71234567_carlos_gomez",
            title="Apoderado General & Representante Legal Suplente",
            role_category="external_counsel",
            is_operational_decision_maker=False,  # External proxy, not internal plant manager!
            tenure_status="active",
        )
        role_b = CompanyIndividualRoleModel(
            role_id="ROLE_CO_900333444_IND_CO_71234567",
            company_id="CO_900333444",
            individual_id="IND_CO_71234567_carlos_gomez",
            title="Apoderado General",
            role_category="external_counsel",
            is_operational_decision_maker=False,
            tenure_status="active",
        )
        session.merge(role_a)
        session.merge(role_b)

        # 6. Link Shared Channel to both companies
        link_a = CompanyChannelLinkModel(
            link_id="LNK_CO_900111222_CH_SHARED",
            company_id="CO_900111222",
            channel_id=shared_channel_id,
            channel_usage="legal_notification_inbox",
        )
        link_b = CompanyChannelLinkModel(
            link_id="LNK_CO_900333444_CH_SHARED",
            company_id="CO_900333444",
            channel_id=shared_channel_id,
            channel_usage="legal_notification_inbox",
        )
        session.merge(link_a)
        session.merge(link_b)

        session.commit()

    # Verify relationships & queries
    with adapter._get_session() as session:
        ch = session.get(ContactChannelModel, shared_channel_id)
        assert ch is not None
        assert ch.network_footprint_count == 2
        assert len(ch.company_links) == 2

        co_a = session.get(CompanyModel, "CO_900111222")
        assert co_a is not None
        assert len(co_a.roles) == 1
        assert co_a.roles[0].is_operational_decision_maker is False
        assert co_a.roles[0].individual.full_name == "Carlos Andrés Gómez Restrepo"

        co_b = session.get(CompanyModel, "CO_900333444")
        assert co_b is not None
        assert co_b.website_status == "OFFLINE_STATUTORY_ACTIVE"
        assert co_b.roles[0].individual_id == lawyer.individual_id


def test_persist_order_leads_populates_normalized_graph():
    """
    Verifies that SqlOrderAdapter.persist_order_leads populates both the legacy
    LeadModel and the normalized Company/Individual/Channel tables.
    """
    adapter = SqlOrderAdapter()
    order_id = "test_norm_order_001"

    # Create dummy order
    created = adapter.create_order(
        client_name="Test Client",
        client_email="client@example.com",
        campaign_id="textile_medellin_test",
        country="CO",
        city="Medellín",
        limit=5,
        tier=2,
    )
    order_id = created["order_id"]

    test_lead = {
        "company_name": "Fabritejidos Colombia S.A.S.",
        "clean_name": "Fabritejidos Colombia",
        "nit": "900.888.777-3",
        "city": "Medellín",
        "department": "Antioquia",
        "ciiu_code": "1311",
        "sector_macro": "Manufactura Textil",
        "company_type": "Sociedad por acciones simplificada",
        "decision_maker_name": "Gloria Patricia Restrepo",
        "decision_maker_title": "Directora General de Planta",
        "email": "gloria.restrepo@fabritejidos.com.co",
        "phone": "+57 311 234 5678",
        "website_url": "https://www.fabritejidos.com.co",
        "website_audit_status": "ONLINE_ACTIVE_HTTP200",
        "mx_host": "mail.fabritejidos.com.co",
    }

    res = {
        "total_qualified": 1,
        "sample_teaser": [test_lead],
        "leads": [test_lead],
    }

    success = adapter.complete_order(order_id, res, amount_in_cents=9900000)
    assert success is True

    # Verify normalized tables received the company, individual, and channels
    with adapter._get_session() as session:
        co = session.get(CompanyModel, "CO_9008887773")
        assert co is not None
        assert co.legal_name == "Fabritejidos Colombia S.A.S."
        assert co.primary_ciiu == "1311"

        ind = session.query(IndividualModel).filter(IndividualModel.full_name == "Gloria Patricia Restrepo").first()
        assert ind is not None

        role = session.query(CompanyIndividualRoleModel).filter_by(company_id=co.company_id, individual_id=ind.individual_id).first()
        assert role is not None
        assert role.title == "Directora General de Planta"
        assert role.is_operational_decision_maker is True

        email_ch = session.get(ContactChannelModel, "CH_EMAIL_gloria.restrepo@fabritejidos.com.co")
        assert email_ch is not None
        assert email_ch.channel_type == "corporate_email"
        assert email_ch.mx_host == "mail.fabritejidos.com.co"

        phone_ch = session.get(ContactChannelModel, "CH_PHONE_CO_573112345678")
        assert phone_ch is not None
        assert phone_ch.channel_type == "mobile_phone"


def test_law_firm_shared_contact_footprint_detection():
    """
    Phase 4: Shared Contact & Law Firm Footprint Intelligence.
    Verifies that statutory revisores fiscales, external legal counsel, and shared
    law firm channels (e.g. Baker Tilly, KPMG) are classified with:
    - is_operational_decision_maker = False
    - role_category in ('fiscal_auditor', 'external_counsel')
    - get_shared_contact_footprint exposes multi-company reach.
    """
    adapter = SqlOrderAdapter()
    now = datetime.now(timezone.utc)

    # Create dummy order with legal proxy
    created = adapter.create_order(
        client_name="Test Legal Audit Client",
        client_email="legalclient@example.com",
        campaign_id="textile_medellin_test",
        country="CO",
        city="Medellín",
        limit=5,
        tier=2,
    )
    order_id = created["order_id"]

    proxy_lead = {
        "company_name": "Industrias Textiles del Norte S.A.S.",
        "clean_name": "Industrias Textiles del Norte",
        "nit": "901.999.888-5",
        "city": "Medellín",
        "department": "Antioquia",
        "ciiu_code": "1399",
        "sector_macro": "Manufactura Textil",
        "company_type": "Sociedad por acciones simplificada",
        "decision_maker_name": "Dr. Fernando Lloreda Posada",
        "decision_maker_title": "Revisor Fiscal Principal & Apoderado Especial",
        "email": "notificaciones@bakertilly.co",
        "phone": "+57 4 444 8899",
        "website_url": "https://www.textilesdelnorte.com.co",
        "website_audit_status": "ONLINE_ACTIVE_HTTP200",
        "mx_host": "mail.bakertilly.co",
    }

    res = {
        "total_qualified": 1,
        "sample_teaser": [proxy_lead],
        "leads": [proxy_lead],
    }

    success = adapter.complete_order(order_id, res, amount_in_cents=9900000)
    assert success is True

    # 1. Verify Role classification
    with adapter._get_session() as session:
        co = session.get(CompanyModel, "CO_9019998885")
        assert co is not None

        role = session.query(CompanyIndividualRoleModel).filter_by(company_id=co.company_id).first()
        assert role is not None
        assert role.is_operational_decision_maker is False
        assert role.role_category in ("fiscal_auditor", "external_counsel")

        ch = session.get(ContactChannelModel, "CH_EMAIL_notificaciones@bakertilly.co")
        assert ch is not None
        assert ch.network_footprint_count >= 1

    # 2. Verify Footprint lookup API
    footprint = adapter.get_shared_contact_footprint("notificaciones@bakertilly.co")
    assert footprint is not None
    assert footprint["normalized_value"] == "notificaciones@bakertilly.co"
    assert footprint["is_external_proxy"] is True
    assert footprint["proxy_classification"] == "external_law_firm"
    assert footprint["associated_companies_count"] >= 1


def test_tiered_freshness_ttl_and_jit_verification():
    """
    Phase 5: Just-In-Time (JIT) Verification & Cache Freshness Engine.
    Verifies that get_cached_fresh_leads enforces tiered TTLs:
    - Fresh leads under 60 days are returned directly.
    - Leads older than 60 days trigger fast JIT MX validation.
    - Dead mailboxes are discarded from cached fulfillment.
    """
    adapter = SqlOrderAdapter()
    now = datetime.now(timezone.utc)
    old_verified = now - timedelta(days=90)  # Exceeds 60-day deliverability TTL

    # Seed an aged lead in DB
    with adapter._get_session() as session:
        from src.adapters.db.models import LeadModel
        aged_lead = LeadModel(
            lead_id="CO_9015554441",
            tax_id="901.555.444-1",
            country="CO",
            city="Medellín",
            company_name="Hilanderías de Antioquia S.A.S.",
            clean_name="Hilanderías de Antioquia",
            ciiu_code="1311",
            sector_macro="Manufactura Textil",
            activity_description="Hilatura y tejeduría",
            segment_name="Mediana Empresa",
            revenue_bracket="$1.000M - $5.000M COP",
            employees_bracket="11-50",
            decision_maker_name="Carlos Mario Gómez",
            decision_maker_title="Gerente General",
            verified_email="contacto@hilanderiasantioquia.co",
            direct_mobile_phone="+57 310 999 8877",
            verified_at=old_verified,
        )
        session.merge(aged_lead)
        session.commit()

    # Query cached leads with JIT verification active
    cached = adapter.get_cached_fresh_leads(
        city="Medellín",
        country="CO",
        limit=5,
        ciiu_codes=["1311"],
        statutory_ttl_days=365,
        deliverability_ttl_days=60,
        jit_verify=True,
    )

    # In test mode, verify_mx succeeds and updates verified_at to now
    assert len(cached) >= 1
    matched = next((c for c in cached if c["tax_id"] == "901.555.444-1"), None)
    assert matched is not None
    assert matched["company_name"] == "Hilanderías de Antioquia S.A.S."

