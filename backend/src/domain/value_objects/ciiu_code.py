"""
CIIU (Clasificación Industrial Internacional Uniforme) Value Object
Based on DANE CIIU Rev. 4 A.C. (Adaptación para Colombia).
Provides official economic activity taxonomy, sector categorization, and validation.
"""

from dataclasses import dataclass
import re
from typing import Dict, Optional, Tuple

OFFICIAL_CIIU_CATALOG: Dict[str, Dict[str, str]] = {
    # --- TECNOLOGÍA & INFORMACIÓN ---
    "6201": {
        "code": "6201",
        "description": "Actividades de desarrollo de sistemas informáticos (planificación, análisis, diseño, programación, pruebas)",
        "sector_macro": "Tecnología, Software & Analítica",
        "tinkko_fit": "Alto (Equipos de desarrollo y producto que buscan oficinas llave en mano con conectividad de alta velocidad)"
    },
    "6202": {
        "code": "6202",
        "description": "Actividades de consultoría informática y actividades de administración de instalaciones informáticas",
        "sector_macro": "Tecnología, Software & Analítica",
        "tinkko_fit": "Alto (Consultoras tech con presencia híbrida y necesidades de salas de juntas ejecutivas)"
    },
    "6209": {
        "code": "6209",
        "description": "Otras actividades de tecnologías de información y actividades de servicios informáticos",
        "sector_macro": "Tecnología, Software & Analítica",
        "tinkko_fit": "Alto (Empresas tech emergentes y soporte regional)"
    },
    "6311": {
        "code": "6311",
        "description": "Procesamiento de datos, alojamiento (hosting) y actividades conexas",
        "sector_macro": "Tecnología, Software & Analítica",
        "tinkko_fit": "Alto (Infraestructura digital y analítica de datos)"
    },

    # --- CONSULTORÍA & GESTIÓN EMPRESARIAL ---
    "7020": {
        "code": "7020",
        "description": "Actividades de consultoría de gestión empresarial y estratégica",
        "sector_macro": "Consultoría Empresarial & Gestión",
        "tinkko_fit": "Muy Alto (Consultores estratégicos que requieren sedes corporativas de alta gama en Milla de Oro y Calle 100)"
    },
    "7010": {
        "code": "7010",
        "description": "Actividades de administración empresarial y sedes principales de holdings",
        "sector_macro": "Consultoría Empresarial & Gestión",
        "tinkko_fit": "Muy Alto (Sedes corporativas para directivos)"
    },

    # --- SERVICIOS LEGALES & FINANCIEROS ---
    "6910": {
        "code": "6910",
        "description": "Actividades jurídicas y asesoría legal corporativa",
        "sector_macro": "Servicios Legales & Corporativos",
        "tinkko_fit": "Muy Alto (Bufetes de abogados que valoran privacidad, acústica y salas de reuniones de alto nivel)"
    },
    "6920": {
        "code": "6920",
        "description": "Actividades de contabilidad, teneduría de libros, auditoría financiera y asesoría tributaria",
        "sector_macro": "Servicios Financieros & Contables",
        "tinkko_fit": "Alto (Firmas de auditoría que requieren sedes centrales y estaciones de trabajo flexibles)"
    },
    "6499": {
        "code": "6499",
        "description": "Otras actividades de servicios financieros (Fintech, estructuración y fondos)",
        "sector_macro": "Servicios Financieros & Contables",
        "tinkko_fit": "Muy Alto (Fintechs y bancas de inversión)"
    },

    # --- INGENIERÍA, ARQUITECTURA & PROYECTOS ---
    "7110": {
        "code": "7110",
        "description": "Actividades de arquitectura e ingeniería y actividades conexas de consultoría técnica",
        "sector_macro": "Ingeniería, Infraestructura & Consultoría Técnica",
        "tinkko_fit": "Alto (Equipos de interventoría y diseño técnico en expansión)"
    },
    "7120": {
        "code": "7120",
        "description": "Ensayos y análisis técnicos",
        "sector_macro": "Ingeniería, Infraestructura & Consultoría Técnica",
        "tinkko_fit": "Medio-Alto"
    },

    # --- INMOBILIARIO & FACILITY SERVICES ---
    "6810": {
        "code": "6810",
        "description": "Actividades inmobiliarias realizadas con bienes propios o arrendados",
        "sector_macro": "Inmobiliario & Gestión de Espacios",
        "tinkko_fit": "Alto (Empresas de desarrollo inmobiliario y fondos de rentas)"
    },
    "6820": {
        "code": "6820",
        "description": "Actividades inmobiliarias realizadas a cambio de una retribución o por contrata",
        "sector_macro": "Inmobiliario & Gestión de Espacios",
        "tinkko_fit": "Alto"
    },
    "8110": {
        "code": "8110",
        "description": "Actividades combinadas de apoyo a instalaciones (Facility Management)",
        "sector_macro": "Facility Management & Servicios Operativos",
        "tinkko_fit": "Medio-Alto (Operadores de servicios corporativos)"
    },

    # --- SALUD & DISPOSITIVOS MÉDICOS ---
    "3250": {
        "code": "3250",
        "description": "Fabricación e importación de instrumentos, aparatos y materiales médicos y odontológicos",
        "sector_macro": "Salud & Dispositivos Médicos",
        "tinkko_fit": "Alto (Equipos comerciales y administrativos de multinacionales de salud)"
    },
    "4645": {
        "code": "4645",
        "description": "Comercio al por mayor de productos farmacéuticos, medicinales y cosméticos",
        "sector_macro": "Salud & Dispositivos Médicos",
        "tinkko_fit": "Alto"
    },

    # --- COMERCIO AL POR MAYOR & TECNOLOGÍA ---
    "4651": {
        "code": "4651",
        "description": "Comercio al por mayor de computadores, equipo periférico y programas de informática",
        "sector_macro": "Comercio al por Mayor de Tecnología & Equipos",
        "tinkko_fit": "Alto (Distribuidores corporativos que requieren oficinas comerciales)"
    },
    "4659": {
        "code": "4659",
        "description": "Comercio al por mayor de otra maquinaria y equipo",
        "sector_macro": "Comercio al por Mayor & Maquinaria",
        "tinkko_fit": "Medio-Alto"
    },

    # --- LOGÍSTICA & TRANSPORTE ---
    "4923": {
        "code": "4923",
        "description": "Transporte de carga por carretera",
        "sector_macro": "Logística, Carga & Comercio Exterior",
        "tinkko_fit": "Medio-Alto (Sedes administrativas de empresas de transporte)"
    },
    "5229": {
        "code": "5229",
        "description": "Otras actividades de transporte conexas (Agencias de aduanas y forwarders)",
        "sector_macro": "Logística, Carga & Comercio Exterior",
        "tinkko_fit": "Alto (Agencias aduaneras que operan en torres corporativas)"
    },

    # --- PUBLICIDAD, EDITORIAL & MEDIOS ---
    "7310": {
        "code": "7310",
        "description": "Publicidad y agencias de medios",
        "sector_macro": "Publicidad, Creatividad & Medios",
        "tinkko_fit": "Muy Alto (Agencias creativas que buscan ambiente colaborativo)"
    },
    "5819": {
        "code": "5819",
        "description": "Otros trabajos de edición y publicaciones",
        "sector_macro": "Editorial & Comunicaciones",
        "tinkko_fit": "Medio-Alto"
    }
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
        """
        text = f"{company_name} {email} {raw_desc}".lower()

        patterns = [
            (r"software|analyt|data|tech|digital|sistemas|program|cloud|\bia\b|\bai\b|ciber", "6201"),
            (r"consult|asesor|advis|estrateg|gestion|management", "7020"),
            (r"abogad|legal|jurid|derecho|leyes|litig", "6910"),
            (r"contab|auditor|financ|tributar|revisoria|impuesto", "6920"),
            (r"fintech|invers|fondos|credito|valores", "6499"),
            (r"arquitect|ingenier|civil|obras|interventor|diseno tecnico", "7110"),
            (r"facility|limpieza|aseo|mantenimiento locativo|seguridad fisica|conserj", "8110"),
            (r"inmobiliari|bienes raices|propiedad horizontal|arrendamiento", "6810"),
            (r"publicid|marketing|btl|eventos|comunicacion|medios|agencia", "7310"),
            (r"medical|salud|ips|clinic|farmaceut|biomed|odontol|dispositiv", "3250"),
            (r"comput|hardware|redes|servidores|telecom", "4651"),
            (r"logist|transport|carga|aduan|fletes|almacen", "4923"),
            (r"maquinaria|equipos|repuestos|industrial", "4659"),
        ]

        for pat, code in patterns:
            if re.search(pat, text):
                return cls.from_code(code)

        # Default fallback: Actividades de consultoría de gestión empresarial y servicios B2B
        return cls.from_code("7020")

    def to_display_string(self) -> str:
        return f"CIIU {self.code}: {self.sector_macro}"

    def to_full_audit_string(self) -> str:
        return f"CIIU {self.code} — {self.description}"
