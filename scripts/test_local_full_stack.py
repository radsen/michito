#!/usr/bin/env python3
"""
Comprehensive Local Full-Stack Test Harness for Michito B2B Engine.
Validates all Stage 1, Stage 2, and Stage 4 additions locally:
- Universal ISIC catalog & sub-millisecond BM25 index
- Dynamic Taxonomy Form-to-DB persistence
- Natural Language Brief Parser (Sales & Procurement directions)
- WhatsApp Conversational Webhook & Meta verification handshake
- Multi-Country Harvester Broadening (CO 🇨🇴, DO 🇩🇴, EC 🇪🇨)
- Full End-to-End Order Qualification Lifecycle & Deliverable Generation
"""

import os
import sys
import time
import json
import shutil
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure root paths are in sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))
sys.path.insert(0, str(REPO_ROOT))

# Test environment settings
os.environ["PYTEST_CURRENT_TEST"] = "1"
os.environ["ENVIRONMENT"] = "test"
os.environ.pop("PUBSUB_EMULATOR_HOST", None)
os.environ.pop("STORAGE_EMULATOR_HOST", None)
os.environ.pop("ORDERS_FEED_WEBHOOK_URL", None)
os.environ.pop("ALERT_WEBHOOK_URL", None)

from src.entrypoints.api.main import app, sql_adapter
from src.domain.taxonomy.isic_index import get_isic_index
from src.adapters.storage.deduplication_ledger import DeduplicationLedger
from src.adapters.storage.local_storage_adapter import LocalStorageAdapter
from src.application.use_cases.generate_prospects_use_case import GenerateProspectsUseCase
from src.entrypoints.workers.order_worker_daemon import OrderWorkerDaemon
from src.domain.entities.universal_prospecting_request import (
    UniversalProspectingRequest,
    SearchDirectionality,
    LocationAllocation,
)

GREEN = "\033[92m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"
BOLD = "\033[1m"

passed_tests = 0
failed_tests = 0


def report(name: str, passed: bool, detail: str = ""):
    global passed_tests, failed_tests
    if passed:
        passed_tests += 1
        print(f" {GREEN}PASS{RESET} {BOLD}{name}{RESET} {CYAN}{detail}{RESET}")
    else:
        failed_tests += 1
        print(f" {RED}FAIL{RESET} {BOLD}{name}{RESET} {YELLOW}{detail}{RESET}")


