#!/usr/bin/env python3
"""
==============================================================================
Michito B2B Engine — End-to-End (E2E) Chaos & Resilience Drill
==============================================================================
Simulates real-world production outages and failures against running services:
  • Live PostgreSQL 16 on 127.0.0.1:5432
  • Live Firebase Storage Emulator on 127.0.0.1:9199
  • Live Outbound Wire HTTP Webhook Receiver on 127.0.0.1:8999

Scenarios Executed:
  1. Zombie Order Self-Healing (Worker Crash Recovery)
  2. Retry Budget Exhaustion & Dead-Letter Queue (DLQ)
  3. Real Wire-Level Alert Dispatch (Slack Webhook Format over TCP)
  4. Worker Pipeline Exception Isolation (Daemon Never Dies)
  5. Concurrency Race Condition Protection (PostgreSQL SKIP LOCKED)
  6. Live Deliverable Upload to Storage Emulator & HTTP Download
==============================================================================
"""

import sys
import os
import time
import json
import socket
from datetime import datetime, timezone, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import urllib.request

# Ensure backend root is on PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import src.config  # Loads .env.local (DATABASE_URL, STORAGE_EMULATOR_HOST, etc.)

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session
from src.adapters.db.models import Base, OrderModel
from src.adapters.db.sql_order_adapter import SqlOrderAdapter
from src.adapters.alerts.webhook_alert_adapter import WebhookAlertAdapter
from src.adapters.storage.gcs_storage_adapter import GcsStorageAdapter
from src.entrypoints.workers.order_worker_daemon import OrderWorkerDaemon

# Colors for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

RECEIVED_ALERTS = []

class MockWebhookHandler(BaseHTTPRequestHandler):
    """Real HTTP server that records incoming webhook calls over TCP."""
    def do_POST(self):
        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len).decode("utf-8")
        parsed = {}
        try:
            parsed = json.loads(body)
        except Exception:
            parsed = {"raw": body}

        RECEIVED_ALERTS.append({
            "path": self.path,
            "headers": dict(self.headers),
            "payload": parsed
        })

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status": "ok", "delivered": true}')

    def log_message(self, format, *args):
        # Silence default HTTP server console logging
        return


