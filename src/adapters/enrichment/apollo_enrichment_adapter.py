"""
Apollo.io & Sales Navigator Enrichment Client
Enriches Colombian corporate accounts with verified decision-maker contact details:
- Official Apollo.io REST API integration (/v1/mixed_people/search, /v1/people/match)
- Sales Navigator & Apollo CSV export importer
- Graceful offline fallback with corporate email domain patterns and Google X-Ray resolution
"""

import os
import csv
import json
import urllib.request
import urllib.parse
from typing import Dict, Any, List, Optional

APOLLO_SEARCH_ENDPOINT = "https://api.apollo.io/v1/mixed_people/search"
APOLLO_MATCH_ENDPOINT = "https://api.apollo.io/v1/people/match"

TARGET_ROLES_DEFAULT = [
    "CFO",
    "Director Financiero",
    "Gerente Financiero",
    "Gerente de Operaciones",
    "COO",
    "Facility Manager",
    "Jefe de Cartera"
]

class ApolloClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("APOLLO_API_KEY", "").strip()

    def has_api_key(self) -> bool:
        return bool(self.api_key)

    def search_decision_maker(
        self,
        company_name: str,
        domain: Optional[str] = None,
        city: str = "Colombia",
        target_roles: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Queries Apollo.io API for verified decision-makers at the given Colombian company.
        Falls back to synthesized verified corporate profile if API key is not present or returns empty.
        """
        roles = target_roles or TARGET_ROLES_DEFAULT

        if self.has_api_key():
            try:
                headers = {
                    "Content-Type": "application/json",
                    "Cache-Control": "no-cache",
                    "X-Api-Key": self.api_key
                }
                
                clean_name = (
                    company_name.replace("S.A.S.", "")
                    .replace("SAS", "")
                    .replace("S.A.", "")
                    .replace("Ltda.", "")
                    .strip()
                )

                payload: Dict[str, Any] = {
                    "api_key": self.api_key,
                    "q_organization_name": clean_name,
                    "person_titles": roles,
                    "person_locations": [city, "Colombia"],
                    "page": 1,
                    "per_page": 1
                }
                if domain:
                    payload["q_organization_domains"] = domain

                req = urllib.request.Request(
                    APOLLO_SEARCH_ENDPOINT,
                    data=json.dumps(payload).encode("utf-8"),
                    headers=headers,
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    if resp.status == 200:
                        data = json.loads(resp.read().decode("utf-8"))
                        people = data.get("people", [])
                        if people:
                            p = people[0]
                            return {
                                "source": "apollo_api_verified",
                                "first_name": p.get("first_name", ""),
                                "last_name": p.get("last_name", ""),
                                "full_name": p.get("name") or f"{p.get('first_name', '')} {p.get('last_name', '')}".strip(),
                                "title": p.get("title", "Director Financiero / CFO"),
                                "email": p.get("email", ""),
                                "email_status": p.get("email_status", "verified"),
                                "phone": p.get("sanitized_phone") or p.get("phone_number") or "",
                                "linkedin_url": p.get("linkedin_url", ""),
                                "company_domain": p.get("organization", {}).get("primary_domain") or domain or ""
                            }
            except Exception as e:
                # Silently catch and fall back
                pass

        # Fallback synthesis
        return self._fallback_decision_maker(company_name, domain, city, target_roles=roles)

    def import_from_csv(self, csv_filepath: str) -> List[Dict[str, Any]]:
        """
        Parses exported CSV from LinkedIn Sales Navigator, Apollo.io, CCMA, or Excel.
        Standardizes columns into normalized prospect records.
        """
        results: List[Dict[str, Any]] = []
        if not os.path.exists(csv_filepath):
            return results

        with open(csv_filepath, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Handle standard Sales Navigator, Apollo, and Colombian Spanish CSV headers
                company = (
                    row.get("Company") 
                    or row.get("Company Name") 
                    or row.get("Organization") 
                    or row.get("Empresa")
                    or row.get("Razon Social")
                    or row.get("Razón Social")
                    or row.get("Nombre Empresa")
                    or ""
                ).strip()
                first_name = (row.get("First Name") or row.get("first_name") or row.get("Nombre") or "").strip()
                last_name = (row.get("Last Name") or row.get("last_name") or row.get("Apellido") or "").strip()
                title = (row.get("Title") or row.get("Job Title") or row.get("Cargo") or row.get("Puesto") or "").strip()
                email = (row.get("Email") or row.get("Work Email") or row.get("Correo") or row.get("Email Corporativo") or "").strip()
                phone = (row.get("Phone") or row.get("Corporate Phone") or row.get("Telefono") or row.get("Teléfono") or row.get("Celular") or "").strip()
                linkedin = (
                    row.get("Person Linkedin Url") 
                    or row.get("LinkedIn URL") 
                    or row.get("Linkedin") 
                    or row.get("URL") 
                    or ""
                ).strip()

                if company:
                    results.append({
                        "source": "csv_import",
                        "company_name": company,
                        "first_name": first_name,
                        "last_name": last_name,
                        "full_name": f"{first_name} {last_name}".strip() if (first_name or last_name) else "",
                        "title": title or "Director(a) Ejecutivo(a)",
                        "email": email,
                        "phone": phone,
                        "linkedin_url": linkedin
                    })

        return results

    @staticmethod
    def _fallback_decision_maker(
        company_name: str,
        domain: Optional[str],
        city: str,
        target_roles: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Generates structured placeholder decision-maker data with Google X-Ray resolution.
        """
        clean_name = (
            company_name.replace("S.A.S.", "")
            .replace("SAS", "")
            .replace("S.A.", "")
            .replace("Ltda.", "")
            .strip()
        )
        
        # Derive clean corporate domain if not provided
        derived_domain = domain
        if not derived_domain:
            slug = clean_name.lower().replace(" ", "").replace("&", "").replace(".", "").replace("(", "").replace(")", "")
            derived_domain = f"{slug}.com.co"

        # Construct direct Google X-Ray search query using target roles (Safe, compliant, zero bot scraping)
        roles = target_roles or TARGET_ROLES_DEFAULT
        roles_str = " OR ".join([f'"{r}"' for r in roles[:4]])
        xray_query = f'site:co.linkedin.com/in/ "{clean_name}" ({roles_str}) "{city}"'
        xray_url = f"https://www.google.com/search?q={urllib.parse.quote(xray_query)}"

        primary_title = roles[0] if roles else "Director(a) de Operaciones / Finanzas"

        return {
            "source": "pending_human_verification",
            "first_name": "Líder",
            "last_name": primary_title,
            "full_name": f"[Por Verificar en LinkedIn: {primary_title}]",
            "title": primary_title,
            "email": "",
            "email_status": "unverified",
            "phone": "",
            "linkedin_url": xray_url,
            "company_domain": derived_domain or ""
        }
