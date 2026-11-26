"""
Universal ISIC / CIIU Rev. 4 In-Memory Token & BM25 Search Index.
Provides sub-millisecond resolution of freeform economic activity text,
company names, or sector queries to official 4-digit UN ISIC / DANE CIIU codes.
"""

from collections import defaultdict
from datetime import datetime, timezone
import math
import re
from typing import Any, Dict, List, Optional, Set, Tuple
import unicodedata

try:
    from src.domain.taxonomy.isic_catalog import UNIVERSAL_ISIC_CATALOG, IsicEntry
except ImportError:
    from backend.src.domain.taxonomy.isic_catalog import UNIVERSAL_ISIC_CATALOG, IsicEntry


def normalize_text(text: str) -> str:
    """Removes accents, lowercases, and strips non-alphanumeric characters."""
    if not text:
        return ""
    # Normalize unicode to decomposed form and remove combining marks (accents)
    nfkd = unicodedata.normalize("NFKD", text)
    stripped = "".join(c for c in nfkd if not unicodedata.combining(c))
    # Lowercase and replace non-alphanumeric with spaces
    lowered = stripped.lower()
    cleaned = re.sub(r"[^a-z0-9\s]", " ", lowered)
    return re.sub(r"\s+", " ", cleaned).strip()


def tokenize(text: str) -> List[str]:
    """Tokenizes normalized text into words, omitting common stop words."""
    norm = normalize_text(text)
    if not norm:
        return []
    
    stop_words = {
        "de", "la", "el", "los", "las", "un", "una", "unos", "unas", "y", "o", "en",
        "a", "para", "por", "con", "sin", "del", "al", "actividades", "actividad",
        "otras", "otros", "demas", "conexas", "conexos", "excepto", "ncp", "incluye",
        "servicios", "servicio", "empresas", "empresa", "general", "generales",
        "grupo", "holding", "sociedad", "sociedades", "inversiones", "inversion",
        "corporativo", "corporativa", "corporacion", "empresarial", "empresariales",
        "asociacion", "asociados", "asociadas", "soluciones", "integrales", "integral",
        "info", "contacto", "ventas", "admin", "comercial", "gerencia", "notificaciones",
        "com", "net", "org", "co",
        "sas", "ltda", "sa", "colombia", "internacional", "nacional"
    }
    
    tokens = [t for t in norm.split() if len(t) > 1 and t not in stop_words]
    return tokens


