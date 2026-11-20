"""
Michito FX & TRM Service — Official Currency Exchange Integration.
Fetches official Tasa Representativa del Mercado (TRM) from Superintendencia Financiera / datos.gov.co
and global exchange rates to provide accurate, transparent currency conversion between USD, DOP, and COP.
"""

import os
import json
import time
import logging
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

# Fallback official rates when network/external API is unreachable
BASELINE_RATES_TO_COP: Dict[str, float] = {
    "COP": 1.0,
    "USD": 4150.0,   # 1 USD = 4,150 COP (Superintendencia Financiera TRM)
    "DOP": 68.6,     # 1 DOP = 68.6 COP (Banco Central RD ~ 60.5 DOP/USD)
    "EUR": 4450.0,   # 1 EUR = 4,450 COP
    "CLP": 4.35,     # 1 CLP = 4.35 COP
}


class TrmExchangeRateService:
    """
    Manages live and cached currency conversions using official TRM data.
    """
    _instance: Optional["TrmExchangeRateService"] = None

    def __init__(self, cache_ttl_seconds: int = 3600):
        self.cache_ttl = cache_ttl_seconds
        self._rates_cache: Dict[str, float] = dict(BASELINE_RATES_TO_COP)
        self._last_updated: float = 0.0

    @classmethod
    def get_instance(cls) -> "TrmExchangeRateService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _refresh_rates_if_needed(self) -> None:
        now = time.time()
        if (now - self._last_updated) < self.cache_ttl:
            return

        # 1. Attempt official Colombia TRM from datos.gov.co
        try:
            url = "https://www.datos.gov.co/resource/32sa-8pi3.json?$limit=1&$order=vigenciahasta%20DESC"
            req = urllib.request.Request(url, headers={"User-Agent": "MichitoFX/1.0", "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data and isinstance(data, list) and "valor" in data[0]:
                    trm_val = float(data[0]["valor"])
                    if trm_val > 1000:
                        self._rates_cache["USD"] = trm_val
                        # Update DOP based on USD rate (~60.5 DOP per USD)
                        self._rates_cache["DOP"] = round(trm_val / 60.5, 2)
                        self._last_updated = now
                        logger.info(f"[TRM] Refreshed official TRM from datos.gov.co: 1 USD = {trm_val:,.2f} COP")
                        return
        except Exception as e:
            logger.debug(f"[TRM] datos.gov.co lookup bypassed: {e}")

        # 2. Secondary fallback: public exchange rate API
        try:
            url = "https://open.er-api.com/v6/latest/USD"
            req = urllib.request.Request(url, headers={"User-Agent": "MichitoFX/1.0", "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                rates = data.get("rates", {})
                cop_rate = rates.get("COP")
                dop_rate = rates.get("DOP")
                if cop_rate and cop_rate > 1000:
                    self._rates_cache["USD"] = float(cop_rate)
                    if dop_rate and dop_rate > 0:
                        self._rates_cache["DOP"] = round(float(cop_rate) / float(dop_rate), 2)
                    self._last_updated = now
                    logger.info(f"[TRM] Refreshed rates from open.er-api: 1 USD = {cop_rate:,.2f} COP")
                    return
        except Exception as e:
            logger.debug(f"[TRM] Secondary open.er-api lookup bypassed: {e}")

        # If external calls fail, refresh timestamp to avoid pounding offline networks
        self._last_updated = now

    def get_rates(self) -> Dict[str, Any]:
        """Returns current exchange rates to COP and TRM metadata."""
        self._refresh_rates_if_needed()
        return {
            "status": "success",
            "base": "COP",
            "rates_to_cop": dict(self._rates_cache),
            "trm_usd": self._rates_cache.get("USD", 4150.0),
            "trm_dop": self._rates_cache.get("DOP", 68.6),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def convert(
        self,
        amount: float,
        from_currency: str = "COP",
        to_currency: str = "COP"
    ) -> Dict[str, Any]:
        """
        Converts an amount between supported currencies using TRM rates.
        """
        self._refresh_rates_if_needed()
        from_c = (from_currency or "COP").upper()
        to_c = (to_currency or "COP").upper()

        rate_from = self._rates_cache.get(from_c, 1.0)
        rate_to = self._rates_cache.get(to_c, 1.0)

        # Convert to COP base first, then to target
        amount_in_cop = amount * rate_from
        converted = amount_in_cop / rate_to if rate_to > 0 else amount_in_cop

        # Format cleanly
        if to_c == "USD":
            formatted = f"${converted:,.2f} USD"
        elif to_c == "DOP":
            formatted = f"RD$ {converted:,.2f} DOP"
        else:
            formatted = f"${round(converted):,} COP"

        return {
            "status": "success",
            "from_currency": from_c,
            "to_currency": to_c,
            "original_amount": amount,
            "converted_amount": round(converted, 2) if to_c in ("USD", "DOP") else round(converted),
            "amount_in_cop": round(amount_in_cop),
            "formatted": formatted,
            "rate_used": round(rate_from / rate_to, 4) if rate_to > 0 else 1.0,
            "trm_cop": self._rates_cache.get("USD", 4150.0),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
