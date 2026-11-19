"""
Michito Intent Engine™ — Stage 1 Natural Language B2B Intent Profiler.
Translates plain language sales briefs into structured campaign parameters,
estimates match volume, and generates a masked teaser lead preview with $0 compute cost.
"""

import re
import hashlib
from typing import Dict, Any, List, Optional
from campaign_loader import load_campaign, list_available_campaigns
from src.application.services.brief_parser_service import BriefParserService


CITY_MAPPINGS = {
    "medellin": "Medellín",
    "medellín": "Medellín",
    "antioquia": "Medellín",
    "aburra": "Medellín",
    "envigado": "Envigado",
    "itagui": "Itagüí",
    "bogota": "Bogotá",
    "bogotá": "Bogotá",
    "cundinamarca": "Bogotá",
    "cali": "Cali",
    "valle": "Cali",
    "barranquilla": "Barranquilla",
    "atlantico": "Barranquilla",
    "atlántico": "Barranquilla",
    "bucaramanga": "Bucaramanga",
    "santander": "Bucaramanga",
    "cartagena": "Cartagena",
    "bolivar": "Cartagena",
    "bolívar": "Cartagena",
    "pereira": "Pereira",
    "manizales": "Manizales",
    "republica dominicana": "Santo Domingo",
    "república dominicana": "Santo Domingo",
    "dominicana": "Santo Domingo",
    "santo domingo": "Santo Domingo",
    "santiago de los caballeros": "Santiago",
    "santiago": "Santiago",
    "punta cana": "Punta Cana",
    "ecuador": "Quito",
    "quito": "Quito",
    "guayaquil": "Guayaquil",
    "cuenca": "Cuenca",
}

SECTOR_KEYWORDS = {
    "tinkko_enterprise_offices": [
        "oficina", "oficinas", "espacio", "espacios", "sede", "sedes", "coworking",
        "edificio", "arriendo corporativo", "mudanza", "crecimiento", "piso corporativo"
    ],
    "tinkko_dr_offices": [
        "republica dominicana", "república dominicana", "dominicana", "santo domingo", "santiago",
        "caribe", "oficinas rd", "b2b dominicana", "punta cana"
    ],
    "tinkko_ec_offices": [
        "ecuador", "quito", "guayaquil", "cuenca", "pichincha", "guayas",
        "oficinas ecuador", "b2b ecuador"
    ],
    "eventos_ferias_b2b": [
        "feria", "ferias", "evento", "eventos", "expositor", "expositores", "stand",
        "mision", "misión", "plaza mayor", "corferias", "comprador", "compradores",
        "rueda de negocios", "congreso"
    ],
    "hebi": [
        "cartera", "cobro", "deuda", "deudores", "factura por cobrar", "riesgo",
        "debida diligencia", "contratista", "contratistas", "litigio", "demanda",
        "insolvencia", "morosidad"
    ],
    "chiketto": [
        "software", "erp", "crm", "factura electronica", "facturación", "dian",
        "api", "apis", "tecnologia", "tecnología", "saas", "desarrollo", "cloud",
        "automatizacion", "automatización", "contable", "contabilidad"
    ],
    "chiketto_school_ids": [
        "colegio", "colegios", "escuela", "escuelas", "carnet", "carnets", "carnetizacion",
        "carnetización", "zebra", "credencial", "credenciales", "estudiantil", "estudiantiles",
        "rector", "rectora", "rectoria", "rectoría", "pvc", "liceo", "gimnasio escolar",
        "identificacion escolar", "identificaciones escolares", "impresora zebra"
    ],
    "blueoil": [
        "combustible", "combustibles", "gasolina", "diesel", "acpm", "lubricante",
        "lubricantes", "flota", "flotas", "camiones", "transporte pesado", "estacion"
    ],
    "facility_services_b2b": [
        "aseo", "limpieza", "seguridad", "vigilancia", "facility", "mantenimiento",
        "desinfección", "porteria", "portería", "guardas", "conserjeria"
    ],
    "warehouse_aburra_norte": [
        "bodega", "bodegas", "parque industrial", "logistica", "logística", "almacen",
        "almacén", "centro de distribucion", "cedi", "lote", "terreno industrial"
    ],
    "tinkko_dr_offices": [
        "republica dominicana", "república dominicana", "santo domingo", "santiago",
        "caribe", "oficinas rd", "b2b dominicana"
    ],
}

