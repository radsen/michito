"""
CIIU (Clasificación Industrial Internacional Uniforme) Value Object
Based on DANE CIIU Rev. 4 A.C. (Adaptación para Colombia).
Provides official economic activity taxonomy, sector categorization, and validation.
"""

from dataclasses import dataclass
import re
from typing import Dict, Optional, Tuple

try:
    from src.domain.taxonomy.isic_catalog import UNIVERSAL_ISIC_CATALOG
except ImportError:
    from backend.src.domain.taxonomy.isic_catalog import UNIVERSAL_ISIC_CATALOG

# Dynamic relational catalog referencing the Universal ISIC Rev. 4 taxonomy (replaces legacy 230-line hardcoding)
OFFICIAL_CIIU_CATALOG: Dict[str, Dict[str, str]] = {
    code: {
        "code": entry.code,
        "description": entry.title,
        "sector_macro": entry.sector_macro,
        "tinkko_fit": f"Sector: {entry.sector_macro}"
    }
    for code, entry in UNIVERSAL_ISIC_CATALOG.items()
}


@dataclass(frozen=True)
class CiiuCode:
    code: str
    description: str
    sector_macro: str
    tinkko_fit: str

    @classmethod
    def from_code(cls, code: str) -> "CiiuCode":
        clean_code = code.strip().zfill(4)
        if clean_code in OFFICIAL_CIIU_CATALOG:
            data = OFFICIAL_CIIU_CATALOG[clean_code]
            return cls(
                code=data["code"],
                description=data["description"],
                sector_macro=data["sector_macro"],
                tinkko_fit=data["tinkko_fit"]
            )
        # Check universal ISIC index
        try:
            try:
                from src.domain.taxonomy.isic_index import GLOBAL_ISIC_INDEX
            except ImportError:
                from backend.src.domain.taxonomy.isic_index import GLOBAL_ISIC_INDEX
            entry = GLOBAL_ISIC_INDEX.get_by_code(clean_code)
            if entry:
                return cls(
                    code=entry.code,
                    description=entry.title,
                    sector_macro=entry.sector_macro,
                    tinkko_fit="Relevante (Taxonomía Universal ISIC Rev. 4)"
                )
        except Exception:
            pass

        return cls(
            code=clean_code,
            description=f"Actividad Económica CIIU {clean_code}",
            sector_macro="Servicios Empresariales & Comerciales",
            tinkko_fit="General"
        )

    @classmethod
    def infer_from_text(cls, company_name: str, email: str = "", raw_desc: str = "") -> "CiiuCode":
        """
        Infers the 4-digit DANE CIIU Rev. 4 A.C. code and economic activity based
        on corporate registration name, official email domain, and declared activity.
        Corresponds to Box 46 ('Actividad Principal') of the Colombian DIAN RUT.
        Uses high-speed inverted index over 241 official classes.
        """
        text = f"{company_name} {email} {raw_desc}".lower()

        patterns = [
            (r"colegio|escuela|educa|ensenanza|liceo|gimnasio|academ|universidad|institucion educativa|bachillerato|preescolar|carnet", "8530"),
            (r"alimento|abarrote|viveres|granos|lacteo|carnic|horeca|frutas|conservas|gastronom|comida", "4631"),
            (r"combustible|gasolina|diesel|acpm|lubricante|hidrocarburo|petroleo|petroquimic", "4661"),
            (r"cemento|concreto|acero|ferreteria industrial|materiales de construccion|ladrillo|prefabricados", "4663"),
            (r"constructor|construccion|edificac|obras civiles", "4111"),
            (r"bodega industrial|cedi|almacenamiento y deposito", "5210"),
            (r"cobranza|gestion de cartera|factoring|recuperacion de cartera", "8291"),
            (r"facility|limpieza|aseo|mantenimiento locativo|seguridad fisica|seguridad privada|vigilancia|conserj", "8110"),
            (r"cowork|oficinas flexibles|espacios compartidos|espacios de trabajo", "6820"),
            (r"inmobiliari|bienes raices|propiedad horizontal|arrendamiento", "6810"),
            (r"logist|transport|carga|aduan|fletes|almacen", "4923"),
            (r"medical|salud|ips|clinic|farmaceut|biomed|odontol|dispositiv", "3250"),
            (r"software|analyt|data|tech|digital|sistemas|program|cloud|\bia\b|\bai\b|ciber", "6201"),
            (r"comput|hardware|redes|servidores|telecom", "4651"),
            (r"abogad|legal|jurid|derecho|leyes|litig", "6910"),
            (r"contab|auditor|financ|tributar|revisoria|impuesto", "6920"),
            (r"fintech|invers|fondos|credito|valores", "6499"),
            (r"arquitect|ingenier|civil|obras|interventor|diseno tecnico", "7110"),
            (r"publicid|marketing|btl|eventos|comunicacion|medios|agencia", "7310"),
            (r"maquinaria|equipos|repuestos|industrial", "4659"),
            (r"(comercio|distribuidora|mayorista|almacen).*(telas|textil|ropa|confeccion)", "4641"),
            (r"boutique|tienda de ropa|almacen de ropa|venta de prendas|venta de ropa", "4771"),
            (r"zapateria|tienda de calzado|almacen de calzado|venta de calzado", "4772"),
            (r"confeccion|confecciones|prendas de vestir|ropa|costura|maquila textil|uniformes|sastreria|camiseria|pantalones|vestidos|lenceria|moda", "1410"),
            (r"calzado|zapater|fabrica de zapatos|botas|suelas|marroquiner|curtiembre|cueros|bolsos de cuero|billeteras de cuero", "1521"),
            (r"textil|textiles|hilatura|hilados|hilanderia|hilaza|tejeduria|telas|tejidos|dril|denim|indigo|tintoreria textil|estampado textil", "1312"),
            (r"distribuid|distribuc|comercializad|comercializac|mayorist", "4690"),
            (r"\b(consultor|asesor|asesoria|consultoria|advisory|estrategi)\b", "7020"),
        ]

        # Dynamic pattern matching: pulls from in-memory DB cache if loaded, falls back to seed list
        active_patterns = patterns
        try:
            try:
                from src.domain.taxonomy.isic_index import GLOBAL_ISIC_INDEX
            except ImportError:
                from backend.src.domain.taxonomy.isic_index import GLOBAL_ISIC_INDEX
            dyn = GLOBAL_ISIC_INDEX.get_patterns()
            if dyn:
                active_patterns = dyn
        except Exception:
            pass

        for pat, code in active_patterns:
            if re.search(pat, text):
                return cls.from_code(code)

        # Dynamic semantic search using Universal ISIC Index
        try:
            try:
                from src.domain.taxonomy.isic_index import GLOBAL_ISIC_INDEX
            except ImportError:
                from backend.src.domain.taxonomy.isic_index import GLOBAL_ISIC_INDEX
            entry = GLOBAL_ISIC_INDEX.resolve_best_match(text)
            if entry:
                return cls.from_code(entry.code)
        except Exception:
            pass

        # Default fallback: Actividades de consultoría de gestión empresarial y servicios B2B
        return cls.from_code("7020")

    def to_display_string(self) -> str:
        return f"CIIU {self.code}: {self.sector_macro}"

    def to_full_audit_string(self) -> str:
        return f"CIIU {self.code} — {self.description}"
