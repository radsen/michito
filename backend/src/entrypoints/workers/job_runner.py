#!/usr/bin/env python3
"""
Michito Cloud Run Job Entrypoint — Decoupled Batch Intelligence Worker.
Executes deep registry harvesting, DNS/MX validation, financial underwriting,
commercial file generation (CSV, XLSX, PDF), GCS persistence, and email delivery.

Designed to be executed as an ephemeral Cloud Run Job:
  python -m src.entrypoints.workers.job_runner --order-id <order_id>
Or via environment variable:
  ORDER_ID=<order_id> python -m src.entrypoints.workers.job_runner
"""

import os
import sys
import argparse
import logging
from typing import Optional

# Ensure application paths are available
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

try:
    import src.config  # Auto-loads .env / .env.stg / .env.local
except ImportError:
    pass

from src.adapters.db.sql_order_adapter import SqlOrderAdapter
from src.adapters.delivery.omnichannel_delivery_adapter import OmnichannelDeliveryAdapter
from src.application.use_cases.deliver_order_use_case import DeliverOrderUseCase
from src.entrypoints.workers.order_worker_daemon import OrderWorkerDaemon

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [JobRunner] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("MichitoJobRunner")


def run_batch_job(order_id: str) -> bool:
    """
    Executes the decoupled harvesting and delivery pipeline for a single order.
    Returns True on success, False on failure.
    """
    if not order_id:
        logger.error("Missing required order_id. Terminating job.")
        return False

    logger.info("=" * 80)
    logger.info(f"STARTING DECOUPLED CLOUD RUN JOB FOR ORDER `{order_id}`")
    logger.info("=" * 80)

    sql_adapter = SqlOrderAdapter()
    order = sql_adapter.get_order(order_id)
    if not order:
        logger.error(f"Order `{order_id}` was not found in the database. Terminating.")
        return False

    client_data = order.get("client", {})
    client_name = client_data.get("name", "Unknown Buyer")
    client_email = client_data.get("email", "unknown@example.com")
    payment_status = order.get("payment", {}).get("status")
    order_status = order.get("status")

    logger.info(f"Target Client:   {client_name} ({client_email})")
    logger.info(f"Order Status:    {order_status} | Payment: {payment_status}")
    logger.info(f"Requested Limit: {order.get('request', {}).get('limit', 10)} leads")

    # Idempotency check: if order is already completed and files exist
    delivery = order.get("delivery", {})
    if (
        order_status in ("paid", "completed", "fulfilled")
        and delivery.get("delivered_at")
        and (delivery.get("csv_path") or delivery.get("xlsx_path"))
    ):
        logger.info(f"Order `{order_id}` is already fully fulfilled and delivered. Exiting successfully.")
        return True

    # 1. Update initial telemetry phase
    sql_adapter.update_telemetry(
        order_id,
        {
            "phase": "harvesting",
            "phase_key": "telemetry.harvesting",
            "step_index": 1,
            "progress_percent": 25,
        },
        status="processing",
    )

    # 2. Execute heavy harvesting, verification, and file packaging via Worker Daemon
    daemon = OrderWorkerDaemon(order_repository=sql_adapter)
    success = daemon.process_order(order)
    if not success:
        logger.error(f"Execution failed in OrderWorkerDaemon for order `{order_id}`.")
        sql_adapter.update_telemetry(
            order_id,
            {
                "phase": "error",
                "phase_key": "telemetry.error",
                "step_index": 4,
                "progress_percent": 100,
            },
            status="failed",
        )
        return False

    # 3. Reload fresh order and dispatch email with GCS deliverables attached
    fresh_order = sql_adapter.get_order(order_id) or order
    sql_adapter.update_telemetry(
        order_id,
        {
            "phase": "delivering_email",
            "phase_key": "telemetry.delivering_email",
            "step_index": 4,
            "progress_percent": 95,
        },
    )

    try:
        delivery_adapter = OmnichannelDeliveryAdapter()
        deliver_use_case = DeliverOrderUseCase(
            delivery_port=delivery_adapter,
            order_repository=sql_adapter,
        )
        delivered = deliver_use_case.execute(order_id)
        if delivered:
            logger.info(f"Omnichannel delivery successfully dispatched for `{order_id}`.")
        else:
            logger.warning(f"Omnichannel delivery returned False for `{order_id}`, but deliverables exist.")
    except Exception as del_err:
        logger.error(f"Error during email delivery for `{order_id}`: {del_err}")
        # We do not fail the whole job if email send failed, files are securely stored in GCS.

    # 4. Final completion telemetry
    sql_adapter.update_telemetry(
        order_id,
        {
            "phase": "completed",
            "phase_key": "telemetry.completed",
            "step_index": 5,
            "progress_percent": 100,
        },
        status="paid",
    )

    logger.info("=" * 80)
    logger.info(f"CLOUD RUN JOB COMPLETED SUCCESSFULLY FOR ORDER `{order_id}`")
    logger.info("=" * 80)
    return True


def main():
    parser = argparse.ArgumentParser(description="Michito Decoupled Cloud Run Batch Harvesting Job")
    parser.add_argument(
        "--order-id",
        type=str,
        default=os.environ.get("ORDER_ID"),
        help="Prospecting Order Reference ID (e.g., ord_20261118_f05b2a)",
    )
    args = parser.parse_args()

    order_id = args.order_id
    if not order_id:
        logger.error("No --order-id specified and ORDER_ID environment variable is unset.")
        sys.exit(1)

    ok = run_batch_job(order_id=order_id.strip())
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