class IsicIndex:
    """
    Sub-millisecond token & BM25 search index for the Universal ISIC Rev. 4 catalog.
    Zero external dependencies and instant in-memory lookup.
    Supports dynamic hot-reloading from PostgreSQL (taxonomy_isic_codes and taxonomy_semantic_patterns)
    with zero-downtime in-memory caching and offline fallback.
    """

    def __init__(self, catalog: Optional[Dict[str, IsicEntry]] = None):
        self.catalog = dict(catalog or UNIVERSAL_ISIC_CATALOG)
        self.doc_count = len(self.catalog)
        self.inverted_index: Dict[str, List[Tuple[str, float]]] = defaultdict(list)
        self.code_lookup: Dict[str, IsicEntry] = {}
        self.doc_lengths: Dict[str, int] = {}
        self.patterns: List[Tuple[str, str, str]] = []  # (regex, code, country_code)
        self.exclusion_rules: Dict[str, List[str]] = defaultdict(list)
        self.last_loaded_at: Optional[float] = None
        self._init_seed_patterns()
        self._init_seed_exclusions()
        self._build_index()

    def _init_seed_exclusions(self) -> None:
        self.exclusion_rules["representative_placeholder"] = [
            "liquidador", "liquidadora", "revisor fiscal", "secretario ad-hoc",
            "agente especial", "curador", "no registra", "no reporta",
            "sin representante", "en tramite", "en trámite", "por definir",
        ]
        self.exclusion_rules["bankrupt_status"] = [
            "en liquidacion", "en liquidación",
        ]
        self.exclusion_rules["sector:food_agriculture"] = [
            "papeleria", "papelería", "contabilidad", "auditoria", "auditoría", "tributaria",
            "construccion", "construcción", "edificios", "bodegas", "obras civiles",
            "farmaceutic", "farmacéutic", "medicinal", "medicamento", "drogueria", "droguería",
            "cosmetico", "cosmético", "textil", "telas", "confeccion", "confección", "prendas de vestir", "ropa",
            "ferreteria", "ferretería", "metal", "metalurgic", "metalúrgic", "tornillo",
            "maquinaria agricola", "tractor", "repuestos de vehiculos", "autopartes",
            "publicidad", "agencia de medios", "software", "inmobiliaria", "vigilancia", "seguridad privada"
        ]

    def _init_seed_patterns(self) -> None:
        self.patterns = [
            (r"colegio|escuela|educa|ensenanza|liceo|gimnasio|academ|universidad|institucion educativa|bachillerato|preescolar|carnet", "8530", "ALL"),
            (r"alimento|abarrote|viveres|granos|lacteo|carnic|horeca|frutas|conservas|gastronom|comida", "4631", "ALL"),
            (r"combustible|gasolina|diesel|acpm|lubricante|hidrocarburo|petroleo|petroquimic", "4661", "ALL"),
            (r"cemento|concreto|acero|ferreteria industrial|materiales de construccion|ladrillo|prefabricados", "4663", "ALL"),
            (r"constructor|construccion|edificac|obras civiles", "4111", "ALL"),
            (r"bodega industrial|cedi|almacenamiento y deposito", "5210", "ALL"),
            (r"cobranza|gestion de cartera|factoring|recuperacion de cartera", "8291", "ALL"),
            (r"facility|limpieza|aseo|mantenimiento locativo|seguridad fisica|seguridad privada|vigilancia|conserj", "8110", "ALL"),
            (r"cowork|oficinas flexibles|espacios compartidos|espacios de trabajo", "6820", "ALL"),
            (r"inmobiliari|bienes raices|propiedad horizontal|arrendamiento", "6810", "ALL"),
            (r"logist|transport|carga|aduan|fletes|almacen", "4923", "ALL"),
            (r"medical|salud|ips|clinic|farmaceut|biomed|odontol|dispositiv", "3250", "ALL"),
            (r"software|analyt|data|tech|digital|sistemas|program|cloud|\bia\b|\bai\b|ciber", "6201", "ALL"),
            (r"comput|hardware|redes|servidores|telecom", "4651", "ALL"),
            (r"abogad|legal|jurid|derecho|leyes|litig", "6910", "ALL"),
            (r"contab|auditor|financ|tributar|revisoria|impuesto", "6920", "ALL"),
            (r"fintech|invers|fondos|credito|valores", "6499", "ALL"),
            (r"arquitect|ingenier|civil|obras|interventor|diseno tecnico", "7110", "ALL"),
            (r"publicid|marketing|btl|eventos|comunicacion|medios|agencia", "7310", "ALL"),
            (r"maquinaria|equipos|repuestos|industrial", "4659", "ALL"),
            (r"(comercio|distribuidora|mayorista|almacen).*(telas|textil|ropa|confeccion)", "4641", "ALL"),
            (r"boutique|tienda de ropa|almacen de ropa|venta de prendas|venta de ropa", "4771", "ALL"),
            (r"zapateria|tienda de calzado|almacen de calzado|venta de calzado", "4772", "ALL"),
            (r"confeccion|confecciones|prendas de vestir|ropa|costura|maquila textil|uniformes|sastreria|camiseria|pantalones|vestidos|lenceria|moda", "1410", "ALL"),
            (r"calzado|zapater|fabrica de zapatos|botas|suelas|marroquiner|curtiembre|cueros|bolsos de cuero|billeteras de cuero", "1521", "ALL"),
            (r"textil|textiles|hilatura|hilados|hilanderia|hilaza|tejeduria|telas|tejidos|dril|denim|indigo|tintoreria textil|estampado textil", "1312", "ALL"),
            (r"distribuid|distribuc|comercializad|comercializac|mayorist", "4690", "ALL"),
            (r"\b(consultor|asesor|asesoria|consultoria|advisory|estrategi)\b", "7020", "ALL"),
        ]

    def _build_index(self) -> None:
        total_len = 0
        for code, entry in self.catalog.items():
            self.code_lookup[code] = entry
            
            # Extract document tokens with weighted sources
            token_weights: Dict[str, float] = defaultdict(float)
            
            # Exact code token
            token_weights[code] += 10.0
            token_weights[entry.division] += 4.0
            
            # Keywords (highest semantic relevance)
            for kw in entry.keywords:
                for token in tokenize(kw):
                    token_weights[token] += 5.0
            
            # Title tokens
            for token in tokenize(entry.title):
                token_weights[token] += 3.0
                
            # Sector macro tokens
            for token in tokenize(entry.sector_macro):
                token_weights[token] += 2.0
                
            # Section title tokens
            for token in tokenize(entry.section_title):
                token_weights[token] += 1.0

            doc_len = len(token_weights)
            self.doc_lengths[code] = doc_len
            total_len += doc_len
            
            for token, weight in token_weights.items():
                self.inverted_index[token].append((code, weight))

        self.avg_doc_len = total_len / max(1, self.doc_count)

    def search(self, query: str, limit: int = 5) -> List[Tuple[IsicEntry, float]]:
        """
        Searches the catalog using BM25-inspired term frequency and inverted index weights.
        Returns ranked list of (IsicEntry, score).
        """
        if not query:
            return []

        # Check for direct 4-digit code (e.g. 1410) or explicitly prefixed code (e.g. ciiu 14, isic 6201)
        prefixed_match = re.search(r"\b(?:ciiu|isic)\s*(\d{2,4})\b", query, re.IGNORECASE)
        if prefixed_match:
            candidate_code = prefixed_match.group(1).zfill(4)
            if candidate_code in self.code_lookup:
                entry = self.code_lookup[candidate_code]
                return [(entry, 100.0)]

        four_digit_match = re.search(r"\b(\d{4})\b", query)
        if four_digit_match:
            candidate_code = four_digit_match.group(1)
            if candidate_code in self.code_lookup:
                entry = self.code_lookup[candidate_code]
                return [(entry, 100.0)]

        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        # BM25 parameters
        k1 = 1.5
        b = 0.75

        scores: Dict[str, float] = defaultdict(float)

        for q_token in query_tokens:
            postings = self.inverted_index.get(q_token, [])
            
            # Partial prefix matching for tokens with len >= 4
            if not postings and len(q_token) >= 4:
                prefix = q_token[:4]
                matching_tokens = [t for t in self.inverted_index if t.startswith(prefix)]
                for mt in matching_tokens:
                    for code, weight in self.inverted_index[mt]:
                        scores[code] += weight * 0.5
                continue

            df = len(postings)
            if df == 0:
                continue

            # IDF calculation
            idf = math.log(1.0 + (self.doc_count - df + 0.5) / (df + 0.5))

            for code, weight in postings:
                doc_len = self.doc_lengths.get(code, self.avg_doc_len)
                norm_tf = (weight * (k1 + 1)) / (weight + k1 * (1 - b + b * (doc_len / self.avg_doc_len)))
                scores[code] += idf * norm_tf

        if not scores:
            return []

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:limit]
        return [(self.code_lookup[code], score) for code, score in ranked]

    def resolve_best_match(self, query: str) -> Optional[IsicEntry]:
        """Returns the single top-ranked ISIC entry for a query, or None if no match."""
        results = self.search(query, limit=1)
        if results:
            return results[0][0]
        return None

    def resolve_match_with_confidence(self, query: str) -> Tuple[Optional[IsicEntry], float]:
        """
        Returns the top-ranked ISIC entry along with its BM25 score.
        A score < 3.0 indicates low semantic confidence.
        """
        results = self.search(query, limit=1)
        if results:
            return results[0][0], results[0][1]
        return None, 0.0

    def get_by_code(self, code: str) -> Optional[IsicEntry]:
        """Direct lookup by 4-digit code (e.g. '8530' or '6201')."""
        clean = code.strip().zfill(4)
        return self.code_lookup.get(clean)

    def suggest_roles(self, code: str, country_code: str = "ALL") -> List[str]:
        """Retrieves typical buyer or vendor roles for a given ISIC code and country."""
        entry = self.get_by_code(code)
        if not entry:
            return ["Gerente General", "Director Comercial", "Director de Compras", "Director de Operaciones"]
        
        country = country_code.upper()
        if country in entry.typical_roles:
            return entry.typical_roles[country]
        if "ALL" in entry.typical_roles:
            return entry.typical_roles["ALL"]
        return ["Gerente General", "Director Comercial", "Director de Compras"]

    def get_patterns(self, country_code: str = "ALL") -> List[Tuple[str, str]]:
        """
        Returns active deterministic and agent-learned regex patterns (regex_pattern, ciiu_code)
        matching the target country or 'ALL'.
        """
        c_code = country_code.upper()
        if c_code == "ALL":
            return [(pat, code) for pat, code, _ in self.patterns]
        return [
            (pat, code)
            for pat, code, c in self.patterns
            if c in ("ALL", c_code)
        ]

    def get_exclusion_rules(self, rule_type: Optional[str] = None, sector_id: Optional[str] = None) -> List[str]:
        """
        Returns active exclusion blacklist terms filtered by rule_type or sector_id.
        Pulls from dynamic database sync with zero-downtime offline seed fallback.
        """
        results: List[str] = []
        if rule_type and rule_type in self.exclusion_rules:
            results.extend(self.exclusion_rules[rule_type])
        if sector_id and f"sector:{sector_id}" in self.exclusion_rules:
            results.extend(self.exclusion_rules[f"sector:{sector_id}"])
        if not rule_type and not sector_id:
            for terms in self.exclusion_rules.values():
                results.extend(terms)
        return list(dict.fromkeys(results))

    def load_from_db(self, db_url_or_engine: Optional[Any] = None) -> int:
        """
        Hot-reloads the taxonomy catalog and agent-learned patterns directly from PostgreSQL.
        Maintains sub-millisecond in-memory speeds while ensuring 100% dynamic DB sync.
        """
        import os
        from sqlalchemy import create_engine, select
        from sqlalchemy.orm import Session

        try:
            from src.adapters.db.models import (
                TaxonomyIsicCodeModel,
                TaxonomySemanticPatternModel,
                TaxonomyIsicRoleLinkModel,
                TaxonomyRoleModel,
            )
        except ImportError:
            from backend.src.adapters.db.models import (
                TaxonomyIsicCodeModel,
                TaxonomySemanticPatternModel,
                TaxonomyIsicRoleLinkModel,
                TaxonomyRoleModel,
            )

        engine = db_url_or_engine
        if not engine:
            url = os.environ.get("DATABASE_URL", "postgresql+psycopg://127.0.0.1:5432/michito")
            engine = create_engine(url)

        with Session(engine) as session:
            # 1. Load active ISIC codes
            db_codes = session.scalars(
                select(TaxonomyIsicCodeModel).where(TaxonomyIsicCodeModel.is_active == True)
            ).all()
            if not db_codes:
                return 0

            # 2. Load role links
            role_links = session.execute(
                select(
                    TaxonomyIsicRoleLinkModel.isic_code,
                    TaxonomyIsicRoleLinkModel.country_code,
                    TaxonomyRoleModel.canonical_title,
                )
                .join(TaxonomyRoleModel, TaxonomyIsicRoleLinkModel.role_id == TaxonomyRoleModel.role_id)
                .order_by(TaxonomyIsicRoleLinkModel.priority_rank)
            ).all()

            roles_by_code: Dict[str, Dict[str, List[str]]] = defaultdict(lambda: defaultdict(list))
            for i_code, c_code, r_title in role_links:
                roles_by_code[i_code][c_code].append(r_title)

            # Build in-memory entries
            new_catalog: Dict[str, IsicEntry] = {}
            for row in db_codes:
                typical = dict(roles_by_code.get(row.code, {}))
                if not typical:
                    typical = {
                        "CO": ["Gerente General", "Director Comercial", "Jefe de Compras"],
                        "ALL": ["Gerente General", "Director Comercial", "Jefe de Compras"],
                    }
                new_catalog[row.code] = IsicEntry(
                    code=row.code,
                    division=row.division,
                    section=row.section,
                    section_title=row.section_title,
                    title=row.title,
                    sector_macro=row.sector_macro,
                    keywords=list(row.keywords or []),
                    typical_roles=typical,
                )

            # 3. Load dynamic patterns
            db_patterns = session.scalars(
                select(TaxonomySemanticPatternModel)
                .where(TaxonomySemanticPatternModel.is_active == True)
                .order_by(TaxonomySemanticPatternModel.priority.asc())
            ).all()

            new_patterns: List[Tuple[str, str, str]] = []
            for p in db_patterns:
                new_patterns.append((p.regex_pattern, p.target_isic_code, p.country_code))

            # 4. Load dynamic exclusion rules
            try:
                from src.adapters.db.models import TaxonomyExclusionRuleModel
                db_exclusions = session.scalars(
                    select(TaxonomyExclusionRuleModel).where(TaxonomyExclusionRuleModel.is_active == True)
                ).all()
                if db_exclusions:
                    new_excl: Dict[str, List[str]] = defaultdict(list)
                    for rule in db_exclusions:
                        new_excl[rule.rule_type].append(rule.term.lower())
                        if rule.target_sector_id:
                            new_excl[f"sector:{rule.target_sector_id}"].append(rule.term.lower())
                    self.exclusion_rules = new_excl
            except Exception:
                pass

            if new_catalog:
                self.catalog = new_catalog
                self.doc_count = len(new_catalog)
                if new_patterns:
                    self.patterns = new_patterns
                self._build_index()
                import time
                self.last_loaded_at = time.time()
                return len(new_catalog)

        return 0

    def try_load_from_db(self) -> bool:
        """Attempts to load from database without raising exceptions."""
        try:
            loaded = self.load_from_db()
            return loaded > 0
        except Exception:
            return False

    def record_learned_pattern(
        self,
        pattern_id: str,
        target_isic_code: str,
        regex_pattern: str,
        country_code: str = "ALL",
        db_url: Optional[str] = None,
    ) -> bool:
        """
        Dynamically records a new agent-learned regex pattern into memory and PostgreSQL.
        Immediately available for all future Stage 1 evaluations.
        """
        import os
        from sqlalchemy import create_engine, select
        from sqlalchemy.orm import Session

        # 1. Update in-memory patterns list
        self.patterns.insert(0, (regex_pattern, target_isic_code, country_code.upper()))

        # 2. Persist to PostgreSQL if accessible
        try:
            from src.adapters.db.models import TaxonomySemanticPatternModel
        except ImportError:
            from backend.src.adapters.db.models import TaxonomySemanticPatternModel

        url = db_url or os.environ.get("DATABASE_URL", "postgresql+psycopg://127.0.0.1:5432/michito")
        try:
            engine = create_engine(url)
            with Session(engine) as session:
                existing = session.scalar(
                    select(TaxonomySemanticPatternModel).where(TaxonomySemanticPatternModel.pattern_id == pattern_id)
                )
                if existing:
                    existing.match_count = (existing.match_count or 0) + 1
                    existing.updated_at = datetime.now(timezone.utc)
                else:
                    new_pat = TaxonomySemanticPatternModel(
                        pattern_id=pattern_id,
                        target_isic_code=target_isic_code,
                        regex_pattern=regex_pattern,
                        country_code=country_code.upper(),
                        priority=50,
                        source="agent_learned",
                        match_count=1,
                        is_active=True,
                    )
                    session.add(new_pat)
                session.commit()
            return True
        except Exception:
            return False


# Global singleton instance for high-speed reuse across the application
GLOBAL_ISIC_INDEX = IsicIndex()
GLOBAL_ISIC_INDEX.try_load_from_db()


def get_isic_index() -> IsicIndex:
    """Returns the singleton ISIC index instance."""
    return GLOBAL_ISIC_INDEX

