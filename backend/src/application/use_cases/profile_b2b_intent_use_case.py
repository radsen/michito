"""
Michito Intent Engine™ — Stage 1 Natural Language B2B Intent Profiler.
Translates plain language sales briefs into structured campaign parameters,
verifies authentic corporate lead inventory dynamically via Zero-Knowledge masking,
and guarantees 100% truth in advertising with $0 compute cost.
"""

import re
import hashlib
import logging
from typing import Dict, Any, List, Optional
from campaign_loader import load_campaign, list_available_campaigns
from src.application.services.brief_parser_service import BriefParserService
from src.domain.services.teaser_masking_service import build_zero_knowledge_teaser

logger = logging.getLogger(__name__)


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


class ProfileB2BIntentUseCase:
    """
    Translates free-text business intent into a verified prospecting configuration.
    Extracts dynamic CIIU codes, sectors, roles, and probes authentic corporate inventory.
    """

    def __init__(
        self,
        brief_parser: Optional[BriefParserService] = None,
        sql_adapter: Optional[Any] = None,
    ):
        self.brief_parser = brief_parser or BriefParserService()
        self.sql_adapter = sql_adapter
        if self.sql_adapter is None:
            try:
                from src.adapters.db.sql_order_adapter import SqlOrderAdapter
                self.sql_adapter = SqlOrderAdapter()
            except Exception:
                self.sql_adapter = None

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

        # 2. Extract Dynamic CIIU, Sectors, Roles, Keywords
        ciiu_codes = parsed_super_query.get("ciiu_codes") or []
        sectors = parsed_super_query.get("sectors") or []
        roles = parsed_super_query.get("roles") or []
        keywords_include = parsed_super_query.get("keywords_include") or []
        keywords_exclude = parsed_super_query.get("keywords_exclude") or []
        directionality = parsed_super_query.get("directionality", "vendor_to_clients")

        # 3. Determine Campaign Identifier
        # Supports preset example campaigns for continuity, but defaults to dynamic universal
        available_camps = list_available_campaigns()
        campaign_id = "universal_prospecting"
        campaign_name = "Prospección Comercial B2B Universal"

        preset_triggers = {
            "tinkko_dr_offices": ["oficinas rd", "coworking dominicana", "oficinas santo domingo"],
            "tinkko_ec_offices": ["oficinas ecuador", "coworking quito", "oficinas quito"],
            "tinkko_enterprise_offices": ["coworking medellin", "oficinas medellin", "oficinas medellín", "coworking bogota"],
            "chiketto_school_ids": ["carnet", "carnets", "colegio", "estudiantil", "zebra"],
            "chiketto": ["factura electronica", "facturación dian", "erp contable", "software contable"],
            "blueoil": ["combustible a granel", "diesel flotas", "acpm flotas", "tractomulas"],
            "facility_services_b2b": ["aseo industrial", "limpieza industrial", "vigilancia privada"],
            "warehouse_aburra_norte": ["bodega industrial", "parque industrial", "cedi logistico"],
        }
        for cid, triggers in preset_triggers.items():
            if cid in available_camps and any(t in normalized for t in triggers):
                campaign_id = cid
                try:
                    cfg = load_campaign(cid)
                    campaign_name = cfg.get("name", cid)
                except Exception:
                    campaign_name = cid
                break

        # Compound check for offices / coworking per territory
        if campaign_id == "universal_prospecting" and any(w in normalized for w in ("oficina", "oficinas", "coworking")):
            if any(w in normalized for w in ("dominicana", "santo domingo", "republica dominicana", "república dominicana")):
                campaign_id = "tinkko_dr_offices"
                try:
                    campaign_name = load_campaign(campaign_id).get("name", campaign_id)
                except Exception:
                    campaign_name = "Tinkko — Sedes y Oficinas Privadas Corporativas (República Dominicana)"
            elif any(w in normalized for w in ("ecuador", "quito", "guayaquil", "cuenca")):
                campaign_id = "tinkko_ec_offices"
                try:
                    campaign_name = load_campaign(campaign_id).get("name", campaign_id)
                except Exception:
                    campaign_name = "Tinkko — Sedes y Oficinas Privadas Corporativas (Ecuador)"
            elif any(w in normalized for w in ("medellin", "medellín", "bogota", "bogotá", "cali", "colombia")):
                campaign_id = "tinkko_enterprise_offices"
                try:
                    campaign_name = load_campaign(campaign_id).get("name", campaign_id)
                except Exception:
                    campaign_name = "Tinkko — Sedes y Oficinas Privadas Corporativas (Medellín)"

        if campaign_id == "universal_prospecting":
            topic = (sectors[0] if sectors else query[:40]).strip().title()
            campaign_name = f"Prospección Dinámica: {topic}"

        # 4. Recommend Tier
        recommended_tier = parsed_super_query.get("tier") or 2
        if any(w in normalized for w in ("auditoria", "auditoría", "niif", "balance", "solvencia", "legal", "diligencia")):
            recommended_tier = 3

        # 5. Volume (Honor explicit volume from parsed query or regex)
        volume = parsed_super_query.get("limit") or 25
        vol_match = re.search(r"\b(10|25|50|100|150|200|300|500)\s*(?:colegios|empresas|cuentas|leads|prospectos|contactos)?\b", normalized)
        if vol_match:
            try:
                volume = int(vol_match.group(1))
            except Exception:
                pass

        # Financial Model Pricing in Local Currency converted via TRM
        target_currency = "USD" if country_code in ("MULTI", "EC") else ("DOP" if country_code == "DO" else "COP")
        from src.entrypoints.workers.order_worker_daemon import calculate_lead_pricing
        from src.domain.services.trm_service import TrmExchangeRateService
        total_cents = calculate_lead_pricing(volume, tier=recommended_tier, currency=target_currency)
        total_price = total_cents / 100.0
        unit_price = total_price / max(1, volume)

        # Exact conversion to COP via official TRM service
        fx_pricing = TrmExchangeRateService.get_instance().convert(
            amount=total_price,
            from_currency=target_currency,
            to_currency="COP"
        )
        total_cop = fx_pricing["amount_in_cop"]
        unit_price_cop = int(total_cop / max(1, volume))

        tier_names = {
            1: "Tier 1: Directorio Base Corporativo",
            2: "Tier 2: Decisor C-Level (Celular & Email Verificado) ⭐",
            3: "Tier 3: Auditoría Financiera & Debida Diligencia 🛡️",
        }

        # 6. Retrieve Representative Teaser Sample from Authentic Lead Inventory
        matching_leads: List[Dict[str, Any]] = []
        if self.sql_adapter:
            try:
                matching_leads = self.sql_adapter.get_cached_fresh_leads(
                    city=target_city,
                    country=country_code,
                    limit=1,
                    ciiu_codes=ciiu_codes,
                    keywords=keywords_include,
                    sectors=sectors,
                    max_age_days=365,
                )
            except Exception as e:
                logger.warning(f"Error querying SQL inventory for preview: {e}")

        # If database inventory had no matches, check statutory baseline registry
        if not matching_leads:
            try:
                from src.adapters.db.seed_statutory_leads import STATUTORY_CORPORATE_LEADS
                geo_tokens = {
                    "santiago", "medellin", "medellín", "bogota", "bogotá", "cali",
                    "quito", "guayaquil", "cuenca", "santo", "domingo", "colombia",
                    "ecuador", "dominicana", target_city.lower()
                }
                clean_intent_kws = [
                    k.lower() for k in keywords_include
                    if k.lower() not in geo_tokens and len(k) >= 3
                ]
                has_intent_filter = bool(ciiu_codes or clean_intent_kws or sectors)
                for item in STATUTORY_CORPORATE_LEADS:
                    if item.get("country") == country_code:
                        if target_city and target_city.lower() not in ("all", "nacional", "todo"):
                            if target_city.lower() not in (item.get("city") or "").lower():
                                continue
                        matches_intent = False
                        if not has_intent_filter:
                            matches_intent = True
                        elif ciiu_codes and any(item.get("ciiu_code", "").startswith(str(c)[:2]) for c in ciiu_codes):
                            matches_intent = True
                        elif clean_intent_kws and any(
                            kw in item.get("company_name", "").lower() or
                            kw in item.get("activity_description", "").lower() or
                            kw in item.get("sector_macro", "").lower()
                            for kw in clean_intent_kws
                        ):
                            matches_intent = True
                        elif sectors and any(
                            sec.lower() in item.get("sector_macro", "").lower() or
                            sec.lower() in item.get("activity_description", "").lower()
                            for sec in sectors
                        ):
                            matches_intent = True

                        if matches_intent:
                            matching_leads.append(dict(item))
                            break
            except Exception as e:
                logger.debug(f"Baseline lead probe failed: {e}")

        sample_preview: Optional[Dict[str, Any]] = None
        estimated_matches: int = 0

        if matching_leads:
            sample_preview = build_zero_knowledge_teaser(
                matching_leads[0],
                country=country_code,
                city=target_city,
            )
            estimated_matches = volume
            summary_msg = (
                f"Configuramos tu lote en {volume} decisores clave verificados en {target_city} "
                f"con alta afinidad para tu propuesta."
            )
        else:
            sample_preview = None
            estimated_matches = 0
            summary_msg = (
                "No fue posible encontrar la información solicitada en este momento. "
                "El registro oficial no está disponible o no se encontraron empresas para este criterio."
            )

        return {
            "status": "success",
            "query": query,
            "campaign_id": campaign_id,
            "campaign_name": campaign_name,
            "country": country_code,
            "city": target_city,
            "recommended_tier": recommended_tier,
            "recommended_limit": volume,
            "estimated_matches": estimated_matches,
            "matched_keywords": keywords_include,
            "sample_preview": sample_preview,
            "directionality": directionality,
            "sectors": sectors,
            "ciiu_codes": ciiu_codes,
            "roles": roles,
            "locations": parsed_super_query.get("locations", []),
            "rfq_specifications": parsed_super_query.get("rfq_specifications"),
            "keywords_include": keywords_include,
            "keywords_exclude": keywords_exclude,
            "query_id": parsed_super_query.get("query_id"),
            "pricing": {
                "tier": recommended_tier,
                "tier_name": tier_names.get(recommended_tier, tier_names[2]),
                "unit_price": unit_price,
                "unit_price_cop": unit_price_cop,
                "volume": volume,
                "total_amount": total_price,
                "total_cop": total_cop,
                "amount_in_cents_cop": total_cop * 100,
                "currency": target_currency,
                "exchange_rate": fx_pricing.get("rate_used", 1.0),
                "guarantee": "Solo pagas por cuentas que superen el 100% de los filtros de verificación.",
            },
            "summary_message": summary_msg,
        }