SAMPLE_PREVIEWS = {
    "tinkko_enterprise_offices": {
        "company_name": "Inversiones & Consultoría Andina S.A.S.",
        "masked_nit": "901.482.***-1",
        "masked_decision_maker": "Carlos Andrés M**** (Gerente General)",
        "title": "Gerente General / Director de Operaciones",
        "masked_phone": "+57 300 842 ****",
        "masked_email": "c.mejia****@andina-consulting.co",
        "annual_revenue_range": "$3.500M - $8.000M COP",
        "signals": "Crecimiento de nómina en Cámara de Comercio + Apertura de sede reciente",
    },
    "eventos_ferias_b2b": {
        "company_name": "Agroindustrias & Alimentos del Valle S.A.S.",
        "masked_nit": "900.912.***-4",
        "masked_decision_maker": "Marcela R**** (Directora Comercial & Exportaciones)",
        "title": "Directora Comercial & Mercadeo",
        "masked_phone": "+57 315 729 ****",
        "masked_email": "exportaciones****@agrovalle.com.co",
        "annual_revenue_range": "$12.000M - $25.000M COP",
        "signals": "Expositor frecuente en ruedas de negocios internacionales y misiones comerciales",
    },
    "hebi": {
        "company_name": "Construcciones & Pavimentos Metropolitanos S.A.",
        "masked_nit": "890.315.***-8",
        "masked_decision_maker": "Alejandro G**** (Director Financiero CFO)",
        "title": "CFO / Director Administrativo y Financiero",
        "masked_phone": "+57 310 405 ****",
        "masked_email": "agomez****@pavimentosmetro.co",
        "annual_revenue_range": "$18.000M - $40.000M COP",
        "signals": "Contratos activos con el Estado (SECOP) + Requiere validación de solvencia de subcontratistas",
    },
    "chiketto": {
        "company_name": "Soluciones Integrales de Salud IPS S.A.S.",
        "masked_nit": "901.129.***-3",
        "masked_decision_maker": "Valeria H**** (Líder de TI & Transformación Digital)",
        "title": "Líder de Sistemas & Facturación Electrónica",
        "masked_phone": "+57 320 631 ****",
        "masked_email": "valeria.h****@saludintegralips.com",
        "annual_revenue_range": "$5.000M - $14.000M COP",
        "signals": "Obligado DIAN a facturación electrónica masiva + Software ERP en proceso de modernización",
    },
    "chiketto_school_ids": {
        "company_name": "Colegio San José de las Vegas",
        "masked_nit": "890.901.***-5",
        "masked_decision_maker": "Gloria F**** (Rectora / Directora General)",
        "title": "Rector / Rectora de Institución Educativa",
        "masked_phone": "+57 312 345 ****",
        "masked_email": "rectoria****@sanjosevegas.edu.co",
        "annual_revenue_range": "$8.000M - $18.000M COP",
        "signals": "Institución Educativa con más de 1.200 estudiantes + Renovación anual de carnets PVC",
    },
    "blueoil": {
        "company_name": "Transportes & Carga del Magdalena S.A.S.",
        "masked_nit": "860.291.***-0",
        "masked_decision_maker": "Jorge Eduardo P**** (Gerente de Flota & Mantenimiento)",
        "title": "Gerente de Flota y Logística de Distribución",
        "masked_phone": "+57 311 902 ****",
        "masked_email": "jorge.p****@transportesmagdalena.com",
        "annual_revenue_range": "$22.000M - $50.000M COP",
        "signals": "Flota propia de más de 35 tractomulas con consumo recurrente de ACPM a granel",
    },
    "facility_services_b2b": {
        "company_name": "Almacenes & Distribuciones Élite S.A.S.",
        "masked_nit": "900.751.***-5",
        "masked_decision_maker": "Diana Lucía T**** (Jefe de Compras & Servicios Generales)",
        "title": "Jefe de Compras y Contratación Corporativa",
        "masked_phone": "+57 301 554 ****",
        "masked_email": "diana.t****@distribucioneselite.com.co",
        "annual_revenue_range": "$9.000M - $20.000M COP",
        "signals": "Tres centros logísticos con demanda activa de aseo industrial y vigilancia privada",
    },
    "warehouse_aburra_norte": {
        "company_name": "Logística & Empaques del Norte S.A.S.",
        "masked_nit": "901.034.***-2",
        "masked_decision_maker": "Santiago R**** (Director de Cadena de Suministro)",
        "title": "Director de Supply Chain & Almacenamiento",
        "masked_phone": "+57 314 883 ****",
        "masked_email": "santiago.r****@empaquesdelnorte.co",
        "annual_revenue_range": "$14.000M - $30.000M COP",
        "signals": "Buscando ampliación de más de 1.500 m² en corredor industrial",
    },
    "tinkko_dr_offices": {
        "company_name": "Servicios Financieros & Fintech del Caribe S.R.L.",
        "masked_nit": "RNC 131.849.***",
        "statutory_badge": "✓ RNC Vigente en DGII / Cámara de Comercio",
        "masked_decision_maker": "José Rafael C**** (Managing Director)",
        "title": "Director General / Country Manager",
        "masked_phone": "+1 809 542 ****",
        "masked_email": "jcastillo****@caribefintech.do",
        "annual_revenue_range": "RD$ 25M - RD$ 60M DOP",
        "signals": "Apertura de operaciones en Santo Domingo (Piantini / Naco)",
    },
    "tinkko_ec_offices": {
        "company_name": "Soluciones Corporativas del Pacífico Cía. Ltda.",
        "masked_nit": "RUC 179248****",
        "statutory_badge": "✓ RUC Vigente en SRI",
        "masked_decision_maker": "Esteban R**** (Gerente General)",
        "title": "Gerente General / Director de Operaciones",
        "masked_phone": "+593 99 482 ****",
        "masked_email": "e.reyes****@pacificocorporativo.ec",
        "annual_revenue_range": "$1.200M - $3.500M USD",
        "signals": "Expansión comercial en Quito (La Carolina / Iñaquito)",
    },
}


