"""
Smoke tests for Michito Engine and Campaign Loaders
"""

import os
import pytest
from campaign_loader import list_available_campaigns, load_campaign, clean_company_name, format_touch
from segments import SEGMENTS, get_segment_info
from deduplication_ledger import DeduplicationLedger, PERMANENT_EXCLUDED_NITS

def test_available_campaigns():
    campaigns = list_available_campaigns()
    assert len(campaigns) >= 5
    assert "hebi" in campaigns
    assert "chiketto" in campaigns
    assert "facility_services_b2b" in campaigns
    assert "warehouse_aburra_norte" in campaigns
    assert "tinkko_enterprise_offices" in campaigns

def test_load_all_campaigns():
    for camp_id in list_available_campaigns():
        cfg = load_campaign(camp_id)
        assert cfg["id"] == camp_id
        assert "target" in cfg
        assert "touches" in cfg

def test_clean_company_name():
    assert clean_company_name("Acme S.A.S.") == "Acme"
    assert clean_company_name("Inversiones El Roble S.A.") == "Inversiones El Roble"
    assert clean_company_name("Soluciones & Cia. Ltda.") == "Soluciones"

def test_segments_info():
    info = get_segment_info("midmarket")
    assert info is not None
    assert "Medianas Empresas" in info["name_es"]
    assert info["revenue_range_cop"] == "$10.000M - $65.000M COP"

def test_permanent_excluded_nits():
    assert "901048123-5" in PERMANENT_EXCLUDED_NITS  # Tinkko Coworking SAS