def main():
    print(f"\n{BOLD}===================================================================={RESET}")
    print(f"{BOLD} MICHITO LOCAL FULL-STACK VALIDATION & SMOKE TEST HARNESS {RESET}")
    print(f"{BOLD}===================================================================={RESET}\n")

    client = TestClient(app)

    # --------------------------------------------------------------------------
    # TEST 1: Sub-Millisecond ISIC BM25 Search Benchmark
    # --------------------------------------------------------------------------
    idx = get_isic_index()
    t0 = time.perf_counter()
    matches = idx.search("reparación y tapizado de muebles de oficina", limit=3)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    is_valid = len(matches) > 0 and matches[0][0].code in ("3110", "9524") and elapsed_ms < 15.0
    report("1. Universal ISIC BM25 Index Benchmark", is_valid, f"Matched {matches[0][0].code} in {elapsed_ms:.2f}ms (<15ms target)")

    # --------------------------------------------------------------------------
    # TEST 2: Dynamic Custom Taxonomy Form-to-DB Persistence
    # --------------------------------------------------------------------------
    custom_niche_payload = {
        "type": "sector",
        "name": "Mantenimiento y Tapicería de Muebles Corporativos",
        "country_code": "CO",
        "keywords": ["tapiceria", "ebanisteria", "silleteria"]
    }
    res_tax = client.post("/api/v1/taxonomy/custom", json=custom_niche_payload)
    tax_data = res_tax.json() if res_tax.status_code == 200 else {}
    item_data = tax_data.get("item", {})
    tax_valid = (
        res_tax.status_code == 200
        and tax_data.get("status") == "success"
        and "mantenimiento" in item_data.get("sector_name", "").lower()
    )
    report("2. Dynamic Taxonomy Form-to-DB Upsert", tax_valid, f"Sector ID: {item_data.get('sector_id')}")

    # --------------------------------------------------------------------------
    # TEST 3: Brief Parser - Buyer / Procurement Mode (Auto-RFQ)
    # --------------------------------------------------------------------------
    proc_brief = {
        "prompt": "Necesito comprar muebles y escritorios para remodelar 3 sedes de Tinkko en Medellín y Bogotá, buscamos talleres o fabricantes",
        "force_fallback": True
    }
    res_proc = client.post("/api/v1/prospecting/parse-brief", json=proc_brief)
    proc_data = res_proc.json().get("data", {}) if res_proc.status_code == 200 else {}
    proc_valid = (
        res_proc.status_code == 200
        and proc_data.get("directionality") == "client_to_vendors"
        and any(c in proc_data.get("ciiu_codes", []) for c in ("3110", "9524"))
        and any("Gerente Comercial" in r or "Director de Ventas" in r for r in proc_data.get("roles", []))
    )
    report("3. Natural Language Brief Parser (Procurement / Auto-RFQ)", proc_valid, f"Direction: {proc_data.get('directionality')}, CIIU: {proc_data.get('ciiu_codes')[:2]}")

    # --------------------------------------------------------------------------
    # TEST 4: Brief Parser - Sales Mode (Cross-Border DO 🇩🇴 & EC 🇪🇨)
    # --------------------------------------------------------------------------
    sales_brief = {
        "prompt": "Vendo software de facturación y gestión académica para colegios privados en Santo Domingo y Quito, 50 prospectos",
        "force_fallback": True
    }
    res_sales = client.post("/api/v1/prospecting/parse-brief", json=sales_brief)
    sales_data = res_sales.json().get("data", {}) if res_sales.status_code == 200 else {}
    countries_found = {loc.get("country") for loc in sales_data.get("locations", [])}
    sales_valid = (
        res_sales.status_code == 200
        and sales_data.get("directionality") == "vendor_to_clients"
        and any(c in sales_data.get("ciiu_codes", []) for c in ("8530", "8521"))
        and "DO" in countries_found
        and "EC" in countries_found
        and sales_data.get("limit") == 50
    )
    report("4. Natural Language Brief Parser (Cross-Border Sales DO & EC)", sales_valid, f"Limit: {sales_data.get('limit')}, Countries: {list(countries_found)}")

    # --------------------------------------------------------------------------
    # TEST 5: WhatsApp Webhook Handshake & Incoming Message Processing
    # --------------------------------------------------------------------------
    # Handshake verification
    os.environ["WHATSAPP_VERIFY_TOKEN"] = "staging_wa_secret_123"
    res_wh_ver = client.get("/api/v1/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=staging_wa_secret_123&hub.challenge=challenge_token_999")
    ver_ok = res_wh_ver.status_code == 200 and res_wh_ver.text == "challenge_token_999"

    # Incoming message processing
    wa_msg = {
        "from": "+573001234567",
        "text": "Búscame 25 colegios bilingües en Medellín para venderles carnets escolares",
        "echo_responses": True
    }
    res_wh_post = client.post("/api/v1/webhooks/whatsapp", json=wa_msg)
    wh_post_data = res_wh_post.json() if res_wh_post.status_code == 200 else {}
    wh_ok = (
        res_wh_post.status_code == 200
        and wh_post_data.get("status") == "ok"
        and len(wh_post_data.get("responses", [])) > 0
    )
    report("5. WhatsApp Webhook Handshake & Intake Processing", ver_ok and wh_ok, f"Verification: OK, Intake Action: {wh_post_data.get('responses', [{}])[0].get('action')}")

    # --------------------------------------------------------------------------
    # TEST 6: Multi-Country Harvester Broadening Verification
    # --------------------------------------------------------------------------
    from src.adapters.registries.colombia.secop_harvester_adapter import SecopHarvesterAdapter
    from src.adapters.registries.dominican_republic.dgcp_dr_adapter import DgcpDrAdapter
    from src.adapters.registries.ecuador.sercop_ecuador_adapter import SercopEcuadorAdapter

    co_cand = SecopHarvesterAdapter(timeout=5).fetch_candidates(city="Medellín", limit=3, ciiu_codes=["8530"])
    do_cand = DgcpDrAdapter().fetch_candidates(city="Santo Domingo", limit=3, ciiu_codes=["8530"])
    ec_cand = SercopEcuadorAdapter().fetch_candidates(city="Quito", limit=3, ciiu_codes=["8530"])

    harv_ok = len(co_cand) > 0 and len(do_cand) > 0 and len(ec_cand) > 0
    report("6. Multi-Country Harvesters (CO 🇨🇴, DO 🇩🇴, EC 🇪🇨)", harv_ok, f"CO: {len(co_cand)}, DO: {len(do_cand)}, EC: {len(ec_cand)} candidates")

    # --------------------------------------------------------------------------
    # TEST 7: End-to-End Procurement Order Lifecycle & Deliverables
    # --------------------------------------------------------------------------
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_ledger = DeduplicationLedger(ledger_path=os.path.join(tmp_dir, "e2e_ledger.json"))
        use_case = GenerateProspectsUseCase(
            ledger=tmp_ledger,
            verify_mx_fn=lambda email: (True, "mail.example.com")
        )

        req = UniversalProspectingRequest(
            offer_description="Cotización urgente para reparación y tapicería de sillas de oficina",
            directionality=SearchDirectionality.CLIENT_TO_VENDORS,
            sectors=["furniture_manufacturing"],
            ciiu_codes=["3110", "9524"],
            locations=[LocationAllocation(country="CO", region="Antioquia", city="Medellín", allocated_leads=5)],
            rfq_specifications="Tapizado en paño de alto tráfico con entrega en 15 días calendario.",
            roles=["Gerente Comercial", "Director de Ventas"],
            tier=2
        )

        res_e2e = use_case.execute(universal_request=req, output_format="all")
        leads = res_e2e.get("leads", [])
        e2e_ok = (
            res_e2e.get("status") == "success"
            and len(leads) >= 3
            and all(bool(lead.get("email") and lead.get("mx_host") and lead.get("decision_maker_name")) for lead in leads)
        )
        report("7. End-to-End Procurement Lifecycle (Auto-RFQ Roster)", e2e_ok, f"Verified Leads: {len(leads)}/5 target")

    # --------------------------------------------------------------------------
    # TEST 8: Web Client Build & Asset Integrity
    # --------------------------------------------------------------------------
    dist_index = REPO_ROOT / "clients" / "web" / "dist" / "index.html"
    dist_assets = list((REPO_ROOT / "clients" / "web" / "dist" / "assets").glob("*.js"))
    web_ok = dist_index.exists() and len(dist_assets) > 0
    report("8. Web Client Distribution Assets", web_ok, f"Found index.html and {len(dist_assets)} bundled JS chunks")

    # --------------------------------------------------------------------------
    # Summary
    # --------------------------------------------------------------------------
    print(f"\n{BOLD}--------------------------------------------------------------------{RESET}")
    print(f"{BOLD}TEST RESULTS: {passed_tests} PASSED, {failed_tests} FAILED (Total: {passed_tests + failed_tests}){RESET}")
    print(f"{BOLD}--------------------------------------------------------------------{RESET}\n")

    if failed_tests > 0:
        sys.exit(1)
    else:
        print(f"{GREEN}{BOLD}✓ ALL LOCAL SYSTEMS VERIFIED & OPERATIONAL!{RESET}\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
