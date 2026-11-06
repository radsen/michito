"""
Firestore Order Adapter for Michito On-Demand Lead Platform.
Handles order lifecycle: queued -> processing -> completed (teaser ready) -> paid -> delivered.
Automatically respects FIRESTORE_EMULATOR_HOST for local offline development.
"""

import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
import uuid

try:
    from google.cloud import firestore
    from google.api_core.exceptions import GoogleAPICallError
    FIRESTORE_AVAILABLE = True
except ImportError:
    FIRESTORE_AVAILABLE = False


class FirestoreOrderAdapter:
    def __init__(self, project_id: str = "michito-growth", force_mock: bool = False):
        self.project_id = project_id
        self.db = None
        self._in_memory_orders: Dict[str, Dict[str, Any]] = {}

        if not force_mock and FIRESTORE_AVAILABLE:
            emulator_host = os.environ.get("FIRESTORE_EMULATOR_HOST")
            gcp_creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
            # Only instantiate real gRPC client if emulator is running or credentials are configured
            if emulator_host or gcp_creds:
                try:
                    self.db = firestore.Client(project=self.project_id)
                except Exception:
                    self.db = None

    @property
    def is_connected(self) -> bool:
        return self.db is not None

    def create_order(
        self,
        client_name: str,
        client_email: str,
        campaign_id: str,
        city: str = "Medellín",
        limit: int = 10,
        client_phone: str = "",
        client_id: Optional[str] = None,
        country: str = "CO",
        currency: str = "COP",
        segment: str = "midmarket",
        cities: Optional[List[str]] = None,
        sectors: Optional[List[str]] = None,
        keywords_include: Optional[List[str]] = None,
        keywords_exclude: Optional[List[str]] = None,
        target_roles: Optional[List[str]] = None,
        tier: int = 2,
        order_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Creates a new lead generation order in 'queued' state with full multi-client attributes.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        if not order_id:
            order_id = f"ord_{datetime.now(timezone.utc).strftime('%Y%m%d')}_{uuid.uuid4().hex[:6]}"

        resolved_cities = cities or ([city] if city and city.lower() != "all" else [])

        order_doc = {
            "order_id": order_id,
            "client_id": client_id or campaign_id.split("_")[0],
            "client": {
                "name": client_name.strip(),
                "email": client_email.strip().lower(),
                "phone": client_phone.strip(),
            },
            "request": {
                "campaign_id": campaign_id,
                "city": city,
                "cities": resolved_cities,
                "country": country.upper(),
                "currency": currency.upper(),
                "limit": int(limit),
                "segment": segment,
                "tier": tier,
                "sectors": sectors or [],
                "keywords_include": keywords_include or [],
                "keywords_exclude": keywords_exclude or [],
                "target_roles": target_roles or [],
            },
            "status": "queued",
            "payment": {
                "provider": "wompi",
                "status": "pending",
                "amount_in_cents": 0,
                "currency": currency.upper(),
                "transaction_id": None,
                "paid_at": None,
            },
            "delivery": {
                "total_qualified": 0,
                "sample_teaser": [],
                "csv_path": None,
                "dossier_path": None,
                "delivered_at": None,
            },
            "metrics": {},
            "created_at": now_iso,
            "updated_at": now_iso,
        }

        if self.db:
            self.db.collection("orders").document(order_id).set(order_doc)
        else:
            self._in_memory_orders[order_id] = order_doc

        return order_doc

    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves order details by ID.
        """
        if self.db:
            doc = self.db.collection("orders").document(order_id).get()
            if doc.exists:
                return doc.to_dict()
            return None
        return self._in_memory_orders.get(order_id)

    def fetch_queued_orders(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Fetches orders currently waiting to be processed.
        """
        if self.db:
            query = (
                self.db.collection("orders")
                .where("status", "==", "queued")
                .limit(limit)
            )
            return [doc.to_dict() for doc in query.stream()]
        else:
            return [
                doc for doc in self._in_memory_orders.values()
                if doc.get("status") == "queued"
            ][:limit]

    def mark_processing(self, order_id: str) -> bool:
        """
        Transitions order from 'queued' to 'processing' to prevent concurrent workers from clashing.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        if self.db:
            ref = self.db.collection("orders").document(order_id)
            doc = ref.get()
            if not doc.exists or doc.to_dict().get("status") != "queued":
                return False
            ref.update({
                "status": "processing",
                "started_processing_at": now_iso,
                "updated_at": now_iso,
            })
            return True
        else:
            doc = self._in_memory_orders.get(order_id)
            if not doc or doc.get("status") != "queued":
                return False
            doc["status"] = "processing"
            doc["started_processing_at"] = now_iso
            doc["updated_at"] = now_iso
            return True

    def complete_order(
        self,
        order_id: str,
        worker_result: Optional[Dict[str, Any]] = None,
        amount_in_cents: int = 0,
        job_result: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Records the generated leads, teaser, paths, and transitions status to 'completed' / 'awaiting_payment'.
        """
        res = worker_result or job_result or {}
        now_iso = datetime.now(timezone.utc).isoformat()
        update_payload = {
            "status": "awaiting_payment" if amount_in_cents > 0 else "completed",
            "delivery": {
                "total_qualified": res.get("total_qualified", 0),
                "sample_teaser": res.get("sample_teaser", []),
                "csv_path": res.get("csv_path"),
                "dossier_path": res.get("dossier_path"),
                "delivered_at": now_iso if amount_in_cents == 0 else None,
            },
            "metrics": res.get("metrics", {}),
            "updated_at": now_iso,
            "completed_at": now_iso,
        }
        if amount_in_cents > 0:
            update_payload["payment.amount_in_cents"] = amount_in_cents

        if self.db:
            self.db.collection("orders").document(order_id).update(update_payload)
            return True
        else:
            doc = self._in_memory_orders.get(order_id)
            if not doc:
                return False
            doc.update({
                "status": update_payload["status"],
                "delivery": update_payload["delivery"],
                "metrics": update_payload["metrics"],
                "updated_at": now_iso,
                "completed_at": now_iso,
            })
            if amount_in_cents > 0:
                doc["payment"]["amount_in_cents"] = amount_in_cents
            return True

    def mark_order_paid(
        self,
        order_id: str,
        transaction_id: str,
        amount_paid: float,
        currency: str = "COP"
    ) -> bool:
        """
        Called when Wompi webhook confirms payment.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        update_data = {
            "status": "paid",
            "payment": {
                "provider": "wompi",
                "status": "approved",
                "amount_paid": amount_paid,
                "currency": currency.upper(),
                "transaction_id": transaction_id,
                "paid_at": now_iso,
            },
            "delivery.delivered_at": now_iso,
            "updated_at": now_iso,
        }

        if self.db:
            self.db.collection("orders").document(order_id).update(update_data)
            return True
        else:
            doc = self._in_memory_orders.get(order_id)
            if not doc:
                return False
            doc["status"] = "paid"
            doc["payment"]["status"] = "approved"
            doc["payment"]["transaction_id"] = transaction_id
            doc["payment"]["paid_at"] = now_iso
            doc["delivery"]["delivered_at"] = now_iso
            doc["updated_at"] = now_iso
            return True

