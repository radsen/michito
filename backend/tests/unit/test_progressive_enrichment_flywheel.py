"""
Unit Test Suite for the Hybrid Asymmetric / Progressive Enrichment Flywheel (Option C).

Verifies:
1. Tier 1 base harvesting achieves zero speculative compute (skipping NIIF underwriting, heavy scraping)
   and asymmetrically persists statutory profiles (Company, Individual, Channel) to the local Lakehouse.
2. Tier 2 read-through cache checks CompanyModel first, achieving 0ms registry latency, protecting SODA rate limits,
   and performing only the required delta enrichment (MX/mobile validation, dynamic copy).
3. Tier 3 underwriting strictly gates balance sheet / EBITDA solvency and litigation docket analysis to Tier 3 orders.
4. Law firm / accounting proxy detection via network_footprint_count on contact channels.
"""

import pytest
from unittest.mock import MagicMock
from datetime import datetime, timezone

from src.adapters.db.models import (
    CompanyModel,
    IndividualModel,
    CompanyIndividualRoleModel,
    ContactChannelModel,
    CompanyChannelLinkModel,
    IndividualChannelLinkModel,
)
from src.adapters.db.sql_order_adapter import SqlOrderAdapter
from src.application.use_cases.generate_prospects_use_case import GenerateProspectsUseCase
from deduplication_ledger import DeduplicationLedger


@pytest.fixture
def fresh_sql_adapter():
    adapter = SqlOrderAdapter()
    return adapter


def test_tier1_zero_speculative_compute_and_asymmetric_persistence(fresh_sql_adapter, tmp_path):
    """
    Tier 1 query must:
    - Skip NIIF underwriting (zero speculative compute).
    - Asymmetrically persist normalized company, individual, and channels to the Lakehouse.
    """
    mock_underwriter = MagicMock()
    mock_auditor = MagicMock()
    mock_auditor.audit.return_value = (True, "https://www.textilesantioquia.com", "Active Audited Site")

    ledger_path = str(tmp_path / "test_ledger_tier1.json")
    ledger = DeduplicationLedger(ledger_path=ledger_path)
    ledger.reset()

    use_case = GenerateProspectsUseCase(
        web_auditor=mock_auditor,
        underwriter=mock_underwriter,
        order_repository=fresh_sql_adapter,
        ledger=ledger,
        verify_mx_fn=lambda email: (True, "mx1.textilesantioquia.com"),
    )

    result = use_case.execute(
        city="Medellín",
        country="CO",
        limit=2,
        tier=1,
        target_ciiu_codes=["1312"],
        segment="midmarket",
        output_format="csv",
    )

    assert result["status"] == "success"
    assert result["tier"] == 1
    assert len(result["leads"]) >= 1

    # 1. Zero speculative compute: underwriter must NEVER be called on Tier 1
    mock_underwriter.execute.assert_not_called()
    for lead in result["leads"]:
        assert "underwriting" not in lead

    # 2. Verify asymmetric persistence to Lakehouse (CompanyModel, IndividualModel, ContactChannelModel)
    first_lead = result["leads"][0]
    tax_id = first_lead["nit"]
    company_id = f"CO_{tax_id.replace('.', '').replace('-', '').strip()}"

    with fresh_sql_adapter._get_session() as session:
        comp = session.get(CompanyModel, company_id)
        assert comp is not None, f"Company {company_id} should have been asymmetrically persisted"
        assert comp.country == "CO"
        assert comp.primary_ciiu == "1312"

        # Check that individual decision maker was created
        roles = comp.roles
        assert len(roles) >= 1
        role = roles[0]
        assert role.individual is not None
        assert role.individual.full_name

        # Check contact channels
        channels = [link.channel for link in comp.channel_links if link.channel]
        assert len(channels) >= 1


