"""
Persistent Deduplication Ledger for B2B Prospects.
Ensures subsequent runs never return companies already prospected across any client or campaign.
"""

import os
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Set, Optional

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../")
)
DEFAULT_LEDGER_PATH = os.path.join(PROJECT_ROOT, "data/prospects_ledger.json")

PERMANENT_EXCLUDED_NITS = {"901048123-5", "9010481235", "901048123"}
PERMANENT_EXCLUDED_KEYWORDS = {"tinkko"}


class DeduplicationLedger:
    def __init__(self, ledger_path: str = DEFAULT_LEDGER_PATH):
        self.ledger_path = ledger_path
        os.makedirs(os.path.dirname(self.ledger_path), exist_ok=True)
        self.data: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        if os.path.exists(self.ledger_path):
            try:
                with open(self.ledger_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    if not isinstance(loaded, dict):
                        loaded = {}
                    if "metadata" not in loaded:
                        loaded["metadata"] = {
                            "created_at": datetime.now(timezone.utc).isoformat(),
                            "last_updated_at": datetime.now(timezone.utc).isoformat(),
                            "total_prospects": 0,
                        }
                    if "prospects" not in loaded:
                        loaded["prospects"] = {}

                    # Filter out any permanent exclusions
                    cleaned_prospects = {}
                    for nit_key, p_data in loaded.get("prospects", {}).items():
                        c_nit = self._clean_nit(nit_key)
                        name_lower = p_data.get("company_name", "").lower()
                        if c_nit in PERMANENT_EXCLUDED_NITS or any(k in name_lower for k in PERMANENT_EXCLUDED_KEYWORDS):
                            continue
                        cleaned_prospects[nit_key] = p_data
                    loaded["prospects"] = cleaned_prospects
                    return loaded
            except Exception as e:
                print(f"[Ledger] Warning: Failed to parse existing ledger ({e}). Starting fresh.")
        return {
            "metadata": {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "last_updated_at": datetime.now(timezone.utc).isoformat(),
                "total_prospects": 0
            },
            "prospects": {}
        }

    def _save(self) -> None:
        if "metadata" not in self.data:
            self.data["metadata"] = {
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        self.data["metadata"]["last_updated_at"] = datetime.now(timezone.utc).isoformat()
        self.data["metadata"]["total_prospects"] = len(self.data.get("prospects", {}))
        with open(self.ledger_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def is_seen(self, nit: str, company_name: str = "") -> bool:
        clean_nit = self._clean_nit(nit)
        if clean_nit in PERMANENT_EXCLUDED_NITS:
            return True
        if company_name and any(k in company_name.lower() for k in PERMANENT_EXCLUDED_KEYWORDS):
            return True
        return clean_nit in self.data["prospects"]

    def get_seen_nits(self, campaign: Optional[str] = None) -> Set[str]:
        if campaign:
            seen = set()
            for nit, p in self.data["prospects"].items():
                if p.get("target_product") == campaign:
                    seen.add(nit)
            seen.update(PERMANENT_EXCLUDED_NITS)
            return seen
        seen = set(self.data["prospects"].keys())
        seen.update(PERMANENT_EXCLUDED_NITS)
        return seen

    def record_prospect(
        self,
        nit: str,
        company_name: str,
        segment: str,
        sector: str,
        city: str,
        product: str,
        batch_id: str,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> None:
        clean_nit = self._clean_nit(nit)
        if clean_nit in PERMANENT_EXCLUDED_NITS or any(k in company_name.lower() for k in PERMANENT_EXCLUDED_KEYWORDS):
            return
        now_iso = datetime.now(timezone.utc).isoformat()

        self.data["prospects"][clean_nit] = {
            "nit": clean_nit,
            "company_name": company_name,
            "segment": segment,
            "sector": sector,
            "city": city,
            "target_product": product,
            "first_discovered_batch": batch_id,
            "discovered_at": now_iso,
            "status": "new",
            "notes": "",
            "details": extra_data or {}
        }

    def save_batch(self) -> None:
        self._save()

    def get_stats(self) -> Dict[str, Any]:
        prospects = self.data.get("prospects", {})
        segments_count: Dict[str, int] = {}
        cities_count: Dict[str, int] = {}
        products_count: Dict[str, int] = {}

        for p in prospects.values():
            seg = p.get("segment", "unknown")
            city = p.get("city", "unknown")
            prod = p.get("target_product", "unknown")
            segments_count[seg] = segments_count.get(seg, 0) + 1
            cities_count[city] = cities_count.get(city, 0) + 1
            products_count[prod] = products_count.get(prod, 0) + 1

        return {
            "total_companies_in_ledger": len(prospects),
            "by_segment": segments_count,
            "by_city": cities_count,
            "by_product": products_count,
            "last_updated": self.data.get("metadata", {}).get("last_updated_at")
        }

    @staticmethod
    def _clean_nit(raw_nit: str) -> str:
        if not raw_nit:
            return ""
        return raw_nit.strip().replace(".", "").replace(" ", "")

