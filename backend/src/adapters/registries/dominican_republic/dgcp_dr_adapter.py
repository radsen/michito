"""
Dominican Republic DGCP (Dirección General de Contrataciones Públicas) Adapter
Extracts verified commercial corporations, active contract awards, legal representatives,
commercial emails, and phone numbers from official open datasets on datosabiertos.dgcp.gob.do.
"""

import json
import re
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional


class DgcpDrAdapter:
    """
    Adapter consuming the Dominican Republic DGCP REST API (Open Contracting Data Standard)
    to identify active commercial vendors and contract awardees in Santo Domingo and Santiago.
    """

    BASE_URL = "https://datosabiertos.dgcp.gob.do/api-dgcp/v1"

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.headers = {
            "User-Agent": "MichitoB2BIntelligence/1.0",
            "Accept": "application/json",
        }

    def _query_api(self, endpoint: str, params: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        query_str = f"?{urllib.parse.urlencode(params)}" if params else ""
        url = f"{self.BASE_URL}/{endpoint}{query_str}"
        req = urllib.request.Request(url, headers=self.headers)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception:
            return {}

    def fetch_proveedor_by_rpe(self, rpe: int) -> Optional[Dict[str, Any]]:
        """
        Retrieves detailed corporate and representative registration for an RPE.
        """
        data = self._query_api("proveedores", {"rpe": str(rpe)})
        content = data.get("payload", {}).get("content", [])
        if content:
            return content[0]
        return None

    def fetch_candidates(
        self,
        city: str = "Santo Domingo",
        limit: int = 10,
        corporate_only: bool = True,
        min_contract_dop: float = 0.0,
        include_keywords: Optional[List[str]] = None,
        exclude_keywords: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetches active commercial vendors from DGCP contracts and suppliers.
        Pairs contract awards (Trigger 1) with verified contact details.
        Supports positive and negative sector keyword filtering and multi-page harvesting.
        """
        candidates: List[Dict[str, Any]] = []
        seen_rpes = set()

        # Scale scan depth: Scan more pages if specific keywords are requested
        max_pages = max(4, (limit // 10) + 4) if include_keywords else max(1, (limit // 30) + 1)

        for page in range(1, max_pages + 1):
            if len(candidates) >= limit:
                break

            contracts_data = self._query_api("contratos", {"page": str(page), "limit": "100"})
            raw_contracts = contracts_data.get("payload", {}).get("content", [])
            if not raw_contracts:
                break

            for c in raw_contracts:
                if len(candidates) >= limit:
                    break
                if c.get("estado_contrato") != "Activo":
                    continue

                rpe = c.get("rpe")
                if not rpe or rpe in seen_rpes:
                    continue

                contract_val = float(c.get("valor_contratado") or 0.0)
                if contract_val < min_contract_dop:
                    continue

                c_desc = (c.get("descripcion") or "").lower()
                c_company = (c.get("razon_social") or "").lower()
                c_text = f"{c_desc} {c_company}"

                # Negative Keyword Exclusion Gate
                if exclude_keywords:
                    if any(bad.lower() in c_text for bad in exclude_keywords):
                        continue

                # Positive Keyword Target Gate
                if include_keywords:
                    if not any(good.lower() in c_text for good in include_keywords):
                        continue

                seen_rpes.add(rpe)

                # Fetch contact and legal registration
                prov = self.fetch_proveedor_by_rpe(rpe)
                if not prov:
                    continue

                company_name = (prov.get("razon_social") or c.get("razon_social") or "").strip()
                rnc = (prov.get("numero_documento") or "").strip()
                rep_name = (prov.get("contacto") or "").strip()
                rep_title = (prov.get("posicion_contacto") or "Gerente General / Director").strip()

                email = (prov.get("correo_contacto") or prov.get("correo_comercial") or "").strip().lower()
                phone = (
                    prov.get("celular_contacto")
                    or prov.get("telefono_contacto")
                    or prov.get("celular_comercial")
                    or prov.get("telefono_comercial")
                    or ""
                ).strip()

                # Clean phone: e.g. 809-562-3344 -> +1 809-562-3344
                clean_digits = re.sub(r"\D", "", phone)
                if len(clean_digits) == 10 and clean_digits.startswith(("809", "829", "849")):
                    formatted_phone = f"+1 ({clean_digits[:3]}) {clean_digits[3:6]}-{clean_digits[6:]}"
                elif len(clean_digits) >= 10:
                    formatted_phone = f"+{clean_digits}"
                else:
                    formatted_phone = phone

                # Quality Gate: Decision Maker Seniority Filter
                # Exclude administrative clerks, accounting assistants, and non-executive contacts
                title_lower = rep_title.lower()
                non_executive_patterns = (
                    "contab", "contador", "contadora", "secretari", "asistent",
                    "auxiliar", "recep", "mensajer", "pasante", "chofer",
                    "facturaci", "cobro", "tesorer", "almacen", "digitador"
                )
                if any(p in title_lower for p in non_executive_patterns):
                    continue

                # Must have valid email and decision maker name
                if not email or "@" not in email:
                    continue
                if not rep_name or len(rep_name) < 3:
                    continue

                # Build 1-Click LinkedIn Executive X-Ray URL
                clean_co = re.sub(
                    r"\b(S\.?A\.?S\.?|S\.?R\.?L\.?|S\.?A\.?|E\.?I\.?R\.?L\.?|INC\.?|CORP\.?)\b",
                    "",
                    company_name,
                    flags=re.IGNORECASE
                ).strip().rstrip(" ,.-")
                linkedin_query = f'site:do.linkedin.com/in/ "{clean_co}" ("Gerente General" OR "Director" OR "Presidente" OR "CEO" OR "COO" OR "Representante")'
                linkedin_xray_url = f"https://www.google.com/search?q={urllib.parse.quote_plus(linkedin_query)}"

                provincia = (prov.get("provincia") or "Distrito Nacional").title()
                municipio = (prov.get("municipio") or city).title()
                address = (prov.get("direccion") or f"{municipio}, República Dominicana").strip()

                # Contract details
                entity = (c.get("unidad_compra") or "").strip().title()
                c_desc = (c.get("descripcion") or "").strip()

                lead = {
                    "company_id": f"DO-{rnc}",
                    "nit": rnc,
                    "rnc": rnc,
                    "rpe": rpe,
                    "company_name": company_name,
                    "sector": "Servicios Empresariales & Comerciales",
                    "city": "Santo Domingo" if "Distrito" in provincia or "Nacional" in provincia else provincia,
                    "province": provincia,
                    "address": address,
                    "decision_maker_name": rep_name.title(),
                    "decision_maker_title": rep_title.title(),
                    "email": email,
                    "phone": formatted_phone,
                    "linkedin_xray_url": linkedin_xray_url,
                    "country": "DO",
                    "currency": "DOP",
                    "contract_val_dop": contract_val,
                    "contract_val_display": f"${contract_val:,.0f} DOP",
                    "contract_entity": entity,
                    "contract_object": c_desc[:120] + ("..." if len(c_desc) > 120 else ""),
                    "data_source": "DGCP_DOMINICAN_REPUBLIC_REGISTRY",
                }

                candidates.append(lead)
                if len(candidates) >= limit:
                    break

        return candidates