class ProfileB2BIntentUseCase:
    """
    Translates free-text business intent into a verified prospecting configuration.
    """

    def __init__(self, brief_parser: Optional[BriefParserService] = None):
        self.brief_parser = brief_parser or BriefParserService()

    def execute(self, query: str, country: Optional[str] = "CO") -> Dict[str, Any]:
        normalized = query.lower().strip()
        default_country = (country or "CO").upper()

        # Parse universal intent parameters via BriefParserService
        parsed_super_query = self.brief_parser.parse_brief(query)

        # 1. Detect Country and City directly from parsed_super_query first, with fallback to query text
        detected_locs = parsed_super_query.get("locations") or []
        if detected_locs:
            primary_loc = detected_locs[0]
            country_code = (primary_loc.get("country") or default_country).upper()
            target_city = primary_loc.get("city") or primary_loc.get("region") or ("Santo Domingo" if country_code == "DO" else "Quito" if country_code == "EC" else "Medellín")
        else:
            primary_token_country = parsed_super_query.get("discovered_tokens", {}).get("primary_country")
            country_code = primary_token_country.upper() if primary_token_country else default_country
            target_city = "Medellín" if country_code == "CO" else "Santo Domingo" if country_code == "DO" else "Quito"
            for keyword, mapped_city in CITY_MAPPINGS.items():
                if re.search(rf"\b{re.escape(keyword)}\b", normalized):
                    target_city = mapped_city
                    if mapped_city in ("Santo Domingo", "Santiago", "Punta Cana"):
                        country_code = "DO"
                    elif mapped_city in ("Quito", "Guayaquil", "Cuenca"):
                        country_code = "EC"
                    break

        # 2. Match Campaign / Vertical with Multi-Country Awareness
        best_campaign = "tinkko_enterprise_offices" if country_code == "CO" else "tinkko_dr_offices" if country_code == "DO" else "tinkko_ec_offices"
        highest_score = 0
        matched_keywords = []

        for campaign_id, keywords in SECTOR_KEYWORDS.items():
            score = 0
            current_matched = []
            for kw in keywords:
                if kw in normalized:
                    score += 1
                    current_matched.append(kw)
            if score > highest_score:
                highest_score = score
                best_campaign = campaign_id
                matched_keywords = current_matched

        if country_code == "DO":
            if best_campaign in ("tinkko_enterprise_offices", "tinkko_dr_offices") or any(k in normalized for k in ["oficina", "oficinas", "coworking", "espacio", "sede"]):
                best_campaign = "tinkko_dr_offices"
        elif country_code == "EC":
            if best_campaign in ("tinkko_enterprise_offices", "tinkko_ec_offices") or any(k in normalized for k in ["oficina", "oficinas", "coworking", "espacio", "sede"]):
                best_campaign = "tinkko_ec_offices"

        # 3. Recommend Tier
        recommended_tier = parsed_super_query.get("tier") or 2
        if any(w in normalized for w in ("auditoria", "auditoría", "niif", "balance", "solvencia", "legal", "diligencia")):
            recommended_tier = 3

        # 4. Volume (Honor explicit volume from parsed query or regex)
        volume = parsed_super_query.get("limit") or 25
        vol_match = re.search(r"\b(10|25|50|100|150|200|300|500)\s*(?:colegios|empresas|cuentas|leads|prospectos|contactos)?\b", normalized)
        if vol_match:
            try:
                volume = int(vol_match.group(1))
            except Exception:
                pass

        # Financial Model Pricing in Local Currency
        target_currency = "USD" if country_code in ("MULTI", "EC") else ("DOP" if country_code == "DO" else "COP")
        from src.entrypoints.workers.order_worker_daemon import calculate_lead_pricing
        total_cents = calculate_lead_pricing(volume, tier=recommended_tier, currency=target_currency)
        total_price = total_cents / 100.0
        unit_price = total_price / max(1, volume)

        tier_names = {
            1: "Tier 1: Directorio Base Corporativo",
            2: "Tier 2: Decisor C-Level (Celular & Email Verificado) ⭐",
            3: "Tier 3: Auditoría Financiera & Debida Diligencia 🛡️",
        }

        # 5. Exact Requested Batch (Truth in Advertising - No Synthetic Multipliers)
        estimated_matches = volume

        # 6. Retrieve Representative Teaser Sample
        sample = SAMPLE_PREVIEWS.get(best_campaign) or SAMPLE_PREVIEWS.get("tinkko_dr_offices" if country_code == "DO" else "tinkko_ec_offices" if country_code == "EC" else "tinkko_enterprise_offices") or {}
        sample_copy = dict(sample)
        if "city" not in sample_copy:
            sample_copy["city"] = target_city

        campaign_config = load_campaign(best_campaign) if best_campaign else {}
        campaign_name = campaign_config.get("name", best_campaign)

        summary_msg = (
            f"Configuramos tu lote en {volume} decisores clave verificados en {target_city} "
            f"con alta afinidad para tu propuesta."
        )

        return {
            "status": "success",
            "query": query,
            "campaign_id": best_campaign,
            "campaign_name": campaign_name,
            "country": country_code,
            "city": target_city,
            "recommended_tier": recommended_tier,
            "recommended_limit": volume,
            "estimated_matches": estimated_matches,
            "matched_keywords": matched_keywords,
            "sample_preview": sample_copy,
            "directionality": parsed_super_query.get("directionality", "vendor_to_clients"),
            "sectors": parsed_super_query.get("sectors", []),
            "ciiu_codes": parsed_super_query.get("ciiu_codes", []),
            "roles": parsed_super_query.get("roles", []),
            "locations": parsed_super_query.get("locations", []),
            "rfq_specifications": parsed_super_query.get("rfq_specifications"),
            "keywords_include": parsed_super_query.get("keywords_include", []),
            "keywords_exclude": parsed_super_query.get("keywords_exclude", []),
            "query_id": parsed_super_query.get("query_id"),
            "pricing": {
                "tier": recommended_tier,
                "tier_name": tier_names.get(recommended_tier, tier_names[2]),
                "unit_price": unit_price,
                "unit_price_cop": int(unit_price),
                "volume": volume,
                "total_amount": total_price,
                "total_cop": total_price,
                "currency": target_currency,
                "guarantee": "Solo pagas por cuentas que superen el 100% de los filtros de verificación.",
            },
            "summary_message": summary_msg,
        }

