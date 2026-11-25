"""
Michito AI Agent Suite — Brief Parser Service.
Translates unstructured natural language business briefs into the Universal Super Query
(UniversalProspectingRequest) with support for directionality (Sales vs Procurement/RFQ),
multi-country geography (CO 🇨🇴, DO 🇩🇴, EC 🇪🇨, LatAm 🌎), dynamic CIIU code resolution,
and seamless fallback between Gemini Flash and the local sub-millisecond BM25 ISIC index.
"""

import os
import re
import json
import logging
from typing import Dict, Any, List, Optional, Tuple

import httpx

from src.domain.taxonomy.isic_index import get_isic_index, IsicEntry

logger = logging.getLogger(__name__)

# Prompt meta-words and Spanish stopwords to purge from search intent
QUERY_STOP_WORDS = {
    # Functional Spanish prepositions & articles
    "para", "con", "por", "que", "los", "las", "una", "uno", "unos", "unas",
    "del", "al", "en", "de", "y", "o", "a", "el", "la", "un", "su", "sus",
    "este", "esta", "estos", "estas", "ese", "esa", "esos", "esas", "como",
    "cual", "cuales", "cuál", "cuáles", "donde", "dónde", "quien", "quién",
    "sobre", "entre", "tras", "hacia", "hasta", "desde", "segun", "según",
    # Imperative / Intent request verbs
    "dame", "dar", "deme", "busca", "buscar", "busco", "buscamos", "consigue",
    "conseguir", "consigan", "necesito", "necesitamos", "quiero", "queremos",
    "solicito", "solicitar", "solicitamos", "pasa", "pasar", "envia", "enviar",
    "obten", "obtener", "obtenga", "trae", "traer", "recomienda", "generar",
    "genera", "crear", "arma", "entregar",
    # Entity & dataset meta-words
    "empresas", "empresa", "prospectos", "prospecto", "clientes", "cliente",
    "proveedores", "proveedor", "cuentas", "cuenta", "leads", "lead",
    "contactos", "contacto", "datos", "base", "bases", "lista", "listas",
    "listado", "registro", "registros", "informacion", "información",
    "directorio", "directorios", "perfil", "perfiles",
    # Commercial model & generic business modifiers (PURGE to avoid polluting domain query)
    "distribuidora", "distribuidor", "distribuidores", "distribuidoras", "distribucion", "distribución",
    "comercializadora", "comercializador", "comercializadoras", "comercializadores", "comercializacion", "comercialización",
    "mayorista", "mayoristas", "mayor", "al por mayor", "minorista", "minoristas", "al detal", "detal",
    "insumo", "insumos", "suministro", "suministros", "abastecimiento",
    "fabricante", "fabricantes", "fabricacion", "fabricación", "manufactura", "manufacturas",
    "importador", "importadores", "importadora", "importadoras", "importacion", "importación",
    "exportador", "exportadores", "exportadora", "exportadoras", "exportacion", "exportación",
    "taller", "talleres", "industria", "industrias", "industrial", "industriales",
    "sociedad", "sociedades", "compania", "compañia", "compañía", "sas", "s.a.s", "ltda",
    "unas", "unos", "otras", "otros", "algunas", "algunos",
    # Field & channel meta-words
    "telefono", "telefonos", "teléfono", "teléfonos", "correo", "correos",
    "email", "emails", "cargo", "cargos", "directivo", "directivos", "celular",
    "celulares", "direccion", "direcciones", "dirección", "pbx",
    "whatsapp", "nombre", "nombres", "apellido", "apellidos", "nit", "ruc", "rnc",
    # Geography meta-words
    "colombia", "ecuador", "dominicana", "medellin", "medellín", "bogota",
    "bogotá", "cali", "barranquilla", "quito", "guayaquil", "santo", "domingo",
    "ciudad", "ciudades", "pais", "país", "nacional", "todo", "toda", "todos", "todas",
    # Generic filler words and polysemic unigrams (purge solitary occurrences to avoid polluting domain query)
    "espacio", "espacios", "servicio", "servicios", "sector", "sectores", "alta", "buena",
    "basico", "básico", "basica", "básica", "tier", "nivel",
    "desarrollo", "soluciones", "gestion", "gestión", "consultoria", "consultoría",
    "actividades", "integral", "integrales", "asesoria", "asesoría"
}