def test_tier2_lakehouse_read_through_cache_hit_and_delta_enrichment(fresh_sql_adapter, tmp_path):
    """
    Subsequent Tier 2 query:
    - Reads candidates directly from local Lakehouse (CompanyModel) with 365-day TTL.
    - Achieves 0ms external registry latency and zero external SODA rate limit consumption.
    - Executes delta enrichment for Tier 2.
    """
    now = datetime.now(timezone.utc)
    # Seed CompanyModel directly
    seeded_tax_id = "901999888"
    company_id = f"CO_{seeded_tax_id}"

    with fresh_sql_adapter._get_session() as session:
        # Pre-populate company
        comp = CompanyModel(
            company_id=company_id,
            tax_id=seeded_tax_id,
            country="CO",
            legal_name="Hilanderías y Tejidos del Norte S.A.S.",
            clean_name="Hilanderías y Tejidos del Norte",
            department="Santander",
            municipality="Bucaramanga",
            primary_ciiu="1512",
            macrosector="Calzado y Marroquinería",
            corporate_type="Sociedad por acciones simplificada",
            website_url="https://www.hilanderiasdelnorte.com",
            website_status="ONLINE_ACTIVE_HTTP200",
            created_at=now,
            updated_at=now,
        )
        session.merge(comp)

        # Pre-populate individual
        ind_id = f"IND_CO_{seeded_tax_id}_carlos_restrepo"
        ind = IndividualModel(
            individual_id=ind_id,
            country="CO",
            full_name="Carlos Restrepo",
            first_name="Carlos",
            created_at=now,
            updated_at=now,
        )
        session.merge(ind)

        # Pre-populate role
        role_id = f"ROLE_{company_id}_{ind_id}"
        role = CompanyIndividualRoleModel(
            role_id=role_id,
            company_id=company_id,
            individual_id=ind_id,
            title="Gerente General",
            role_category="statutory_signer",
            is_operational_decision_maker=True,
            tenure_status="active",
            verified_at=now,
            created_at=now,
            updated_at=now,
        )
        session.merge(role)

        # Pre-populate channels: email & mobile
        ch_email = ContactChannelModel(
            channel_id="CH_EMAIL_carlos.restrepo@hilanderiasdelnorte.com",
            channel_type="corporate_email",
            normalized_value="carlos.restrepo@hilanderiasdelnorte.com",
            raw_value="carlos.restrepo@hilanderiasdelnorte.com",
            verification_state="mx_valid",
            mx_host="mail.hilanderiasdelnorte.com",
            network_footprint_count=1,
            verified_at=now,
            created_at=now,
            updated_at=now,
        )
        session.merge(ch_email)

        ch_phone = ContactChannelModel(
            channel_id="CH_PHONE_573001234567",
            channel_type="mobile_phone",
            normalized_value="+573001234567",
            raw_value="3001234567",
            verification_state="verified_active",
            network_footprint_count=1,
            verified_at=now,
            created_at=now,
            updated_at=now,
        )
        session.merge(ch_phone)

        # Channel links
        session.merge(CompanyChannelLinkModel(
            link_id=f"LNK_CO_{company_id}_{ch_email.channel_id}",
            company_id=company_id,
            channel_id=ch_email.channel_id,
            created_at=now,
        ))
        session.merge(CompanyChannelLinkModel(
            link_id=f"LNK_CO_{company_id}_{ch_phone.channel_id}",
            company_id=company_id,
            channel_id=ch_phone.channel_id,
            created_at=now,
        ))
        session.commit()

    # Now verify that read-through candidate retrieval yields the seeded company
    cached_candidates = fresh_sql_adapter.get_cached_candidates(
        country="CO",
        cities=["Bucaramanga"],
        ciiu_codes=["1512"],
        limit=5,
    )
    assert any(c["nit"] == seeded_tax_id for c in cached_candidates)

    # Mock external harvester to assert it is NOT called when cache satisfies quota
    mock_harvester = MagicMock()
    mock_harvester.fetch_candidates.return_value = []

    ledger_path = str(tmp_path / "test_ledger_tier2.json")
    ledger = DeduplicationLedger(ledger_path=ledger_path)
    ledger.reset()

    use_case = GenerateProspectsUseCase(
        harvester_co=mock_harvester,
        order_repository=fresh_sql_adapter,
        ledger=ledger,
        verify_mx_fn=lambda email: (True, "mx1.hilanderiasdelnorte.com"),
    )

    result = use_case.execute(
        city="Bucaramanga",
        country="CO",
        limit=1,
        tier=2,
        target_ciiu_codes=["1512"],
        output_format="csv",
    )

    assert result["status"] == "success"
    assert result["tier"] == 2
    assert len(result["leads"]) == 1
    delivered_lead = result["leads"][0]
    assert delivered_lead["nit"] == seeded_tax_id
    assert delivered_lead["clean_name"].lower() == "hilanderías y tejidos del norte"
    assert delivered_lead["is_mobile"] is True
    assert delivered_lead["is_cached_statutory"] is True

    # External harvester was NOT needed because Lakehouse read-through satisfied the order
    mock_harvester.fetch_candidates.assert_not_called()