def start_mock_webhook_server(port=8999):
    """Spins up a lightweight HTTP server in a background thread."""
    server = HTTPServer(("127.0.0.1", port), MockWebhookHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def print_header(title):
    print(f"\n{BOLD}{CYAN}════════════════════════════════════════════════════════════════════════════════{RESET}")
    print(f"{BOLD}{CYAN}▶ {title}{RESET}")
    print(f"{BOLD}{CYAN}════════════════════════════════════════════════════════════════════════════════{RESET}")


def run_drill():
    print(f"\n{BOLD}{YELLOW}🚀 STARTING MICHITO PRODUCTION CHAOS DRILL{RESET}")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")

    db_url = "postgresql+psycopg://127.0.0.1:5432/michito"
    webhook_port = 8999
    webhook_url = f"http://127.0.0.1:{webhook_port}/slack.com/services/T000/B000/X000"

    # Start live HTTP webhook server
    print(f"[*] Starting live wire-level Webhook listener on port {webhook_port}...")
    server = start_mock_webhook_server(webhook_port)
    time.sleep(0.3)

    # Initialize live SQL adapter against PostgreSQL
    print(f"[*] Connecting to PostgreSQL on 127.0.0.1:5432...")
    adapter = SqlOrderAdapter(database_url=db_url)
    engine = adapter.engine

    # --------------------------------------------------------------------------
    # SCENARIO 1: Live Zombie Order Self-Healing & Progressive Retry
    # --------------------------------------------------------------------------
    print_header("SCENARIO 1: Zombie Order Self-Healing (Worker Crash Recovery)")
    test_order_1 = adapter.create_order(
        client_name="Chaos Corp 1",
        client_email="chaos1@chiketto.com",
        campaign_id="tinkko_enterprise_offices",
        limit=5,
        city="Medellín"
    )
    o1_id = test_order_1["order_id"]
    print(f"  • Created test order `{o1_id}` in PostgreSQL.")

    # Simulate worker crash mid-flight: set status to 'processing' with timestamp 10m ago
    now = datetime.now(timezone.utc)
    ten_min_ago = now - timedelta(minutes=10)
    with adapter._get_session() as session:
        ord_obj = session.get(OrderModel, o1_id)
        assert ord_obj is not None
        ord_obj.status = "processing"
        ord_obj.started_processing_at = ten_min_ago
        ord_obj.retry_count = 0
        ord_obj.max_retries = 3
        session.commit()
    print(f"  • Injected crash: Order marked as 'processing' with started_processing_at = 10 mins ago.")

    # Trigger live recovery sweeper
    reaper_results = adapter.recover_stuck_processing_orders(max_processing_minutes=5)
    
    # Query order from DB to verify physical update
    recovered = adapter.get_order(o1_id)
    assert recovered is not None
    assert recovered["status"] == "queued", f"Expected queued, got {recovered['status']}"
    assert recovered["retry_count"] == 1, f"Expected retry_count=1, got {recovered['retry_count']}"
    print(f"  • Sweeper result: Order successfully reverted to '{recovered['status']}' with retry_count = {recovered['retry_count']}.")
    print(f"{BOLD}{GREEN}  ✅ SCENARIO 1 PASSED: Self-healing successfully recovered stuck order.{RESET}")

    # --------------------------------------------------------------------------
    # SCENARIO 2: Retry Budget Exhaustion & Dead-Letter Queue (DLQ)
    # --------------------------------------------------------------------------
    print_header("SCENARIO 2: Retry Budget Exhaustion & Dead-Letter Queue (DLQ)")
    with adapter._get_session() as session:
        ord_obj = session.get(OrderModel, o1_id)
        assert ord_obj is not None
        ord_obj.status = "processing"
        ord_obj.started_processing_at = ten_min_ago
        ord_obj.retry_count = 3  # Exhausted retries
        session.commit()
    print(f"  • Injected retry exhaustion: Order marked with retry_count = 3 / max_retries = 3.")

    dead_lettered = adapter.recover_stuck_processing_orders(max_processing_minutes=5)
    dead_ids = [d["order_id"] for d in dead_lettered]
    assert o1_id in dead_ids, f"Order {o1_id} was not returned in dead_lettered list"

    dead_record = adapter.get_order(o1_id)
    assert dead_record is not None
    assert dead_record["status"] == "failed"
    assert "dead-lettered" in dead_record.get("error_message", "").lower()
    print(f"  • Database status: '{dead_record['status']}'")
    print(f"  • Error diagnostic: {dead_record.get('error_message')}")
    print(f"{BOLD}{GREEN}  ✅ SCENARIO 2 PASSED: Order permanently moved to Dead-Letter Queue upon retry exhaustion.{RESET}")

    # --------------------------------------------------------------------------
    # SCENARIO 3: Live Wire Outbound Alerting (Slack Webhook Format over TCP)
    # --------------------------------------------------------------------------
    print_header("SCENARIO 3: Live Wire Outbound Alerting (Slack Webhook Format over TCP)")
    alert_adapter = WebhookAlertAdapter(webhook_url=webhook_url)
    
    # Send live alert for the dead-lettered order
    send_ok = alert_adapter.send_alert(
        title="Order Dead-Lettered (Chaos Test)",
        message=f"Order `{o1_id}` failed after 3 retry attempts.",
        level="critical",
        details={
            "order_id": o1_id,
            "client_email": "chaos1@chiketto.com",
            "retry_count": 3,
            "error": "SECOP API persistent 504 Gateway Timeout",
        }
    )
    assert send_ok, "Alert adapter failed to transmit HTTP request"

    time.sleep(0.3)
    assert len(RECEIVED_ALERTS) > 0, "Mock webhook server received 0 requests!"
    last_alert = RECEIVED_ALERTS[-1]
    
    # Validate Slack formatting
    payload = last_alert["payload"]
    assert "text" in payload, f"Expected Slack 'text' field, got: {payload}"
    assert "🚨 *[CRITICAL] Order Dead-Lettered" in payload["text"]
    assert o1_id in payload["text"]
    print(f"  • Real HTTP POST received on {last_alert['path']}")
    print(f"  • Content-Type: {last_alert['headers'].get('Content-Type')}")
    print(f"  • Transmitted Slack text snippet:\n    {payload['text'][:120]}...")
    print(f"{BOLD}{GREEN}  ✅ SCENARIO 3 PASSED: Alert transmitted over real network socket with verified Slack formatting.{RESET}")

    # --------------------------------------------------------------------------
    # SCENARIO 4: Worker Pipeline Exception Isolation (Daemon Never Dies)
    # --------------------------------------------------------------------------
    print_header("SCENARIO 4: Worker Pipeline Exception Isolation")
    test_order_2 = adapter.create_order(
        client_name="Crash Test Lead",
        client_email="crashtest@chiketto.com",
        campaign_id="tinkko_enterprise_offices",
        limit=10,
        city="Bogotá"
    )
    o2_id = test_order_2["order_id"]

    # Mock a use case that raises a severe unhandled crash
    class ExplodingUseCase:
        def execute(self, *args, **kwargs):
            raise ConnectionResetError("Fatal Remote Chamber Registry Connection Abort!")

    daemon = OrderWorkerDaemon(
        order_repository=adapter,
        order_queue=None,
        use_case=ExplodingUseCase(),
        storage_adapter=GcsStorageAdapter(),
        alert_dispatcher=alert_adapter
    )

    initial_alert_count = len(RECEIVED_ALERTS)
    success = daemon.process_order(test_order_2)
    assert not success, "Daemon should return False when pipeline raises error"

    # Verify order recorded the failure in DB
    failed_ord = adapter.get_order(o2_id)
    assert failed_ord is not None
    assert failed_ord["retry_count"] == 1
    assert failed_ord["status"] == "queued"  # Auto-requeued for retry
    print(f"  • Daemon caught crash: Order updated to status='{failed_ord['status']}', retry_count={failed_ord['retry_count']}.")
    print(f"{BOLD}{GREEN}  ✅ SCENARIO 4 PASSED: Pipeline crashes caught gracefully; state persisted safely.{RESET}")

    # --------------------------------------------------------------------------
    # SCENARIO 5: PostgreSQL Row-Level Concurrency Protection (SKIP LOCKED)
    # --------------------------------------------------------------------------
    print_header("SCENARIO 5: Concurrency Race Condition Protection (SKIP LOCKED)")
    # Worker 1 grabs queued orders with lock inside an open transaction
    session1 = Session(engine)
    session2 = Session(engine)

    try:
        # Worker 1 locks pending orders
        stmt1 = select(OrderModel).where(OrderModel.status == "queued").order_by(OrderModel.created_at.asc()).limit(1).with_for_update(skip_locked=True)
        w1_orders = session1.scalars(stmt1).all()
        assert len(w1_orders) > 0, "Expected at least 1 queued order"
        locked_order_id = w1_orders[0].order_id
        print(f"  • Worker 1 locked order: `{locked_order_id}` (Transaction uncommitted).")

        # Worker 2 attempts to fetch queued orders simultaneously
        stmt2 = select(OrderModel).where(OrderModel.status == "queued").order_by(OrderModel.created_at.asc()).limit(1).with_for_update(skip_locked=True)
        w2_orders = session2.scalars(stmt2).all()
        w2_ids = [o.order_id for o in w2_orders]
        assert locked_order_id not in w2_ids, f"Race condition! Worker 2 fetched already locked order {locked_order_id}"
        print(f"  • Worker 2 query result: Locked order `{locked_order_id}` was skipped! (No double processing).")
        print(f"{BOLD}{GREEN}  ✅ SCENARIO 5 PASSED: PostgreSQL SKIP LOCKED prevents concurrent worker race conditions.{RESET}")
    finally:
        session1.rollback()
        session2.rollback()
        session1.close()
        session2.close()

    # --------------------------------------------------------------------------
    # SCENARIO 6: Live Deliverable Upload to Storage Emulator & HTTP Download
    # --------------------------------------------------------------------------
    print_header("SCENARIO 6: Live Deliverable Upload to Storage Emulator (Port 9199)")
    storage = GcsStorageAdapter()
    
    # Create temporary payload files
    temp_dir = "/tmp/michito_chaos_test"
    os.makedirs(temp_dir, exist_ok=True)
    temp_csv = os.path.join(temp_dir, "test_leads.csv")
    with open(temp_csv, "w") as f:
        f.write("company_name,nit,email,phone\nInversiones Chaos SAS,901.999.888,ceo@chaos.com,+573001234567\n")

    dest_blob = f"orders/ord_chaos_live_verify/prospects.csv"
    print(f"  • Uploading {temp_csv} to gs://michito-deliverables/{dest_blob}...")
    uploaded_uri = storage.upload_file(temp_csv, dest_blob, content_type="text/csv")
    assert uploaded_uri.startswith("gs://"), f"Unexpected URI: {uploaded_uri}"
    print(f"  • Successfully uploaded: {uploaded_uri}")

    download_url = storage.generate_download_url(dest_blob, expiration_hours=48)
    print(f"  • Generated signed/emulator download URL: {download_url}")

    # Perform real HTTP GET against port 9199
    req = urllib.request.Request(download_url)
    with urllib.request.urlopen(req, timeout=5) as response:
        assert response.status == 200, f"Expected 200, got {response.status}"
        body = response.read().decode("utf-8")
        assert "Inversiones Chaos SAS" in body
        print(f"  • HTTP GET on port 9199 returned 200 OK ({len(body)} bytes read).")
        print(f"{BOLD}{GREEN}  ✅ SCENARIO 6 PASSED: Deliverable verified live in Storage Emulator.{RESET}")

    # --------------------------------------------------------------------------
    # FINAL SUMMARY
    # --------------------------------------------------------------------------
    print(f"\n{BOLD}{GREEN}════════════════════════════════════════════════════════════════════════════════{RESET}")
    print(f"{BOLD}{GREEN}🎉 ALL 6 CHAOS DRILL SCENARIOS PASSED WITH ZERO FAILURES!{RESET}")
    print(f"{BOLD}{GREEN}════════════════════════════════════════════════════════════════════════════════{RESET}")
    print(f"Total alerts captured on real wire socket: {len(RECEIVED_ALERTS)}")
    print(f"PostgreSQL ACID locking verified: True")
    print(f"Storage Emulator upload & download verified: True")
    print(f"Self-Healing Zombie Reaper verified: True\n")

if __name__ == "__main__":
    run_drill()
