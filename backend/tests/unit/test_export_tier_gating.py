import os
import csv
import pytest
from unittest.mock import MagicMock
from src.application.use_cases.generate_prospects_use_case import GenerateProspectsUseCase
from src.adapters.export.pdf_dossier_adapter import PdfDossierAdapter
import openpyxl


@pytest.fixture
def mock_dependencies():
    mock_harvester = MagicMock()
    mock_harvester.fetch_candidates.return_value = [
        {
            "nit": "900123456",
            "company_name": "Inversiones Bogota SAS",
            "clean_name": "Inversiones Bogota",
            "city": "Bogotá",
            "department": "Cundinamarca",
            "country": "CO",
            "country_name": "Colombia",
            "address": "Calle 100 # 15-20",
            "sector": "Servicios de Software y Tecnología",
            "ciiu_code": "6201",
            "segment_name": "Mediana Empresa",
            "revenue_bracket": "$1.000M - $5.000M COP",
            "employees_bracket": "11-50 empleados",
            "website": "https://inversionesbogota.co",
            "website_audit_status": "ONLINE_ACTIVE_HTTP200",
            "phone": "+57 310 744 0000",
            "phone_line_type": "Línea Móvil Celular",
            "email": "contacto@inversionesbogota.co",
            "decision_maker_name": "Carlos Gomez",
            "decision_maker_title": "Representante Legal",
            "mx_host": "mail.inversionesbogota.co",
            "expansion_flag": "Expansión Bogotá",
        }
    ]

    mock_contracts = MagicMock()
    mock_contracts.fetch_contracts_summary.return_value = {
        "has_contracts": True,
        "contracts_count": 1,
        "total_value_cop": 150000000.0,
        "total_value_display": "$150.0M COP",
        "top_contract_entity": "Alcaldía Mayor de Bogotá",
        "top_contract_value_cop": 150000000.0,
        "top_contract_value_display": "$150.0M COP",
        "top_contract_object": "Servicios de Software",
        "intent_level": "Alto",
    }

    mock_auditor = MagicMock()
    mock_auditor.audit.return_value = (True, "https://inversionesbogota.co", "Sitio Web Auditado y Activo HTTP 200")

    mock_mb = MagicMock()
    mock_mb.verify_email.return_value = "deliverable"

    mock_ledger = MagicMock()
    mock_ledger.is_seen.return_value = False
    mock_ledger.is_duplicate.return_value = False
    mock_ledger.seen_nits = set()

    return {
        "harvester": mock_harvester,
        "contracts": mock_contracts,
        "auditor": mock_auditor,
        "mb": mock_mb,
        "ledger": mock_ledger,
    }


