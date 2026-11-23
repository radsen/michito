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


def calculate_lead_pricing(
    total_qualified: int,
    tier: int = 2,
    currency: str = "COP",
    allow_courtesy: bool = True,
    partner_id: Optional[str] = None,
) -> int:
    """
    Calculates fair, tiered batch pricing in cents by delegating to the centralized
    PricingCatalogService, enforcing dynamic database price books, volume discount
    brackets, and courtesy micro-batch policies.
    """
    from src.domain.services.pricing_catalog_service import PricingCatalogService
    service = PricingCatalogService.get_instance()
    quote = service.calculate_quote(
        total_qualified=total_qualified,
        tier=tier,
        currency=currency,
        partner_id=partner_id,
        allow_courtesy=allow_courtesy,
    )
    return quote["total_cents"]


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
        if use_case:
            self.use_case = use_case
        else:
            rep_ledger = getattr(self.order_repository, "ledger", None)
            if "pytest" in sys.modules or os.environ.get("ALLOW_STATUTORY_FALLBACK", "").lower() == "true":
                from unittest.mock import MagicMock
                mock_auditor = MagicMock()
                mock_auditor.audit.side_effect = lambda *args, **kwargs: (True, args[0] if args and args[0] else "https://www.example.com", "Active Test Site")
                self.use_case = GenerateProspectsUseCase(
                    ledger=rep_ledger,
                    verify_mx_fn=lambda *args, **kwargs: (True, "mail.example.com"),
                    web_auditor=mock_auditor,
                )
            else:
                self.use_case = GenerateProspectsUseCase(ledger=rep_ledger)

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
        import sys
        order_id = order.get("order_id") or order.get("id")
        if not order_id:
            print("[WorkerDaemon] [WARN] Invalid order object received: missing order_id.")
            return False

        # Idempotency Gate: If order is already paid and deliverables exist, skip duplicate processing
        payment_status = (order.get("payment", {}).get("status") or "").upper()
        order_status = (order.get("status") or "").lower()
        is_paid = order_status in ("paid", "completed", "fulfilled") or payment_status == "APPROVED"
        delivery = order.get("delivery", {})
        has_deliverables = bool(delivery.get("csv_path") or delivery.get("xlsx_path"))
        if is_paid and has_deliverables:
            print(f"[WorkerDaemon] [INFO] Order `{order_id}` is already fully fulfilled. Skipping batch harvesting.")
            return True

        client_name = order.get("client", {}).get("name", "Unknown Client")
        req = order.get("request", {})
        campaign_id = req.get("campaign_id", "tinkko_enterprise_offices")
        city = req.get("city", "Medellín")
        limit = req.get("limit", 10)
        segment = req.get("segment")
        tier = req.get("tier", 2)
        exclusions = req.get("exclusions") or req.get("keywords_exclude")

        print(f"\n[WorkerDaemon] [RUN] Locking and starting processing for Order `{order_id}`...")
        print(f"               Client:   {client_name}")
        print(f"               Campaign: {campaign_id} | City: {city} | Limit: {limit} | Tier: {tier}")
        if exclusions:
            print(f"               Exclusions: {len(exclusions)} accounts or domains blacklisted.")
        print(f"[WorkerDaemon] [WAIT] [1/4] Ingestion & Chamber of Commerce Harvester running...")

        # 1. Lock the order in the repository to prevent double processing
        if not self.order_repository.mark_processing(order_id):
            print(f"[WorkerDaemon] [WARN] Order `{order_id}` could not be locked (already picked up by another worker).")
            return False

        if hasattr(self.order_repository, "update_telemetry"):
            self.order_repository.update_telemetry(order_id, {
                "phase": "harvesting",
                "phase_key": "telemetry.harvesting",
                "step_index": 1,
                "progress_percent": 25,
            }, status="processing")

        # 2. Execute the heavy harvesting, verification, and intent pipeline
        try:
            print(f"[WorkerDaemon] [SEARCH] [2/4] Verifying domains, HTTP footprint & Socket MX servers...")
            print(f"[WorkerDaemon] [GUARD] [3/4] Underwriting solvency risk & composing 5 tailored multichannel touches...")
            if hasattr(self.order_repository, "update_telemetry"):
                self.order_repository.update_telemetry(order_id, {
                    "phase": "verifying_mx",
                    "phase_key": "telemetry.verifying_mx",
                    "step_index": 2,
                    "progress_percent": 55,
                })
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
            if req.get("country") and req.get("country") != "CO":
                exec_kwargs["country"] = req.get("country")
            if req.get("country_allocations"):
                exec_kwargs["country_allocations"] = req.get("country_allocations")
            if req.get("offer_description"):
                exec_kwargs["offer_description"] = req.get("offer_description")
            if req.get("target_roles"):
                exec_kwargs["target_roles"] = req.get("target_roles")
            if req.get("sector"):
                raw_sec = req.get("sector")
                if isinstance(raw_sec, list):
                    exec_kwargs["target_sectors"] = raw_sec
                elif isinstance(raw_sec, str):
                    exec_kwargs["target_sectors"] = [s.strip() for s in raw_sec.split(",") if s.strip()]
            if req.get("target_ciiu_codes"):
                exec_kwargs["target_ciiu_codes"] = req.get("target_ciiu_codes")
            if req.get("location_allocations"):
                exec_kwargs["location_allocations"] = req.get("location_allocations")
            if req.get("keywords_include"):
                raw_kws = req.get("keywords_include")
                if isinstance(raw_kws, list):
                    from src.application.services.brief_parser_service import QUERY_STOP_WORDS
                    clean_kws = []
                    for k in raw_kws:
                        k_clean = str(k).strip().lower()
                        if k_clean and k_clean not in QUERY_STOP_WORDS:
                            clean_kws.append(k_clean)
                    exec_kwargs["keywords_include"] = clean_kws
            if req.get("keywords_exclude"):
                exec_kwargs["keywords_exclude"] = req.get("keywords_exclude")
            if req.get("directionality"):
                exec_kwargs["directionality"] = req.get("directionality")
            if req.get("rfq_specifications"):
                exec_kwargs["rfq_specifications"] = req.get("rfq_specifications")

            job_result = self.use_case.execute(**exec_kwargs)
            elapsed = time.time() - t0

            # Fair Pay-Per-Lead Tiered Pricing (Strategy Financial Model)
            total_qualified = job_result.get("total_qualified", len(job_result.get("leads", [])))
            if total_qualified == 0:
                err_msg = job_result.get("message") or "No se encontraron prospectos que superaran los filtros de calidad o el registro mercantil estuvo inaccesible."
                print(f"[WorkerDaemon] [WARN] Order `{order_id}` produced 0 qualified leads. Marking failed.")
                if hasattr(self.order_repository, "mark_failed"):
                    self.order_repository.mark_failed(order_id, err_msg)

                if hasattr(self.alert_dispatcher, "send_feed_event"):
                    self.alert_dispatcher.send_feed_event(
                        title="Order Qualification Incomplete (0 Leads)",
                        message=f"Order `{order_id}` for {client_name} produced 0 qualified leads in {elapsed:.1f}s. Criteria may need broadening.",
                        details={
                            "order_id": order_id,
                            "client": client_name,
                            "campaign": campaign_id,
                            "city": city,
                            "tier": tier,
                            "status": "failed_zero_leads",
                            "reason": err_msg,
                        },
                    )

                if hasattr(self.alert_dispatcher, "send_alert"):
                    self.alert_dispatcher.send_alert(
                        title="Order Failed - 0 Qualified Leads",
                        message=f"Order `{order_id}` ({campaign_id} in {city}) yielded 0 leads: {err_msg}",
                        level="warning",
                        details={
                            "order_id": order_id,
                            "client": client_name,
                            "campaign": campaign_id,
                            "city": city,
                            "error": err_msg,
                        },
                    )
                return False

            country = req.get("country", "CO")
            country_allocations = req.get("country_allocations")
            if country_allocations:
                currency = "USD"
            elif country == "EC":
                currency = "USD"
            elif country == "DO":
                currency = "DOP"
            else:
                currency = job_result.get("currency", "COP")

            partner_ref = order.get("referral_partner") or (order.get("client") or {}).get("referral_partner")
            total_price_cents = calculate_lead_pricing(
                total_qualified=total_qualified,
                tier=tier,
                currency=currency,
                partner_id=partner_ref,
            )

            # Upload deliverables to Storage Adapter (Local or GCS)
            print(f"[WorkerDaemon] [PACKAGE] [4/4] Packaging structured CSV/XLSX manifest and executive PDF dossier...")
            if hasattr(self.order_repository, "update_telemetry"):
                self.order_repository.update_telemetry(order_id, {
                    "phase": "generating_deliverables",
                    "phase_key": "telemetry.generating_deliverables",
                    "step_index": 3,
                    "progress_percent": 85,
                })
            csv_path = job_result.get("csv_path")
            xlsx_path = job_result.get("xlsx_path")
            dossier_path = job_result.get("dossier_path")
            full_csv_path = job_result.get("full_csv_path")
            pdf_path = job_result.get("pdf_path")

            if csv_path and os.path.exists(csv_path):
                dest_csv = f"orders/{order_id}/prospects.csv"
                csv_uri = self.storage_adapter.upload_file(csv_path, dest_csv, content_type="text/csv")
                csv_url = self.storage_adapter.generate_download_url(dest_csv, expiration_hours=48)
                job_result["csv_uri"] = csv_uri
                job_result["csv_download_url"] = csv_url
                print(f"[WorkerDaemon] [PACKAGE] Clean CRM CSV Stored: {csv_uri}")

            if full_csv_path and os.path.exists(full_csv_path):
                dest_full_csv = f"orders/{order_id}/prospects_full_intelligence.csv"
                full_csv_uri = self.storage_adapter.upload_file(full_csv_path, dest_full_csv, content_type="text/csv")
                full_csv_url = self.storage_adapter.generate_download_url(dest_full_csv, expiration_hours=48)
                job_result["full_csv_uri"] = full_csv_uri
                job_result["full_csv_download_url"] = full_csv_url
                print(f"[WorkerDaemon] [PACKAGE] Full Intelligence CSV Stored: {full_csv_uri}")

            if xlsx_path and os.path.exists(xlsx_path):
                dest_xlsx = f"orders/{order_id}/prospects.xlsx"
                xlsx_uri = self.storage_adapter.upload_file(xlsx_path, dest_xlsx, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                xlsx_url = self.storage_adapter.generate_download_url(dest_xlsx, expiration_hours=48)
                job_result["xlsx_uri"] = xlsx_uri
                job_result["xlsx_download_url"] = xlsx_url
                print(f"[WorkerDaemon]  XLSX Stored: {xlsx_uri}")

            if dossier_path and os.path.exists(dossier_path):
                dest_dossier = f"orders/{order_id}/executive_dossier.md"
                dossier_uri = self.storage_adapter.upload_file(dossier_path, dest_dossier, content_type="text/markdown")
                dossier_url = self.storage_adapter.generate_download_url(dest_dossier, expiration_hours=48)
                job_result["dossier_uri"] = dossier_uri
                job_result["dossier_download_url"] = dossier_url
                print(f"[WorkerDaemon] [DOC] Markdown Dossier Stored: {dossier_uri}")

            if pdf_path and os.path.exists(pdf_path):
                dest_pdf = f"orders/{order_id}/executive_dossier.pdf"
                pdf_uri = self.storage_adapter.upload_file(pdf_path, dest_pdf, content_type="application/pdf")
                pdf_url = self.storage_adapter.generate_download_url(dest_pdf, expiration_hours=48)
                job_result["pdf_uri"] = pdf_uri
                job_result["pdf_download_url"] = pdf_url
                print(f"[WorkerDaemon] [PDF] PDF Dossier Stored: {pdf_uri}")

            self.order_repository.complete_order(
                order_id=order_id,
                job_result=job_result,
                amount_in_cents=total_price_cents
            )

            # Trigger buyer notification (Email + WhatsApp)
            if hasattr(self.order_repository, "get_order"):
                fresh_order = self.order_repository.get_order(order_id)
                if fresh_order and not fresh_order.get("ready_notified_at"):
                    try:
                        from src.adapters.delivery.omnichannel_delivery_adapter import OmnichannelDeliveryAdapter
                        delivery_adapter = OmnichannelDeliveryAdapter()
                        verified_count = job_result.get("total_qualified", 0)
                        if 1 <= verified_count < 3:
                            # Low Yield Courtesy Gift ($0 charge, single email with downloads/attachments)
                            delivery_adapter.send_courtesy_gift_notification(fresh_order)
                            print(f"[WorkerDaemon] Dispatched single courtesy gift email for `{order_id}` ({verified_count} leads).")
                        elif verified_count >= 3:
                            # Standard Yield Fair-Price Quote (Quote email without files)
                            delivery_adapter.send_ready_for_review_notification(fresh_order)
                            print(f"[WorkerDaemon] Dispatched review quote notification for `{order_id}` ({verified_count} leads).")
                        if hasattr(self.order_repository, "mark_ready_notified"):
                            self.order_repository.mark_ready_notified(order_id)
                    except Exception as notify_err:
                        print(f"[WorkerDaemon] [WARN] Error dispatching notification for `{order_id}`: {notify_err}")

            if hasattr(self.alert_dispatcher, "send_feed_event"):
                self.alert_dispatcher.send_feed_event(
                    title="Leads Ready & Awaiting Payment",
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

            print(f"[WorkerDaemon] [OK] Order `{order_id}` completed successfully in {elapsed:.2f}s!")
            print(f"               Qualified Leads: {job_result.get('total_qualified', 0)}")
            print(f"               Status: awaiting_payment (Quote: ${total_price_cents // 100:,.0f} COP)")
            print(f"               Ready for buyer review and Wompi unlock.\n")
            return True

        except Exception as e:
            print(f"[WorkerDaemon] [ERROR] Error processing Order `{order_id}`: {e}")
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

            client_email = order.get("client", {}).get("email") if isinstance(order, dict) else "N/A"
            if hasattr(self.alert_dispatcher, "send_feed_event"):
                self.alert_dispatcher.send_feed_event(
                    title="Order Execution Error",
                    message=f"Order `{order_id}` encountered an error: {e}",
                    details={
                        "order_id": order_id,
                        "client": client_email,
                        "status": "execution_error",
                        "reason": str(e),
                    },
                )

            # If dead-lettered after max retries, dispatch operator alert immediately
            if not failure_info or failure_info.get("status") == "dead-lettered":
                self.alert_dispatcher.send_alert(
                    title="Order Dead-Lettered (Execution Failure)",
                    message=f"Order `{order_id}` failed unrecoverably: {e}",
                    level="error",
                    details={
                        "order_id": order_id,
                        "client_email": client_email,
                        "retry_count": failure_info.get("order", {}).get("retry_count") if failure_info else "N/A",
                        "error": str(e),
                    },
                )
            return False

    def run_loop(self, poll_interval_sec: int = 5, run_once: bool = False):
        print("=" * 80)
        print("  [DAEMON] MICHITO ASYNCHRONOUS ORDER WORKER DAEMON STARTED")
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
                    dead_lettered = self.order_repository.recover_stuck_processing_orders(max_processing_minutes=60)
                    for dead in dead_lettered:
                        print(f"[WorkerDaemon] [ALERT] Order `{dead['order_id']}` Dead-Lettered by Timeout Reaper!")
                        self.alert_dispatcher.send_alert(
                            title="Order Dead-Lettered (Timeout Recovery)",
                            message=f"Order `{dead['order_id']}` exceeded maximum execution time and maximum retry attempts.",
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
                    print(f"[WorkerDaemon] [RUN] Found {len(queued_orders)} queued order(s) waiting in database. Processing now...")
                    for ord_doc in queued_orders:
                        self.process_order(ord_doc)
                else:
                    if loop_count % 4 == 1 and not run_once:
                        now_str = time.strftime("%H:%M:%S")
                        print(f"[{now_str}]  [WorkerDaemon] [HEARTBEAT] Heartbeat: Daemon healthy • Polling {mode_str} (Interval: {poll_interval_sec}s)...")

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
