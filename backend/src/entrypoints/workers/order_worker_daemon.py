"""
Michito Asynchronous Order Processing Worker Daemon.
Clean Architecture Entrypoint for processing incoming prospecting orders.
Supports queue-driven decoupled intake (e.g., in-memory queue, Google Cloud Pub/Sub)
as well as direct repository polling (Firestore).
"""

import os
import sys
import time
from typing import Dict, Any, Optional

from src.adapters.db.firestore_order_adapter import FirestoreOrderAdapter
from src.application.ports.order_queue_port import OrderQueuePort
from src.application.ports.storage_port import StoragePort
from src.application.use_cases.generate_prospects_use_case import GenerateProspectsUseCase, run_prospecting_job


def calculate_lead_pricing(total_qualified: int, tier: int = 2, currency: str = "COP") -> int:
    """
    Calculates fair, tiered batch pricing in cents according to the Michito Financial Model
    (docs/strategy/financial_model_unit_economics.md) with statutory volume discount curves.
    """
    if total_qualified <= 0:
        return 0

    if currency.upper() == "DOP":
        base_rates = {1: 10000, 2: 35000, 3: 75000}  # 100, 350, 750 DOP in cents
    else:
        base_rates = {1: 500000, 2: 3000000, 3: 6500000}  # $5.000, $30.000, $65.000 COP in cents

    unit_base = base_rates.get(tier, base_rates[2])

    # Volume discount curve
    if total_qualified >= 1000:
        discount = 0.42
    elif total_qualified >= 500:
        discount = 0.35
    elif total_qualified >= 250:
        discount = 0.28
    elif total_qualified >= 100:
        discount = 0.20
    elif total_qualified >= 50:
        discount = 0.12
    elif total_qualified >= 25:
        discount = 0.06
    else:
        discount = 0.0

    discounted_unit = int(unit_base * (1.0 - discount))
    return total_qualified * discounted_unit