# Supported geographic dictionaries
GEO_CITY_REGISTRY = {
    # Colombia 🇨🇴
    "medellin": {"country": "CO", "city": "Medellín", "department": "Antioquia"},
    "medellín": {"country": "CO", "city": "Medellín", "department": "Antioquia"},
    "antioquia": {"country": "CO", "city": "Medellín", "department": "Antioquia"},
    "valle de aburra": {"country": "CO", "city": "Medellín", "department": "Antioquia"},
    "aburra": {"country": "CO", "city": "Medellín", "department": "Antioquia"},
    "envigado": {"country": "CO", "city": "Envigado", "department": "Antioquia"},
    "itagui": {"country": "CO", "city": "Itagüí", "department": "Antioquia"},
    "itagüi": {"country": "CO", "city": "Itagüí", "department": "Antioquia"},
    "bello": {"country": "CO", "city": "Bello", "department": "Antioquia"},
    "bogota": {"country": "CO", "city": "Bogotá", "department": "Bogotá D.C."},
    "bogotá": {"country": "CO", "city": "Bogotá", "department": "Bogotá D.C."},
    "cundinamarca": {"country": "CO", "city": "Bogotá", "department": "Bogotá D.C."},
    "santiago de cali": {"country": "CO", "city": "Cali", "department": "Valle del Cauca"},
    "cali": {"country": "CO", "city": "Cali", "department": "Valle del Cauca"},
    "valle del cauca": {"country": "CO", "city": "Cali", "department": "Valle del Cauca"},
    "barranquilla": {"country": "CO", "city": "Barranquilla", "department": "Atlántico"},
    "atlantico": {"country": "CO", "city": "Barranquilla", "department": "Atlántico"},
    "cartagena": {"country": "CO", "city": "Cartagena", "department": "Bolívar"},
    "bolivar": {"country": "CO", "city": "Cartagena", "department": "Bolívar"},
    "bucaramanga": {"country": "CO", "city": "Bucaramanga", "department": "Santander"},
    "santander": {"country": "CO", "city": "Bucaramanga", "department": "Santander"},
    "pereira": {"country": "CO", "city": "Pereira", "department": "Risaralda"},
    "manizales": {"country": "CO", "city": "Manizales", "department": "Caldas"},
    "todo colombia": {"country": "CO", "city": "Colombia", "department": "Nacional"},
    "toda colombia": {"country": "CO", "city": "Colombia", "department": "Nacional"},
    "colombia": {"country": "CO", "city": "Colombia", "department": "Nacional"},

    # Dominican Republic 🇩🇴
    "santo domingo": {"country": "DO", "city": "Santo Domingo", "department": "Distrito Nacional"},
    "distrito nacional": {"country": "DO", "city": "Santo Domingo", "department": "Distrito Nacional"},
    "santiago de los caballeros": {"country": "DO", "city": "Santiago", "department": "Santiago"},
    "santiago": {"country": "DO", "city": "Santiago", "department": "Santiago"},
    "punta cana": {"country": "DO", "city": "Punta Cana", "department": "La Altagracia"},
    "republica dominicana": {"country": "DO", "city": "Santo Domingo", "department": "Distrito Nacional"},
    "república dominicana": {"country": "DO", "city": "Santo Domingo", "department": "Distrito Nacional"},

    # Ecuador 🇪🇨
    "quito": {"country": "EC", "city": "Quito", "department": "Pichincha"},
    "pichincha": {"country": "EC", "city": "Quito", "department": "Pichincha"},
    "guayaquil": {"country": "EC", "city": "Guayaquil", "department": "Guayas"},
    "guayas": {"country": "EC", "city": "Guayaquil", "department": "Guayas"},
    "cuenca": {"country": "EC", "city": "Cuenca", "department": "Azuay"},
    "azuay": {"country": "EC", "city": "Cuenca", "department": "Azuay"},
    "ambato": {"country": "EC", "city": "Ambato", "department": "Tungurahua"},
    "manta": {"country": "EC", "city": "Manta", "department": "Manabí"},
    "ecuador": {"country": "EC", "city": "Quito", "department": "Pichincha"},
}

BUYER_DIRECTIONALITY_TRIGGERS = [
    "comprar", "compro", "adquirir", "adquisicion", "adquisición",
    "cotizar", "cotizacion", "cotización", "cotizaciones",
    "proveedor", "proveedores", "busco proveedor", "buscamos proveedor",
    "necesito proveedor", "necesitamos proveedor", "reparar", "reparacion", "reparación",
    "mantenimiento", "mantenimiento de", "suministro", "suministro de",
    "licitacion", "licitación", "rfq", "pliego", "contratar", "solicitar cotizacion",
    "solicitar cotización", "quiero comprar", "buscamos quien nos haga",
]

