"""
SECOP II Direct Contact Harvester Adapter
Extracts verified Colombian corporate contractors, legal representatives,
direct emails, and cell phone numbers from statutory public disclosures
on datos.gov.co (SECOP II Proveedores Registrados - Resource ID: qmzu-gj57).
"""

import json
import re
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

from src.domain.entities.company import Company
from src.domain.entities.decision_maker import DecisionMaker
from src.domain.value_objects.tax_id import TaxId


class SecopHarvesterAdapter:
    """
    Consumes official Colombia Compra Eficiente SECOP II open datasets
    to retrieve verified corporate entities with direct legal representative contact data.
    """

    RESOURCE_ID = "qmzu-gj57"
    BASE_URL = f"https://www.datos.gov.co/resource/{RESOURCE_ID}.json"

    VALID_CORPORATE_TYPES = [
        "Sociedad por acciones simplificada",
        "Sociedad Anónima Abierta colombiana",
        "Sociedad Anónima Cerrada Colombiana",
        "Sociedad de Responsabilidad Limitada colombiana",
        "Sucursal de Sociedad Extranjera",
    ]

    def __init__(self, app_token: Optional[str] = None, timeout: int = 15):
        self.app_token = app_token
        self.timeout = timeout

    @staticmethod
    def _clean_phone(raw_phone: Optional[str]) -> str:
        if not raw_phone or raw_phone.strip() in ("No Provisto", "No Definido", "0"):
            return ""
        digits = re.sub(r"\D", "", raw_phone)
        # Strip country code if prefixed (+57)
        if digits.startswith("57") and len(digits) > 10:
            digits = digits[2:]
        return digits

    @staticmethod
    def _is_valid_email(email: Optional[str]) -> bool:
        if not email or email.strip() in ("No Provisto", "No Definido"):
            return False
        # Basic RFC 5322 regex
        pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        return bool(re.match(pattern, email.strip()))

    def fetch_candidates(
        self,
        city: str = "Medellín",
        limit: int = 50,
        corporate_only: bool = True,
        min_contracts_hint: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Queries SECOP II for active registered corporate entities in the target city,
        extracting real legal representatives, direct emails, and phone numbers.
        """
        params: Dict[str, str] = {
            "esta_activa": "Si",
            "$limit": str(max(limit * 3, 100)),
        }

        if city.strip().lower() in ("bogotá", "bogota", "bogota d.c.", "bogotá d.c."):
            params["departamento"] = "Distrito Capital de Bogotá"
        else:
            params["municipio"] = city

        if corporate_only:
            # Default to S.A.S., which represents 80%+ of modern mid-market Colombian companies
            params["tipo_empresa"] = "Sociedad por acciones simplificada"

        encoded_url = f"{self.BASE_URL}?" + urllib.parse.urlencode(params)
        headers = {"User-Agent": "MichitoB2BIntelligence/1.0", "Accept": "application/json"}
        if self.app_token:
            headers["X-App-Token"] = self.app_token

        req = urllib.request.Request(encoded_url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw_data = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            # Fallback empty list on connection/network error
            return []

        qualified_leads: List[Dict[str, Any]] = []

        for item in raw_data:
            company_name = (item.get("nombre") or "").strip()
            raw_nit = (item.get("nit") or "").strip()
            rep_name = (item.get("nombre_representante_legal") or "").strip()
            
            # Prioritize representative email over generic company email
            email = (
                item.get("correo_representante_legal")
                or item.get("correo")
                or ""
            ).strip().lower()

            phone = self._clean_phone(
                item.get("telefono_representante_legal") or item.get("telefono")
            )

            # Filtering criteria:
            # 1. Must have a valid email
            # 2. Must have a real decision maker name (not equal to the company name itself)
            # 3. Must have a NIT
            if not self._is_valid_email(email):
                continue
            if not rep_name or rep_name.upper() == company_name.upper():
                continue
            if not raw_nit:
                continue

            # Clean and normalize
            clean_nit_base = raw_nit.replace(".", "").split("-")[0]
            clean_rep_title = "Representante Legal / Gerente General"
            rep_name_title = rep_name.title()

            google_xray = (
                f"https://www.google.com/search?q="
                f"{urllib.parse.quote_plus(f'site:co.linkedin.com/in/ \"{company_name}\" \"{rep_name_title}\"')}"
            )

            lead_dict = {
                "company_id": f"CO-{clean_nit_base}",
                "nit": raw_nit,
                "company_name": company_name,
                "sector": item.get("descripcion_categoria_principal") or "Servicios Empresariales",
                "city": item.get("municipio") or city,
                "department": item.get("departamento") or "",
                "address": (item.get("direccion") or "").strip(),
                "website": item.get("sitio_web") if item.get("sitio_web") != "No Provisto" else "",
                "company_type": item.get("tipo_empresa") or "",
                "decision_maker_name": rep_name_title,
                "decision_maker_title": clean_rep_title,
                "email": email,
                "phone": phone,
                "linkedin_xray_url": google_xray,
                "data_source": "SECOP_II_REGISTRY",
            }

            qualified_leads.append(lead_dict)
            if len(qualified_leads) >= limit:
                break

        return qualified_leads

