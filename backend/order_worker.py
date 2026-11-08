#!/usr/bin/env python3
"""
Michito Asynchronous Order Processing Worker (Root Entrypoint)
Delegates to src.entrypoints.workers.order_worker_daemon.OrderWorkerDaemon.
"""

import os
import sys
import argparse
from typing import Dict, Any

# Ensure backend directory and monorepo root are on sys.path
backend_dir = os.path.abspath(os.path.dirname(__file__))
repo_root = os.path.abspath(os.path.join(backend_dir, ".."))
for p in [backend_dir, repo_root]:
    if p not in sys.path:
        sys.path.insert(0, p)

import src.config  # Auto-loads .env.local / .env.stg / .env

from src.adapters.db.firestore_order_adapter import FirestoreOrderAdapter
from src.application.use_cases.generate_prospects_use_case import run_prospecting_job
from src.entrypoints.workers.order_worker_daemon import OrderWorkerDaemon


class DynamicProspectingUseCaseAdapter:
    """Invokes the module-level run_prospecting_job dynamically (allowing unittest mocks)."""
    def execute(self, **kwargs):
        return run_prospecting_job(**kwargs)


def process_single_order(adapter: FirestoreOrderAdapter, order: Dict[str, Any]) -> bool:
    daemon = OrderWorkerDaemon(
        order_repository=adapter,
        use_case=DynamicProspectingUseCaseAdapter()
    )
    return daemon.process_order(order)


def run_worker_loop(poll_interval_sec: int = 5, run_once: bool = False):
    from src.adapters.queue.pubsub_queue_adapter import PubSubQueueAdapter
    queue_adapter = None
    try:
        queue_adapter = PubSubQueueAdapter()
    except Exception as e:
        print(f"Failed to initialize PubSub adapter: {e}")
        
    daemon = OrderWorkerDaemon(
        order_queue=queue_adapter,
        use_case=DynamicProspectingUseCaseAdapter()
    )
    daemon.run_loop(poll_interval_sec=poll_interval_sec, run_once=run_once)


def main():
    parser = argparse.ArgumentParser(description="Michito Asynchronous Order Processing Worker")
    parser.add_argument("--interval", type=int, default=5, help="Polling interval in seconds (default: 5)")
    parser.add_argument("--once", action="store_true", help="Process currently queued orders and exit")
    args = parser.parse_args()

    run_worker_loop(poll_interval_sec=args.interval, run_once=args.once)


if __name__ == "__main__":
    main()
