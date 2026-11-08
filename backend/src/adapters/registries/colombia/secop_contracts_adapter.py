"""
SECOP II Contract Awards Adapter (Buying Intent Trigger)
Enriches Colombian corporate prospects with verified public contract awards
from Colombia Compra Eficiente (SECOP II Contratos Electrónicos - Resource ID: jbjy-vk9h).
Identifies companies with active expansion cash inflows and delivery obligations.
"""

import json
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional


class SecopContractsAdapter:
    """
    Queries SECOP II electronic contracts to retrieve verified contract awards,
    award values, contracting entities, and objects for a given corporate NIT.
    """

    RESOURCE_ID = "jbjy-vk9h"
    BASE_URL = f"https://www.datos.gov.co/resource/{RESOURCE_ID}.json"

    def __init__(self, timeout: int = 6):
        self.timeout = timeout

    def fetch_contracts_summary(self, nit: str) -> Dict[str, Any]:
        """
        Retrieves recent contract award records for the specified NIT.
        Returns a structured summary containing total contract value, contract count,
        and details of the most significant contract award.
        """
        clean_nit = nit.replace(".", "").replace(" ", "").split("-")[0].strip()
        if not clean_nit or not clean_nit.isdigit():
            return self._empty_summary()

        params = {
            "documento_proveedor": clean_nit,
            "$limit": "10",
            "$order": "valor_del_contrato DESC",
        }

        url = f"{self.BASE_URL}?" + urllib.parse.urlencode(params)
        headers = {"User-Agent": "MichitoIntentIntelligence/1.0", "Accept": "application/json"}
        req = urllib.request.Request(url, headers=headers)

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                records = json.loads(resp.read().decode("utf-8"))
        except Exception:
            return self._empty_summary()

        if not records:
            return self._empty_summary()

        total_value = 0.0
        for r in records:
            try:
                total_value += float(r.get("valor_del_contrato") or 0)
            except (ValueError, TypeError):
                continue

        top_rec = records[0]
        top_val = 0.0
        try:
            top_val = float(top_rec.get("valor_del_contrato") or 0)
        except (ValueError, TypeError):
            pass

        top_entity = (top_rec.get("nombre_entidad") or "").strip().title()
        top_object = (top_rec.get("descripcion_del_proceso") or top_rec.get("objeto_del_contrato") or "").strip()

        # Intent scoring
        if total_value >= 500_000_000:
            intent_level = "Muy Alto (Adjudicación > $500M COP)"
        elif total_value >= 100_000_000:
            intent_level = "Alto (Adjudicación > $100M COP)"
        elif total_value > 0:
            intent_level = "Medio (Contratista Activo Adjudicado)"
        else:
            intent_level = "Sin contratos públicos registrados"

        return {
            "has_contracts": True,
            "contracts_count": len(records),
            "total_value_cop": total_value,
            "total_value_display": f"${total_value:,.0f} COP" if total_value > 0 else "$0 COP",
            "top_contract_entity": top_entity,
            "top_contract_value_cop": top_val,
            "top_contract_value_display": f"${top_val:,.0f} COP" if top_val > 0 else "$0 COP",
            "top_contract_object": top_object[:120] + ("..." if len(top_object) > 120 else ""),
            "intent_level": intent_level,
        }

    @staticmethod
    def _empty_summary() -> Dict[str, Any]:
        return {
            "has_contracts": False,
            "contracts_count": 0,
            "total_value_cop": 0.0,
            "total_value_display": "$0 COP",
            "top_contract_entity": "Sin contratos públicos recientes",
            "top_contract_value_cop": 0.0,
            "top_contract_value_display": "$0 COP",
            "top_contract_object": "Operación exclusivamente privada",
            "intent_level": "Estándar (Crecimiento Privado)",
        }