VENDOR_DIRECTIONALITY_TRIGGERS = [
    "vender", "vendo", "ofrecer", "ofrezco", "ofrecemos", "nuestros servicios",
    "nuestro producto", "prospectar", "prospeccion", "prospección",
    "buscar clientes", "busco clientes", "conseguir clientes", "lead generation",
    "generar leads", "venderle", "venderles", "comercializar", "quiero vender",
]

PROCUREMENT_ROLES = [
    "Gerente Comercial",
    "Director de Ventas",
    "Ejecutivo de Cuenta",
    "Representante Legal",
    "Gerente de Operaciones",
]


class BriefParserService:
    """
    Intelligent Brief-to-Criteria compiler.
    Uses Gemini Flash when available, falling back seamlessly to local BM25 indexing.
    """

    def __init__(self, gemini_api_key: Optional[str] = None, sql_adapter: Optional[Any] = None):
        self.api_key = gemini_api_key or os.environ.get("GEMINI_API_KEY", "")
        self.sql_adapter = sql_adapter
        self.isic_index = get_isic_index()

    def parse_brief(
        self,
        prompt: str,
        client_id: Optional[str] = None,
        session_id: Optional[str] = None,
        force_fallback: bool = False,
    ) -> Dict[str, Any]:
        """
        Translates raw text into a validated Super Query configuration.
        """
        clean_prompt = prompt.strip()
        if not clean_prompt:
            raise ValueError("Prompt must not be empty.")

        # Attempt Gemini Flash resolution if API key present and not forced fallback
        if self.api_key and not force_fallback:
            try:
                parsed = self._parse_with_gemini_flash(clean_prompt)
                parsed["source"] = "gemini-flash"
            except Exception as e:
                logger.warning(f"Gemini Flash parsing failed ({e}). Falling back to local BM25 index.")
                parsed = self._parse_with_local_index(clean_prompt)
                parsed["source"] = "local-bm25-fallback"
        else:
            parsed = self._parse_with_local_index(clean_prompt)
            parsed["source"] = "local-bm25-fallback"

        # Cross-validate CIIU codes with official catalog
        validated_codes = []
        for code in parsed.get("ciiu_codes", []):
            clean_code = str(code).strip()
            entry = self.isic_index.get_by_code(clean_code)
            if entry:
                validated_codes.append(entry.code)
        
        # If no valid codes returned, search local index using prompt tokens
        if not validated_codes:
            local_matches = self.isic_index.search(clean_prompt, limit=3)
            validated_codes = [m[0].code for m in local_matches]

        parsed["ciiu_codes"] = validated_codes

        # Persist to database if adapter available
        query_id = None
        if self.sql_adapter and hasattr(self.sql_adapter, "log_search_intent_query"):
            try:
                query_id = self.sql_adapter.log_search_intent_query(
                    raw_prompt=clean_prompt,
                    parsed_criteria=parsed,
                    client_id=client_id,
                    discovered_tokens=parsed.get("discovered_tokens", {}),
                    session_id=session_id,
                )
            except Exception as e:
                logger.warning(f"Could not persist search intent query: {e}")

        parsed["query_id"] = query_id or f"qry_{os.urandom(4).hex()}"
        return parsed

    def _parse_with_local_index(self, prompt: str) -> Dict[str, Any]:
        """
        Sub-millisecond local BM25 + regex deterministic parser ($0 cost, 100% offline).
        """
        lower = prompt.lower()

        # 1. Directionality
        buyer_score = sum(1 for kw in BUYER_DIRECTIONALITY_TRIGGERS if kw in lower)
        vendor_score = sum(1 for kw in VENDOR_DIRECTIONALITY_TRIGGERS if kw in lower)

        if buyer_score > vendor_score:
            directionality = "client_to_vendors"
        elif vendor_score > buyer_score:
            directionality = "vendor_to_clients"
        else:
            directionality = "vendor_to_clients"  # Default

        # 2. Geography Detection
        detected_locations = []
        seen_cities = set()
        primary_country = "CO"

        # Search for exact city/country tokens, prioritizing longer multi-word tokens first
        sorted_tokens = sorted(GEO_CITY_REGISTRY.keys(), key=len, reverse=True)
        for token in sorted_tokens:
            geo_info = GEO_CITY_REGISTRY[token]
            if re.search(rf"\b{re.escape(token)}\b", lower):
                city_key = f"{geo_info['country']}_{geo_info['city']}"
                if city_key not in seen_cities:
                    seen_cities.add(city_key)
                    detected_locations.append(geo_info)
                    primary_country = geo_info["country"]

        # Default to Medellín CO if none found
        if not detected_locations:
            detected_locations.append({"country": "CO", "city": "Medellín", "department": "Antioquia"})

        # 3. Volume / Limit & Location Allocation
        # Match explicit lead allocations per city (e.g. "Cali unas 50 y Barranquilla 40 y en todo Colombia otras 10")
        explicit_allocations: Dict[str, int] = {}
        for loc in detected_locations:
            loc_name = loc["city"].lower()
            # Match patterns like: "cali (?:unas |unos |otras |otros )?(\d+)" or "(\d+)\s+(?:en\s+)?cali"
            m = re.search(rf"\b{re.escape(loc_name)}\b[^\d\n\.,;]{{0,25}}?(\d+)", lower)
            if not m:
                m = re.search(rf"(\d+)[^\d\n\.,;]{{0,15}}?\b{re.escape(loc_name)}\b", lower)
            if m:
                count = int(m.group(1))
                if 1 <= count <= 10000:
                    explicit_allocations[loc["city"]] = count

        total_limit_match = re.search(r"\b(?:busco|necesito|quiero|solicito|dame|genera|generar|arma|total|de)\s+(\d{1,4})\b", lower)
        numbers = [int(n) for n in re.findall(r"\b\d+\b", lower) if int(n) >= 5]

        if total_limit_match:
            limit = int(total_limit_match.group(1))
        elif explicit_allocations and len(explicit_allocations) == len(detected_locations):
            limit = sum(explicit_allocations.values())
        elif numbers:
            limit = numbers[0]
        else:
            limit = 25  # Standard conversion-optimized batch

        leads_per_loc = max(1, limit // len(detected_locations))
        remainder = limit % len(detected_locations)
        location_allocations = []
        for i, loc in enumerate(detected_locations):
            alloc = explicit_allocations.get(loc["city"]) or (leads_per_loc + (remainder if i == 0 else 0))
            location_allocations.append({
                "country": loc["country"],
                "region": loc.get("department", loc["city"]),
                "city": loc["city"],
                "allocated_leads": alloc,
            })
        if explicit_allocations and len(explicit_allocations) == len(detected_locations):
            limit = sum(l["allocated_leads"] for l in location_allocations)

        # 4. Tier Detection & Cross-Border Cap
        tier = 2
        if any(term in lower for term in ["ebitda", "balance", "financiero", "solvencia", "litigio", "demanda", "deuda", "superintendencia", "debida diligencia"]):
            tier = 3
        elif any(term in lower for term in ["directorio", "masivo", "tier 1", "base basica", "base básica", "basico", "básico", "pbx"]):
            tier = 1

        # Restrict Tier 3 exclusively to 100% Colombian campaigns
        has_non_co = any(loc["country"] != "CO" for loc in location_allocations)
        tier_notice = None
        if tier == 3 and has_non_co:
            tier = 2
            tier_notice = (
                "Tier 3 (Auditoría Financiera NIIF & Litigios) está disponible exclusivamente para entidades registradas en Colombia "
                "debido a la centralización pública de estados contables en la Superintendencia de Sociedades. Para pedidos con "
                "cobertura en Ecuador o República Dominicana, el nivel estándar de prospección comercial es Tier 2 (Contactos Directos Verificados)."
            )

        # 5. Local BM25 CIIU Resolution
        # Purge prompt meta-words so terms like "cargos directivos" don't trigger freight cargo
        clean_tokens = [w for w in re.findall(r"\b[a-záéíóúñ]{3,}\b", lower) if w not in QUERY_STOP_WORDS]
        search_query = " ".join(clean_tokens) if clean_tokens else prompt
        matches = self.isic_index.search(search_query, limit=4)
        ciiu_codes = [m[0].code for m in matches]
        
        # Sector keys
        sectors = []
        for m in matches:
            entry = m[0]
            # Convert sector_macro to slug
            slug = re.sub(r"[^a-z0-9_]+", "_", entry.sector_macro.lower().strip()).strip("_")
            if slug and slug not in sectors:
                sectors.append(slug)
        if not sectors:
            sectors = ["general_commercial"]

        # 6. Roles Resolution
        if directionality == "client_to_vendors":
            roles = list(PROCUREMENT_ROLES)
        else:
            roles = []
            for m in matches:
                entry_roles = m[0].typical_roles.get(primary_country) or m[0].typical_roles.get("ALL") or []
                for r in entry_roles:
                    if r not in roles:
                        roles.append(r)
            if not roles:
                roles = ["Gerente General", "Director de Operaciones", "Director de Compras", "Jefe de Compras"]

        # 7. Keywords Include / Exclude
        # Extract high-intent compound domain phrases first
        compound_patterns = [
            (r"\bdesarrollo\s+(?:de\s+)?software\b", "desarrollo de software"),
            (r"\bdesarrollo\s+(?:de\s+)?sistemas\b", "desarrollo de software"),
            (r"\bdesarrollo\s+web\b", "desarrollo web"),
            (r"\bservicios?\s+cloud\b", "cloud"),
            (r"\binfraestructura\s+ti\b", "infraestructura ti"),
            (r"\bobras?\s+civiles?\b", "obras civiles"),
            (r"\bgestion\s+(?:de\s+)?cartera\b", "gestion de cartera"),
            (r"\bseguridad\s+privada\b", "seguridad privada"),
            (r"\bmantenimiento\s+locativo\b", "mantenimiento"),
        ]
        compound_kws = []
        for pat, canonical in compound_patterns:
            if re.search(pat, lower):
                if canonical not in compound_kws:
                    compound_kws.append(canonical)

        # Remove prompt meta-words and Spanish stopwords
        raw_words = [w for w in re.findall(r"\b[a-záéíóúñ]{4,}\b", lower) if w not in QUERY_STOP_WORDS]
        # Normalize plurals (e.g. coworkings -> coworking)
        words = list(compound_kws)
        for w in raw_words:
            norm_w = w[:-1] if w.endswith("s") and len(w) > 5 and not w.endswith("ss") else w
            if norm_w not in QUERY_STOP_WORDS and norm_w not in words:
                words.append(norm_w)
        keywords_include = words[:6]

        # Exclusions (e.g. "sin colegios publicos", "no intermediarios")
        keywords_exclude = []
        exclude_match = re.search(r"(?:sin|no incluir|excluir|excepto)\s+([a-záéíóúñ\s,]+)", lower)
        if exclude_match:
            ex_terms = [t.strip() for t in exclude_match.group(1).split(",") if len(t.strip()) > 3]
            keywords_exclude.extend(ex_terms[:4])

        # RFQ specifications if buyer mode
        rfq_specifications = None
        if directionality == "client_to_vendors":
            rfq_specifications = prompt.strip()

        return {
            "directionality": directionality,
            "sectors": sectors[:3],
            "ciiu_codes": ciiu_codes,
            "roles": roles[:5],
            "locations": location_allocations,
            "limit": limit,
            "tier": tier,
            "tier_notice": tier_notice,
            "rfq_specifications": rfq_specifications,
            "keywords_include": keywords_include,
            "keywords_exclude": keywords_exclude,
            "discovered_tokens": {
                "raw_keywords": words[:10],
                "primary_country": primary_country,
                "isic_matches": [
                    {"code": m[0].code, "title": m[0].title, "score": round(m[1], 2)}
                    for m in matches
                ],
            },
            "confidence_score": 0.95 if matches else 0.70,
        }

    def _parse_with_gemini_flash(self, prompt: str) -> Dict[str, Any]:
        """
        Parses complex or unstructured briefs using Gemini Flash via HTTP REST.
        Tries latest production Gemini Flash models with graceful fallback.
        """
        system_instruction = (
            "You are Michito AI, an expert B2B prospecting & procurement briefing engine "
            "for Colombia 🇨🇴, Dominican Republic 🇩🇴, and Ecuador 🇪🇨.\n"
            "Analyze the user's natural language request and output a strictly valid JSON object matching the schema:\n"
            "{\n"
            '  "directionality": "vendor_to_clients" (if selling) or "client_to_vendors" (if buying/procuring/RFQ),\n'
            '  "sectors": ["slug_sector_name"],\n'
            '  "ciiu_codes": ["4-digit ISIC/CIIU codes matching the niche product/domain precisely (e.g. food wholesale: 4631, 4632; restaurant supplies: 5611)"],\n'
            '  "roles": ["Target executive titles"],\n'
            '  "locations": [{"country": "CO"|"DO"|"EC", "region": "Department/State", "city": "City name", "allocated_leads": 15}],\n'
            '  "limit": integer total volume (default 25),\n'
            '  "tier": 1 (directory) | 2 (decision maker email+phone) | 3 (financial EBITDA / litigation audit, ONLY if all locations are in CO),\n'
            '  "rfq_specifications": "tender requirements or null",\n'
            '  "keywords_include": ["SPECIFIC product, service, or niche substantive terms or compound phrases only (e.g. alimentos, restaurantes, desarrollo de software, servicios cloud). NEVER include solitary generic words like desarrollo, distribuidora, empresa, mayorista, proveedor, fabricante, soluciones, servicios."],\n'
            '  "keywords_exclude": ["terms to exclude"],\n'
            '  "confidence_score": float between 0.0 and 1.0\n'
            "}\n"
            "CRITICAL RULES:\n"
            "1. 'keywords_include' MUST ONLY contain specific industry/product nouns or compound phrases (e.g. 'desarrollo de software', 'servicios cloud', 'alimentos', 'carnicos'). NEVER output solitary generic words like 'desarrollo', 'distribuidora', 'empresa', 'proveedor', 'mayorista', 'fabricante', 'soluciones', or 'servicios'.\n"
            "2. If the user allocates specific counts per city (e.g. 'Cali unas 50 y Barranquilla 40 y en todo Colombia 10'), allocate exact numbers in 'allocated_leads' for each location.\n"
            "3. Tier 3 is strictly restricted to orders where 100% of locations are in Colombia ('CO'). If locations include 'DO', 'EC', or are mixed, tier MUST be 2 or 1."
        )

        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "systemInstruction": {"parts": [{"text": system_instruction}]},
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.1,
            },
        }

        models_to_try = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
        last_error = None
        usage_data = {}
        chosen_model = None

        for model_name in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.api_key}"
            try:
                with httpx.Client(timeout=2.5) as client:
                    resp = client.post(url, json=body)
                    resp.raise_for_status()
                    data = resp.json()
                text_response = data["candidates"][0]["content"]["parts"][0]["text"]
                usage_data = data.get("usageMetadata", {})
                chosen_model = model_name
                result = json.loads(text_response)
                break
            except Exception as e:
                last_error = e
                continue
        else:
            raise RuntimeError(f"All Gemini Flash models failed. Last error: {last_error}")

        # Basic sanitization
        if "directionality" not in result or result["directionality"] not in ("vendor_to_clients", "client_to_vendors"):
            result["directionality"] = "vendor_to_clients"

        # Sanitize keywords_include: purge any accidental commercial stopwords and lone polysemic unigrams
        if "keywords_include" in result and isinstance(result["keywords_include"], list):
            sanitized_kws = []
            for kw in result["keywords_include"]:
                clean_k = str(kw).strip().lower()
                if " " not in clean_k and clean_k in QUERY_STOP_WORDS:
                    continue
                if clean_k and len(clean_k) >= 3 and clean_k not in sanitized_kws:
                    sanitized_kws.append(clean_k)
            result["keywords_include"] = sanitized_kws

        # Sanitize cross-border Tier 3 restriction
        locs = result.get("locations", [])
        if any(l.get("country") != "CO" for l in locs) and result.get("tier") == 3:
            result["tier"] = 2
            result["tier_notice"] = (
                "Tier 3 (Auditoría Financiera NIIF & Litigios) está disponible exclusivamente para entidades registradas en Colombia "
                "debido a la centralización pública de estados contables en la Superintendencia de Sociedades. Para pedidos con "
                "cobertura en Ecuador o República Dominicana, el nivel estándar de prospección comercial es Tier 2 (Contactos Directos Verificados)."
            )

        # Financial Observability: Record Token Usage & Incurred Cost
        prompt_tokens = usage_data.get("promptTokenCount", 0)
        candidates_tokens = usage_data.get("candidatesTokenCount", 0)
        total_tokens = usage_data.get("totalTokenCount", prompt_tokens + candidates_tokens)
        cost_cop = round(((prompt_tokens * 0.075 / 1_000_000) + (candidates_tokens * 0.30 / 1_000_000)) * 4100, 4)

        result["token_usage"] = {
            "model": chosen_model,
            "prompt_tokens": prompt_tokens,
            "candidates_tokens": candidates_tokens,
            "total_tokens": total_tokens,
            "cost_cop": cost_cop,
        }

        result["discovered_tokens"] = {
            "gemini_parsed": True,
            "raw_text": prompt,
            "token_usage": result["token_usage"],
        }
        return result