def test_tier3_underwriting_solvency_gated(fresh_sql_adapter, tmp_path):
    """
    Tier 3 query must execute NIIF balance sheet underwriting and litigation risk checks.
    """
    mock_underwriter = MagicMock()
    mock_auditor = MagicMock()
    mock_auditor.audit.return_value = (True, "https://www.example.com", "Active Audited Site")
    mock_uw_result = MagicMock()
    mock_uw_result.underwriting_grade = "AA"
    mock_uw_result.composite_score = 92
    mock_uw_result.ebitda = 450000000.0
    mock_uw_result.ebitda_margin = MagicMock(value=0.22)
    mock_uw_result.solvency_tier = MagicMock(value="Tier 1 High Solvency")
    mock_uw_result.solvency_summary = "High liquidity and EBITDA margins"
    mock_uw_result.litigation_risk_status = "CLEAN_RECORD"
    mock_uw_result.litigation_summary = "Zero active commercial litigation dockets"
    mock_uw_result.credit_recommendation = "Approved 60-day terms up to 100M COP"
    mock_uw_result.to_dict.return_value = {
        "underwriting_grade": "AA",
        "composite_score": 92,
        "solvency_tier": "Tier 1 High Solvency",
        "litigation_risk_status": "CLEAN_RECORD",
    }
    mock_underwriter.execute.return_value = mock_uw_result

    ledger_path = str(tmp_path / "test_ledger_tier3.json")
    ledger = DeduplicationLedger(ledger_path=ledger_path)
    ledger.reset()

    use_case = GenerateProspectsUseCase(
        web_auditor=mock_auditor,
        underwriter=mock_underwriter,
        order_repository=fresh_sql_adapter,
        ledger=ledger,
        verify_mx_fn=lambda email: (True, "mx1.example.com"),
    )

    result = use_case.execute(
        city="Medellín",
        country="CO",
        limit=1,
        tier=3,
        target_ciiu_codes=["6201"],
        output_format="csv",
    )

    assert result["status"] == "success"
    assert result["tier"] == 3
    assert len(result["leads"]) >= 1

    # Underwriter MUST be called for Tier 3
    assert mock_underwriter.execute.called
    first_lead = result["leads"][0]
    assert "underwriting" in first_lead
    assert first_lead["underwriting"]["underwriting_grade"] == "AA"


def test_law_firm_shared_proxy_detection_via_network_footprint(fresh_sql_adapter):
    """
    Verifies that when a contact channel appears across multiple companies (network_footprint_count >= 5),
    it is automatically identified as an external legal/accounting proxy rather than an operational manager.
    """
    now = datetime.now(timezone.utc)
    shared_email = "contacto@gestionlegalbogota.com"

    # Persist 5 distinct companies sharing the same statutory law firm email
    for idx in range(1, 6):
        lead_data = {
            "nit": f"90088800{idx}",
            "company_name": f"Sociedad Fiduciaria {idx} S.A.S.",
            "clean_name": f"Sociedad Fiduciaria {idx}",
            "city": "Bogotá",
            "department": "Cundinamarca",
            "ciiu_code": "6499",
            "email": shared_email,
            "phone": "6017654321",
            "decision_maker_name": "Dr. Fernando Morales",
            "decision_maker_title": "Representante Legal / Abogado Apoderado",
            "decision_maker_category": "external_counsel",
            "website_audit_status": "ONLINE_ACTIVE_HTTP200",
            "website_url": "https://www.gestionlegalbogota.com",
            "mx_host": "mail.gestionlegalbogota.com",
        }
        fresh_sql_adapter.persist_normalized_leads([lead_data], country="CO", fallback_city="Bogotá")

    with fresh_sql_adapter._get_session() as session:
        ch = session.get(ContactChannelModel, f"CH_EMAIL_{shared_email}")
        assert ch is not None
        assert ch.network_footprint_count >= 5

        # Check that the role for the 5th company flagged the individual as non-operational
        company_id = "CO_900888005"
        roles = session.query(CompanyIndividualRoleModel).filter_by(company_id=company_id).all()
        assert len(roles) >= 1
        assert roles[0].is_operational_decision_maker is False
        assert roles[0].role_category == "external_counsel"
