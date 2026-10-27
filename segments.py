"""
Colombian Enterprise Business Segments Definition
Based on Decreto 957 de 2019 (MinCIT / DANE / Supersociedades)
"""

from typing import Dict, Any, List

SEGMENTS: Dict[str, Dict[str, Any]] = {
    "enterprise": {
        "id": "enterprise",
        "name_es": "Grandes Empresas",
        "name_en": "Large Enterprise",
        "estimated_count_colombia": 9500,
        "revenue_range_cop": "> $65.000M COP",
        "revenue_min_cop": 65000000000,
        "revenue_max_cop": float("inf"),
        "employees_range": "> 200 empleados",
        "employees_min": 200,
        "sweet_spot_rating": "High (Strategic Accounts / ERP Integrations)",
        "typical_stack": "SAP / Oracle / Odoo Enterprise",
        "hebi_fit": "High Ley 2300 legal liability, 200+ vendor compliance audits, multi-campus facility maintenance.",
        "chiketto_fit": "High-volume DIAN electronic invoicing & custom subscription workflows."
    },
    "midmarket": {
        "id": "midmarket",
        "name_es": "Medianas Empresas",
        "name_en": "Mid-Market Enterprise",
        "estimated_count_colombia": 38000,
        "revenue_range_cop": "$10.000M - $65.000M COP",
        "revenue_min_cop": 10000000000,
        "revenue_max_cop": 65000000000,
        "employees_range": "50 - 200 empleados",
        "employees_min": 50,
        "employees_max": 200,
        "sweet_spot_rating": "🎯 SWEET SPOT (Immediate ICP for Hebi)",
        "typical_stack": "Odoo / Siigo / Excel / Google Drive",
        "hebi_fit": "1-2 people drowning in manual WhatsApp/Excel collection, 50-100 recurring vendors needing RUT/PILA, 2-10 commercial sedes.",
        "chiketto_fit": "Automated recurring subscription invoicing replacing manual DIAN portal generation."
    },
    "small": {
        "id": "small",
        "name_es": "Pequeñas Empresas Formales",
        "name_en": "Small Formal Business",
        "estimated_count_colombia": 125000,
        "revenue_range_cop": "$2.000M - $10.000M COP",
        "revenue_min_cop": 2000000000,
        "revenue_max_cop": 10000000000,
        "employees_range": "15 - 50 empleados",
        "employees_min": 15,
        "employees_max": 50,
        "sweet_spot_rating": "Fast Conversion (Low Friction)",
        "typical_stack": "Excel / Siigo Nube / Alegra",
        "hebi_fit": "Instant Excel drop-in to organize late receivables & eliminate manual phone calls.",
        "chiketto_fit": "Ideal entry-level DIAN automated electronic billing & Wompi integration."
    },
    "micro": {
        "id": "micro",
        "name_es": "Microempresas Formales",
        "name_en": "Formal Micro-Businesses",
        "estimated_count_colombia": 237000,
        "revenue_range_cop": "< $2.000M COP",
        "revenue_min_cop": 0,
        "revenue_max_cop": 2000000000,
        "employees_range": "1 - 10 empleados",
        "employees_min": 1,
        "employees_max": 10,
        "sweet_spot_rating": "Self-Serve (Freemium / Invoicing Only)",
        "typical_stack": "WhatsApp / Excel / Facturador Gratuito DIAN",
        "hebi_fit": "Self-service 1-click collection link generation.",
        "chiketto_fit": "1-click automated electronic billing directly to DIAN."
    }
}

def get_segment_info(segment_id: str) -> Dict[str, Any]:
    return SEGMENTS.get(segment_id.lower(), SEGMENTS["midmarket"])

def list_supported_segments() -> List[str]:
    return list(SEGMENTS.keys()) + ["all"]
