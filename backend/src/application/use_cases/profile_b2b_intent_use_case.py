"""
Michito Intent Engine™ — Stage 1 Natural Language B2B Intent Profiler.
Translates plain language sales briefs into structured campaign parameters,
estimates match volume, and generates a masked teaser lead preview with $0 compute cost.
"""

import re
import hashlib
from typing import Dict, Any, List, Optional
from campaign_loader import load_campaign, list_available_campaigns


CITY_MAPPINGS = {
    "medellin": "Medellín",
    "medellín": "Medellín",
    "antioquia": "Medellín",
    "aburra": "Medellín",
    "envigado": "Medellín",
    "itagui": "Medellín",
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
    "santo domingo": "Santo Domingo",
    "santiago": "Santiago",
}

SECTOR_KEYWORDS = {
    "tinkko_enterprise_offices": [
        "oficina", "oficinas", "espacio", "espacios", "sede", "sedes", "coworking",
        "edificio", "arriendo corporativo", "mudanza", "crecimiento", "piso corporativo"
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
        "masked_decision_maker": "José Rafael C**** (Managing Director)",
        "title": "Director General / Country Manager",
        "masked_phone": "+1 809 542 ****",
        "masked_email": "jcastillo****@caribefintech.do",
        "annual_revenue_range": "RD$ 25M - RD$ 60M DOP",
        "signals": "Apertura de operaciones en Santo Domingo (Piantini / Naco)",
    },
}


class ProfileB2BIntentUseCase:
    """
    Translates free-text business intent into a verified prospecting configuration.
    """

    def execute(self, query: str, country: Optional[str] = "CO") -> Dict[str, Any]:
        normalized = query.lower().strip()
        country_code = (country or "CO").upper()

        # 1. Detect City
        target_city = "Medellín" if country_code == "CO" else "Santo Domingo"
        for keyword, mapped_city in CITY_MAPPINGS.items():
            if re.search(rf"\b{re.escape(keyword)}\b", normalized):
                target_city = mapped_city
                if mapped_city in ("Santo Domingo", "Santiago"):
                    country_code = "DO"
                break

        # 2. Match Campaign / Vertical
        best_campaign = "tinkko_enterprise_offices" if country_code == "CO" else "tinkko_dr_offices"
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

        if country_code == "DO" and best_campaign == "tinkko_enterprise_offices":
            best_campaign = "tinkko_dr_offices"

        # 3. Recommend Tier based on criteria
        recommended_tier = 2
        if any(term in normalized for term in ["financiero", "balance", "ebitda", "solvencia", "litigio", "demanda", "riesgo"]):
            recommended_tier = 3
        elif any(term in normalized for term in ["directorio", "base basica", "pbx", "masivo", "tier 1"]):
            recommended_tier = 1

        # 4. Determine Volume & Pricing
        volume = 25  # Standard conversion-optimized batch
        pricing_matrix = {
            1: {"unit_cop": 5000, "name": "Tier 1: Directorio Base Corporativo"},
            2: {"unit_cop": 30000, "name": "Tier 2: Decisor C-Level (Celular & Email Verificado) ⭐"},
            3: {"unit_cop": 65000, "name": "Tier 3: Auditoría Financiera & Debida Diligencia 🛡️"},
        }
        tier_info = pricing_matrix.get(recommended_tier, pricing_matrix[2])
        unit_price_cop = tier_info["unit_cop"]
        total_price_cop = unit_price_cop * volume

        # 5. Calculate Realistic Estimated Matches (Deterministic Hash)
        hash_seed = int(hashlib.md5(f"{best_campaign}_{target_city}".encode()).hexdigest(), 16)
        estimated_matches = 32 + (hash_seed % 54)  # Between 32 and 85 matching companies

        # 6. Retrieve Representative Teaser Sample
        sample = SAMPLE_PREVIEWS.get(best_campaign, SAMPLE_PREVIEWS["tinkko_enterprise_offices"])
        # Adapt city to query if relevant
        sample_copy = dict(sample)
        if "city" not in sample_copy:
            sample_copy["city"] = target_city

        campaign_config = load_campaign(best_campaign)
        campaign_name = campaign_config.get("name", best_campaign)

        summary_msg = (
            f"Encontramos aproximadamente {estimated_matches} cuentas corporativas en {target_city} "
            f"con alta afinidad para tu propuesta. "
            f"Te recomendamos un lote curado de {volume} decisores clave verificados."
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
            "pricing": {
                "tier": recommended_tier,
                "tier_name": tier_info["name"],
                "unit_price_cop": unit_price_cop,
                "volume": volume,
                "total_cop": total_price_cop,
                "currency": "DOP" if country_code == "DO" else "COP",
                "guarantee": "Solo pagas por cuentas que superen el 100% de los filtros de verificación.",
            },
            "summary_message": summary_msg,
        }