class OrderWorkerDaemon:
    """
    Decoupled Worker Daemon that monitors incoming orders, locks them, executes
    the heavy harvesting and intent pipeline, calculates the quote, and transitions
    the order state to 'awaiting_payment'.
    """

    def __init__(
        self,
        order_repository: Optional[Any] = None,
        order_queue: Optional[OrderQueuePort] = None,
        use_case: Optional[Any] = None,
        storage_adapter: Optional[StoragePort] = None,
        alert_dispatcher: Optional[Any] = None,
    ):
        if order_repository:
            self.order_repository = order_repository
        elif os.environ.get("DATABASE_URL") or not os.environ.get("FIRESTORE_EMULATOR_HOST"):
            from src.adapters.db.sql_order_adapter import SqlOrderAdapter
            self.order_repository = SqlOrderAdapter()
        else:
            self.order_repository = FirestoreOrderAdapter()

        self.order_queue = order_queue
        self.use_case = use_case or GenerateProspectsUseCase()

        if storage_adapter:
            self.storage_adapter = storage_adapter
        elif os.environ.get("STORAGE_EMULATOR_HOST") or os.environ.get("GCS_BUCKET_NAME") or os.environ.get("ENVIRONMENT") == "production":
            from src.adapters.storage.gcs_storage_adapter import GcsStorageAdapter
            self.storage_adapter = GcsStorageAdapter()
        else:
            from src.adapters.storage.local_storage_adapter import LocalStorageAdapter
            self.storage_adapter = LocalStorageAdapter()

        if alert_dispatcher:
            self.alert_dispatcher = alert_dispatcher
        else:
            from src.adapters.alerts.webhook_alert_adapter import WebhookAlertAdapter
            self.alert_dispatcher = WebhookAlertAdapter()

    def process_order(self, order: Dict[str, Any]) -> bool:
        order_id = order.get("order_id")
        if not order_id:
            print("[WorkerDaemon] ⚠️ Invalid order object received: missing order_id.")
            return False

        client_name = order.get("client", {}).get("name", "Unknown Client")
        req = order.get("request", {})
        campaign_id = req.get("campaign_id", "tinkko_enterprise_offices")
        city = req.get("city", "Medellín")
        limit = req.get("limit", 10)
        segment = req.get("segment")
        tier = req.get("tier", 2)
        exclusions = req.get("exclusions") or req.get("keywords_exclude")

        print(f"\n[WorkerDaemon] ⚡ Locking and starting processing for Order `{order_id}`...")
        print(f"               Client:   {client_name}")
        print(f"               Campaign: {campaign_id} | City: {city} | Limit: {limit} | Tier: {tier}")
        if exclusions:
            print(f"               Exclusions: {len(exclusions)} accounts or domains blacklisted.")
        print(f"[WorkerDaemon] ⏳ [1/4] Ingestion & Chamber of Commerce Harvester running...")

        # 1. Lock the order in the repository to prevent double processing
        if not self.order_repository.mark_processing(order_id):
            print(f"[WorkerDaemon] ⚠️ Order `{order_id}` could not be locked (already picked up by another worker).")
            return False

        # 2. Execute the heavy harvesting, verification, and intent pipeline
        try:
            print(f"[WorkerDaemon] 🔍 [2/4] Verifying domains, HTTP footprint & Socket MX servers...")
            print(f"[WorkerDaemon] 🛡️ [3/4] Underwriting solvency risk & composing 5 tailored multichannel touches...")
            t0 = time.time()
            exec_kwargs: Dict[str, Any] = {
                "campaign": campaign_id,
                "city": city,
                "limit": limit,
                "segment": segment,
                "tier": tier,
                "dry_run": False,
                "output_format": "both",
            }
            if exclusions:
                exec_kwargs["exclusions"] = exclusions

            job_result = self.use_case.execute(**exec_kwargs)
            elapsed = time.time() - t0

            # Fair Pay-Per-Lead Tiered Pricing (Strategy Financial Model)
            total_qualified = job_result.get("total_qualified", len(job_result.get("leads", [])))
            if total_qualified == 0:
                err_msg = job_result.get("message") or "No se encontraron prospectos que superaran los filtros de calidad o el registro mercantil estuvo inaccesible."
                print(f"[WorkerDaemon] ⚠️ Order `{order_id}` produced 0 qualified leads. Marking failed.")
                if hasattr(self.order_repository, "mark_failed"):
                    self.order_repository.mark_failed(order_id, err_msg)
                return False

            country = req.get("country", "CO")
            currency = job_result.get("currency", "DOP" if country == "DO" else "COP")

            total_price_cents = calculate_lead_pricing(
                total_qualified=total_qualified,
                tier=tier,
                currency=currency
            )

            # Upload deliverables to Storage Adapter (Local or GCS)
            print(f"[WorkerDaemon] 📦 [4/4] Packaging structured CSV manifest and executive dossier...")
            csv_path = job_result.get("csv_path")
            dossier_path = job_result.get("dossier_path")

            if csv_path and os.path.exists(csv_path):
                dest_csv = f"orders/{order_id}/prospects.csv"
                csv_uri = self.storage_adapter.upload_file(csv_path, dest_csv, content_type="text/csv")
                csv_url = self.storage_adapter.generate_download_url(dest_csv, expiration_hours=48)
                job_result["csv_uri"] = csv_uri
                job_result["csv_download_url"] = csv_url
                print(f"[WorkerDaemon] 📦 CSV Stored: {csv_uri}")

            if dossier_path and os.path.exists(dossier_path):
                dest_dossier = f"orders/{order_id}/executive_dossier.md"
                dossier_uri = self.storage_adapter.upload_file(dossier_path, dest_dossier, content_type="text/markdown")
                dossier_url = self.storage_adapter.generate_download_url(dest_dossier, expiration_hours=48)
                job_result["dossier_uri"] = dossier_uri
                job_result["dossier_download_url"] = dossier_url
                print(f"[WorkerDaemon] 📄 Dossier Stored: {dossier_uri}")

            self.order_repository.complete_order(
                order_id=order_id,
                job_result=job_result,
                amount_in_cents=total_price_cents
            )

            if hasattr(self.alert_dispatcher, "send_feed_event"):
                self.alert_dispatcher.send_feed_event(
                    title="Leads Ready & Awaiting Payment 🎯",
                    message=f"Order `{order_id}` finished processing in {elapsed:.1f}s. {job_result.get('total_qualified', 0)} qualified leads generated.",
                    details={
                        "order_id": order_id,
                        "client": client_name,
                        "campaign": campaign_id,
                        "city": city,
                        "qualified_leads": job_result.get("total_qualified", 0),
                        "total_quote": f"${total_price_cents // 100:,.0f} COP",
                    }
                )

            print(f"[WorkerDaemon] ✅ Order `{order_id}` completed successfully in {elapsed:.2f}s!")
            print(f"               Qualified Leads: {job_result.get('total_qualified', 0)}")
            print(f"               Status: awaiting_payment (Quote: ${total_price_cents // 100:,.0f} COP)")
            print(f"               Ready for buyer review and Wompi unlock.\n")
            return True

        except Exception as e:
            print(f"[WorkerDaemon] ❌ Error processing Order `{order_id}`: {e}")
            failure_info = None
            if hasattr(self.order_repository, "record_order_failure"):
                failure_info = self.order_repository.record_order_failure(order_id, str(e))
            elif hasattr(self.order_repository, "mark_failed"):
                self.order_repository.mark_failed(order_id, str(e))
            elif getattr(self.order_repository, "db", None):
                self.order_repository.db.collection("orders").document(order_id).update({
                    "status": "failed",
                    "error_message": str(e),
                    "failed_at": time.time(),
                })

            # If dead-lettered after max retries, dispatch operator alert immediately
            if not failure_info or failure_info.get("status") == "dead-lettered":
                self.alert_dispatcher.send_alert(
                    title="Order Dead-Lettered (Execution Failure)",
                    message=f"Order `{order_id}` failed unrecoverably: {e}",
                    level="error",
                    details={
                        "order_id": order_id,
                        "client_email": order.get("client", {}).get("email"),
                        "retry_count": failure_info.get("order", {}).get("retry_count") if failure_info else "N/A",
                        "error": str(e),
                    },
                )
            return False

    def run_loop(self, poll_interval_sec: int = 5, run_once: bool = False):
        print("=" * 80)
        print("⚙️  MICHITO ASYNCHRONOUS ORDER WORKER DAEMON STARTED")
        print("=" * 80)
        mode_str = getattr(self.order_repository, "database_url", type(self.order_repository).__name__)
        queue_str = type(self.order_queue).__name__ if self.order_queue else "Direct Queue / Polling"
        print(f"• Database Engine:     {mode_str}")
        print(f"• Intake Queue Mode:   {queue_str}")
        print(f"• Polling Interval:    {poll_interval_sec}s")
        print(f"• Mode:                {'Run-Once (Batch)' if run_once else 'Continuous Listener'}")
        print("=" * 80)

        loop_count = 0
        try:
            while True:
                loop_count += 1

                # 0. Zombie Order Reaper & Timeout Sweeper (Self-Healing every ~30s)
                if loop_count % 6 == 1 and hasattr(self.order_repository, "recover_stuck_processing_orders"):
                    dead_lettered = self.order_repository.recover_stuck_processing_orders(max_processing_minutes=5)
                    for dead in dead_lettered:
                        print(f"[WorkerDaemon] 🚨 Order `{dead['order_id']}` Dead-Lettered by Timeout Reaper!")
                        self.alert_dispatcher.send_alert(
                            title="Order Dead-Lettered (Timeout Recovery)",
                            message=f"Order `{dead['order_id']}` was stuck in 'processing' longer than 5 minutes and exceeded max retries.",
                            level="critical",
                            details={
                                "order_id": dead.get("order_id"),
                                "client_email": dead.get("client", {}).get("email"),
                                "retry_count": dead.get("retry_count"),
                                "error": dead.get("error_message"),
                            },
                        )
                # 1. Check Queue if available (Pub/Sub)
                queue_processed = False
                if self.order_queue:
                    def _queue_handler(payload: Dict[str, Any]) -> bool:
                        nonlocal queue_processed
                        order_id = payload.get("order_id")
                        fetched = self.order_repository.get_order(str(order_id)) if order_id else None
                        order = fetched or payload
                        if not order:
                            return False
                        res = self.process_order(order)
                        if res is not False:
                            queue_processed = True
                        return res

                    try:
                        self.order_queue.listen_orders(
                            handler=_queue_handler,
                            max_messages=1 if run_once else 10
                        )
                    except Exception as e:
                        pass

                    if queue_processed:
                        if run_once:
                            break
                        time.sleep(poll_interval_sec)
                        continue

                # 2. Check repository directly (Dual-Intake safety net)
                # Guarantees that even if Pub/Sub drops or delays a message, no order gets stuck
                queued_orders = self.order_repository.fetch_queued_orders(limit=5)
                if queued_orders:
                    print(f"[WorkerDaemon] ⚡ Found {len(queued_orders)} queued order(s) waiting in database. Processing now...")
                    for ord_doc in queued_orders:
                        self.process_order(ord_doc)
                else:
                    if loop_count % 4 == 1 and not run_once:
                        now_str = time.strftime("%H:%M:%S")
                        print(f"[{now_str}] 🟢 [WorkerDaemon] Heartbeat: Daemon healthy • Polling {mode_str} (Interval: {poll_interval_sec}s)...")

                if run_once:
                    print("[WorkerDaemon] Run-once flag active. Exiting worker process.")
                    break

                time.sleep(poll_interval_sec)

        except KeyboardInterrupt:
            print("\n[WorkerDaemon] Shutting down worker gracefully. Goodbye!")


# Legacy helper function matching original order_worker.py signature
def process_single_order(adapter: FirestoreOrderAdapter, order: Dict[str, Any]) -> bool:
    daemon = OrderWorkerDaemon(order_repository=adapter)
    return daemon.process_order(order)
