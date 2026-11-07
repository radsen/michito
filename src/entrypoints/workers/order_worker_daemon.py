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
        use_case: Optional[GenerateProspectsUseCase] = None,
        storage_adapter: Optional[StoragePort] = None,
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
        elif os.environ.get("GCS_BUCKET_NAME") or os.environ.get("ENVIRONMENT") == "production":
            from src.adapters.storage.gcs_storage_adapter import GcsStorageAdapter
            self.storage_adapter = GcsStorageAdapter()
        else:
            from src.adapters.storage.local_storage_adapter import LocalStorageAdapter
            self.storage_adapter = LocalStorageAdapter()

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

        print(f"\n[WorkerDaemon] ⚡ Locking and starting processing for Order `{order_id}`...")
        print(f"               Client:   {client_name}")
        print(f"               Campaign: {campaign_id} | City: {city} | Limit: {limit} | Tier: {tier}")

        # 1. Lock the order in the repository to prevent double processing
        if not self.order_repository.mark_processing(order_id):
            print(f"[WorkerDaemon] ⚠️ Order `{order_id}` could not be locked (already picked up by another worker).")
            return False

        # 2. Execute the heavy harvesting, verification, and intent pipeline
        try:
            t0 = time.time()
            job_result = self.use_case.execute(
                campaign=campaign_id,
                city=city,
                limit=limit,
                segment=segment,
                tier=tier,
                dry_run=False,
                output_format="both",
            )
            elapsed = time.time() - t0

            # Fair Pay-Per-Lead Tiered Pricing (Strategy Financial Model)
            total_qualified = job_result.get("total_qualified", len(job_result.get("leads", [])))
            country = req.get("country", "CO")
            currency = job_result.get("currency", "DOP" if country == "DO" else "COP")

            total_price_cents = calculate_lead_pricing(
                total_qualified=total_qualified,
                tier=tier,
                currency=currency
            )

            # Upload deliverables to Storage Adapter (Local or GCS)
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
            print(f"[WorkerDaemon] ✅ Order `{order_id}` completed successfully in {elapsed:.2f}s!")
            print(f"               Qualified Leads: {job_result.get('total_qualified', 0)}")
            print(f"               Status: awaiting_payment (Quote: ${total_price_cents // 100:,.0f} COP)")
            return True

        except Exception as e:
            print(f"[WorkerDaemon] ❌ Error processing Order `{order_id}`: {e}")
            if hasattr(self.order_repository, "mark_failed"):
                self.order_repository.mark_failed(order_id, str(e))
            elif getattr(self.order_repository, "db", None):
                self.order_repository.db.collection("orders").document(order_id).update({
                    "status": "failed",
                    "error_message": str(e),
                    "failed_at": time.time(),
                })
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

        try:
            while True:
                # 1. Check Queue if available
                if self.order_queue:
                    def _queue_handler(payload: Dict[str, Any]) -> bool:
                        order_id = payload.get("order_id")
                        order = self.order_repository.get_order(order_id) or payload
                        return self.process_order(order)

                    self.order_queue.listen_orders(
                        handler=_queue_handler,
                        max_messages=1 if run_once else 10
                    )
                    if run_once:
                        break
                    time.sleep(poll_interval_sec)
                    continue

                # 2. Fallback to direct repository query
                queued_orders = self.order_repository.fetch_queued_orders(limit=5)
                if queued_orders:
                    print(f"[WorkerDaemon] Found {len(queued_orders)} queued order(s) waiting for processing.")
                    for ord_doc in queued_orders:
                        self.process_order(ord_doc)

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