def test_tier_1_export_strictly_gates_direct_contacts(mock_dependencies):
    """
    Tier 1 (Directorio Base) MUST NOT export direct decision maker names, verified personal emails,
    mobile phones, WhatsApp links, commercial triggers, or sales cadences.
    """
    use_case = GenerateProspectsUseCase(
        ledger=mock_dependencies["ledger"],
        harvester_co=mock_dependencies["harvester"],
        contracts_adapter=mock_dependencies["contracts"],
        web_auditor=mock_dependencies["auditor"],
        mailbox_verifier=mock_dependencies["mb"],
        verify_mx_fn=lambda email: (True, "mail.inversionesbogota.co"),
    )
    res = use_case.execute(
        campaign="universal",
        offer_description="Empresas de tecnología y software",
        country="CO",
        city="Bogotá",
        tier=1,
        limit=1,
        output_format="all",
        dry_run=True,
    )

    assert res["status"] == "success"
    assert res["tier"] == 1
    assert len(res["playbook_cadences"]) == 0, "Tier 1 must not contain playbook cadences"

    xlsx_path = res["xlsx_path"]
    csv_path = res["csv_path"]
    full_csv_path = res["full_csv_path"]

    assert os.path.exists(xlsx_path)
    assert os.path.exists(csv_path)
    assert os.path.exists(full_csv_path)

    # 1. Verify XLSX Deliverable
    wb = openpyxl.load_workbook(xlsx_path)
    ws = wb.active
    headers = [cell.value for cell in ws[1] if cell.value is not None]

    # Required Tier 1 Headers
    assert "Company Name" in headers
    assert "NIT" in headers
    assert "City" in headers
    assert "Corporate Phone" in headers
    assert "Website" in headers
    assert "Verification Status" in headers

    # FORBIDDEN Tier 2/3 Headers in Tier 1
    forbidden_tier2_headers = [
        "Official Registered Contact",
        "Official Statutory Title",
        "Targeted Campaign Persona",
        "Decision Maker Name",
        "Official Title",
        "Verified Work Email",
        "WhatsApp Direct Link",
        "Direct Mobile Phone",
        "Commercial Trigger",
        "Recommended Angle",
        "Underwriting Grade",
        "Solvency Tier",
        "Litigation Risk",
    ]
    for forbidden in forbidden_tier2_headers:
        assert forbidden not in headers, f"Data leak: '{forbidden}' found in Tier 1 XLSX headers: {headers}"

    # 2. Verify CSV Deliverable
    with open(csv_path, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        csv_headers = reader.fieldnames or []
        for forbidden in forbidden_tier2_headers:
            assert forbidden not in csv_headers, f"Data leak: '{forbidden}' found in Tier 1 CSV headers: {csv_headers}"

    # 3. Verify Full Intelligence CSV Deliverable
    with open(full_csv_path, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        full_headers = reader.fieldnames or []
        for forbidden in [
            "Official Registered Contact",
            "Verified Work Email",
            "WhatsApp Direct Link",
            "Direct Mobile Phone",
            "Touch 1: LinkedIn Connection Note",
            "Touch 2: Cold Email Subject",
            "Underwriting Grade",
        ]:
            assert forbidden not in full_headers, f"Data leak: '{forbidden}' found in Tier 1 Full Intelligence CSV"

    # 4. Verify Sample Teaser Gating
    teaser = res["sample_teaser"][0]
    assert teaser["decision_maker_name"] is None
    assert teaser["email"] is None
    assert teaser["decision_maker_role"] == "Directorio Institucional"


def test_tier_2_export_includes_contacts_and_cadences(mock_dependencies):
    """
    Tier 2 (Contactos Directos) MUST include direct contacts, email, phone, and 5-touch cadences,
    but MUST NOT include Tier 3 underwriting or litigation risk.
    """
    use_case = GenerateProspectsUseCase(
        ledger=mock_dependencies["ledger"],
        harvester_co=mock_dependencies["harvester"],
        contracts_adapter=mock_dependencies["contracts"],
        web_auditor=mock_dependencies["auditor"],
        mailbox_verifier=mock_dependencies["mb"],
        verify_mx_fn=lambda email: (True, "mail.inversionesbogota.co"),
    )
    res = use_case.execute(
        campaign="universal",
        offer_description="Empresas de tecnología y software",
        country="CO",
        city="Bogotá",
        tier=2,
        limit=1,
        output_format="all",
        dry_run=True,
    )

    assert res["status"] == "success"
    assert res["tier"] == 2
    assert len(res["playbook_cadences"]) == 1

    wb = openpyxl.load_workbook(res["xlsx_path"])
    ws = wb.active
    headers = [cell.value for cell in ws[1] if cell.value is not None]

    # Required Tier 2 Headers
    assert "Official Registered Contact" in headers
    assert "Verified Work Email" in headers
    assert "Corporate Phone" in headers
    assert "Commercial Trigger" in headers
    assert "Recommended Angle" in headers

    # Tier 3 Underwriting MUST NOT leak to Tier 2
    assert "Underwriting Grade" not in headers
    assert "Solvency Tier" not in headers
    assert "Litigation Risk" not in headers


def test_tier_1_pdf_generation_without_contacts(tmp_path):
    """
    Verify PdfDossierAdapter generates valid PDF for Tier 1 with institutional table and without personal touches.
    """
    adapter = PdfDossierAdapter()
    leads = [
        {
            "Company Name": "Soluciones Cloud SAS",
            "Tax ID Type": "NIT",
            "Tax ID": "900555666",
            "Economic Activity": "Desarrollo de Software",
            "City": "Bogotá",
            "Corporate Phone": "+57 1 600 0000",
            "Website": "https://solucionescloud.co",
            "Address": "Cra 7 # 72-10",
        }
    ]
    out_pdf = os.path.join(tmp_path, "tier1_dossier.pdf")
    res = adapter.generate_dossier_pdf(
        campaign_cfg={"name": "Tech Bogotá", "id": "tech_bog", "touches": {}},
        leads=leads,
        output_path=out_pdf,
        tier=1,
    )
    assert os.path.exists(res)
    assert os.path.getsize(res) > 1000
