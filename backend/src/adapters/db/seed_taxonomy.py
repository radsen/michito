"""
Taxonomy Seeder & Knowledge Graph Initializer for Michito Engine.
Populates persistent database tables with:
1. Supported LatAm territories & metropolitan clusters (🇨🇴, 🇩🇴, 🇪🇨)
2. Executive decision maker titles & cross-country aliases
3. Universal economic sectors & CIIU activity codes
"""

import sys
import os
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select

# Ensure backend root is on sys.path
BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from src.adapters.db.models import (
    Base,
    TaxonomyLocationModel,
    TaxonomyRoleModel,
    TaxonomySectorModel,
)


LOCATION_SEEDS: List[Dict[str, Any]] = [
    # --- 🇨🇴 COLOMBIA ---
    {
        "location_id": "co_bogota_dc",
        "country_code": "CO",
        "country_name": "Colombia",
        "region_name": "Cundinamarca",
        "city_name": "Bogotá D.C.",
        "aliases": ["Bogotá", "Distrito Capital", "Sabana de Bogotá", "Chía", "Cota", "Soacha", "Funza", "Mosquera", "Madrid", "Siberia"],
        "registry_sources": ["rues", "camara_bogota", "secop", "dian"],
        "is_active": True,
    },
    {
        "location_id": "co_antioquia_medellin",
        "country_code": "CO",
        "country_name": "Colombia",
        "region_name": "Antioquia",
        "city_name": "Medellín",
        "aliases": ["Medellín", "Valle de Aburrá", "Envigado", "Itagüí", "Sabaneta", "Bello", "Rionegro", "Oriente Antioqueño", "Guarne", "Girardota"],
        "registry_sources": ["rues", "camara_medellin", "camara_aburra_sur", "secop", "dian"],
        "is_active": True,
    },
    {
        "location_id": "co_valle_cali",
        "country_code": "CO",
        "country_name": "Colombia",
        "region_name": "Valle del Cauca",
        "city_name": "Cali",
        "aliases": ["Cali", "Santiago de Cali", "Yumbo", "Jamundí", "Palmira", "Buenaventura", "Buga", "Tuluá"],
        "registry_sources": ["rues", "camara_cali", "secop", "dian"],
        "is_active": True,
    },
    {
        "location_id": "co_atlantico_barranquilla",
        "country_code": "CO",
        "country_name": "Colombia",
        "region_name": "Atlántico",
        "city_name": "Barranquilla",
        "aliases": ["Barranquilla", "Soledad", "Puerto Colombia", "Malambo", "Costa Caribe"],
        "registry_sources": ["rues", "camara_barranquilla", "secop", "dian"],
        "is_active": True,
    },
    {
        "location_id": "co_santander_bucaramanga",
        "country_code": "CO",
        "country_name": "Colombia",
        "region_name": "Santander",
        "city_name": "Bucaramanga",
        "aliases": ["Bucaramanga", "Floridablanca", "Girón", "Piedecuesta", "Barrancabermeja"],
        "registry_sources": ["rues", "camara_bucaramanga", "secop", "dian"],
        "is_active": True,
    },
    {
        "location_id": "co_bolivar_cartagena",
        "country_code": "CO",
        "country_name": "Colombia",
        "region_name": "Bolívar",
        "city_name": "Cartagena",
        "aliases": ["Cartagena", "Cartagena de Indias", "Mamonal", "Turbaco", "Costa Caribe"],
        "registry_sources": ["rues", "camara_cartagena", "secop", "dian"],
        "is_active": True,
    },
    {
        "location_id": "co_risaralda_pereira",
        "country_code": "CO",
        "country_name": "Colombia",
        "region_name": "Risaralda",
        "city_name": "Pereira",
        "aliases": ["Pereira", "Dosquebradas", "Eje Cafetero", "Santa Rosa de Cabal"],
        "registry_sources": ["rues", "camara_pereira", "secop", "dian"],
        "is_active": True,
    },
    {
        "location_id": "co_caldas_manizales",
        "country_code": "CO",
        "country_name": "Colombia",
        "region_name": "Caldas",
        "city_name": "Manizales",
        "aliases": ["Manizales", "Villamaría", "Eje Cafetero", "Chinchiná"],
        "registry_sources": ["rues", "camara_manizales", "secop", "dian"],
        "is_active": True,
    },
    {
        "location_id": "co_quindio_armenia",
        "country_code": "CO",
        "country_name": "Colombia",
        "region_name": "Quindío",
        "city_name": "Armenia",
        "aliases": ["Armenia", "Calarcá", "Eje Cafetero", "La Tebaida", "Montenegro"],
        "registry_sources": ["rues", "camara_armenia", "secop", "dian"],
        "is_active": True,
    },
    {
        "location_id": "co_tolima_ibague",
        "country_code": "CO",
        "country_name": "Colombia",
        "region_name": "Tolima",
        "city_name": "Ibagué",
        "aliases": ["Ibagué", "Espinal"],
        "registry_sources": ["rues", "camara_ibague", "secop", "dian"],
        "is_active": True,
    },
    {
        "location_id": "co_norte_santander_cucuta",
        "country_code": "CO",
        "country_name": "Colombia",
        "region_name": "Norte de Santander",
        "city_name": "Cúcuta",
        "aliases": ["Cúcuta", "Los Patios", "Villa del Rosario"],
        "registry_sources": ["rues", "camara_cucuta", "secop", "dian"],
        "is_active": True,
    },

    # --- 🇩🇴 DOMINICAN REPUBLIC ---
    {
        "location_id": "do_distrito_nacional",
        "country_code": "DO",
        "country_name": "República Dominicana",
        "region_name": "Distrito Nacional",
        "city_name": "Santo Domingo",
        "aliases": ["Santo Domingo", "Distrito Nacional", "Piantini", "Naco", "Bella Vista", "Evaristo Morales", "Zona Colonial", "Santo Domingo Este", "Santo Domingo Oeste"],
        "registry_sources": ["dgcp", "dgii", "onapi"],
        "is_active": True,
    },
    {
        "location_id": "do_santiago",
        "country_code": "DO",
        "country_name": "República Dominicana",
        "region_name": "Santiago",
        "city_name": "Santiago de los Caballeros",
        "aliases": ["Santiago", "Santiago de los Caballeros", "El Cibao", "Tamboril", "Villa González"],
        "registry_sources": ["dgcp", "dgii", "onapi"],
        "is_active": True,
    },
    {
        "location_id": "do_la_altagracia",
        "country_code": "DO",
        "country_name": "República Dominicana",
        "region_name": "La Altagracia",
        "city_name": "Punta Cana",
        "aliases": ["Punta Cana", "Bávaro", "Higüey", "Cap Cana", "Verón"],
        "registry_sources": ["dgcp", "dgii", "onapi"],
        "is_active": True,
    },
    {
        "location_id": "do_la_romana",
        "country_code": "DO",
        "country_name": "República Dominicana",
        "region_name": "La Romana",
        "city_name": "La Romana",
        "aliases": ["La Romana", "Casa de Campo", "Bayahíbe"],
        "registry_sources": ["dgcp", "dgii", "onapi"],
        "is_active": True,
    },
    {
        "location_id": "do_san_cristobal",
        "country_code": "DO",
        "country_name": "República Dominicana",
        "region_name": "San Cristóbal",
        "city_name": "San Cristóbal",
        "aliases": ["San Cristóbal", "Bajos de Haina", "Haina", "Zona Industrial Haina"],
        "registry_sources": ["dgcp", "dgii", "onapi"],
        "is_active": True,
    },

    # --- 🇪🇨 ECUADOR ---
    {
        "location_id": "ec_pichincha_quito",
        "country_code": "EC",
        "country_name": "Ecuador",
        "region_name": "Pichincha",
        "city_name": "Quito",
        "aliases": ["Quito", "Distrito Metropolitano de Quito", "Cumbayá", "Tumbaco", "Los Chillos", "Valle de Cumbayá", "Calderón"],
        "registry_sources": ["sercop", "supercias", "sri"],
        "is_active": True,
    },
    {
        "location_id": "ec_guayas_guayaquil",
        "country_code": "EC",
        "country_name": "Ecuador",
        "region_name": "Guayas",
        "city_name": "Guayaquil",
        "aliases": ["Guayaquil", "Samborondón", "Durán", "Daule", "Vía a la Costa", "La Puntilla"],
        "registry_sources": ["sercop", "supercias", "sri"],
        "is_active": True,
    },
    {
        "location_id": "ec_azuay_cuenca",
        "country_code": "EC",
        "country_name": "Ecuador",
        "region_name": "Azuay",
        "city_name": "Cuenca",
        "aliases": ["Cuenca", "Azuay", "Gualaceo", "Challuabamba"],
        "registry_sources": ["sercop", "supercias", "sri"],
        "is_active": True,
    },
    {
        "location_id": "ec_manabi_manta",
        "country_code": "EC",
        "country_name": "Ecuador",
        "region_name": "Manabí",
        "city_name": "Manta",
        "aliases": ["Manta", "Portoviejo", "Montecristi"],
        "registry_sources": ["sercop", "supercias", "sri"],
        "is_active": True,
    },
    {
        "location_id": "ec_el_oro_machala",
        "country_code": "EC",
        "country_name": "Ecuador",
        "region_name": "El Oro",
        "city_name": "Machala",
        "aliases": ["Machala", "Puerto Bolívar", "Pasaje", "Santa Rosa"],
        "registry_sources": ["sercop", "supercias", "sri"],
        "is_active": True,
    },
]


ROLE_SEEDS: List[Dict[str, Any]] = [
    {
        "role_id": "general_management",
        "canonical_title": "Gerente General",
        "seniority_level": "c_level",
        "functional_domain": "executive",
        "country_code": "ALL",
        "aliases": [
            "CEO", "Presidente Ejecutivo", "Director General", "Socio Director",
            "Managing Director", "Representante Legal", "Country Manager", "Administrador Delegado", "Gerente"
        ],
        "applicable_sectors": ["all"],
        "usage_count": 500,
        "is_active": True,
    },
    {
        "role_id": "operations_leadership",
        "canonical_title": "Director de Operaciones",
        "seniority_level": "director",
        "functional_domain": "operations",
        "country_code": "ALL",
        "aliases": [
            "COO", "Chief Operating Officer", "Gerente de Operaciones", "Vicepresidente de Operaciones",
            "Operations Director", "Jefe de Operaciones", "Líder de Operaciones", "Gerente de Planta"
        ],
        "applicable_sectors": ["logistics", "manufacturing", "food_agriculture", "construction", "services"],
        "usage_count": 350,
        "is_active": True,
    },
    {
        "role_id": "procurement_supply_chain",
        "canonical_title": "Director de Compras y Abastecimiento",
        "seniority_level": "director",
        "functional_domain": "procurement",
        "country_code": "ALL",
        "aliases": [
            "Gerente de Compras", "Director de Cadena de Suministro", "Supply Chain Director",
            "Jefe de Compras", "Encargado de Compras", "Gerente de Abastecimiento", "Director de Supply Chain",
            "Gerente de Adquisiciones", "Jefe de Suministros", "Purchasing Manager"
        ],
        "applicable_sectors": ["food_agriculture", "construction", "manufacturing", "logistics", "healthcare"],
        "usage_count": 420,
        "is_active": True,
    },
    {
        "role_id": "finance_solvency",
        "canonical_title": "Director Financiero",
        "seniority_level": "c_level",
        "functional_domain": "finance",
        "country_code": "ALL",
        "aliases": [
            "CFO", "Chief Financial Officer", "Gerente Financiero", "Vicepresidente Financiero",
            "Director de Finanzas", "Gerente Administrativo y Financiero", "Director Administrativo"
        ],
        "applicable_sectors": ["all"],
        "usage_count": 280,
        "is_active": True,
    },
    {
        "role_id": "technology_security",
        "canonical_title": "Director de Tecnología",
        "seniority_level": "c_level",
        "functional_domain": "technology",
        "country_code": "ALL",
        "aliases": [
            "CTO", "Chief Technology Officer", "Gerente de TI", "Director de Sistemas",
            "Director de Ciberseguridad", "CISO", "Head of IT", "Gerente de Transformación Digital"
        ],
        "applicable_sectors": ["tech_software", "financial", "retail", "services"],
        "usage_count": 220,
        "is_active": True,
    },
    {
        "role_id": "commercial_sales_growth",
        "canonical_title": "Director Comercial",
        "seniority_level": "director",
        "functional_domain": "commercial",
        "country_code": "ALL",
        "aliases": [
            "VP de Ventas", "Vicepresidente Comercial", "Gerente Comercial", "Head of Growth",
            "Director de Ventas", "Chief Commercial Officer", "Gerente de Negocios", "Director de Cuentas"
        ],
        "applicable_sectors": ["all"],
        "usage_count": 310,
        "is_active": True,
    },
    {
        "role_id": "human_capital_people",
        "canonical_title": "Director de Gestión Humana",
        "seniority_level": "director",
        "functional_domain": "hr",
        "country_code": "ALL",
        "aliases": [
            "Director de Recursos Humanos", "Gerente de Talento Humano", "People Operations Director",
            "Chief People Officer", "CHRO", "Gerente de RRHH", "Líder de Cultura y Talento"
        ],
        "applicable_sectors": ["services", "bpo", "corporate", "all"],
        "usage_count": 190,
        "is_active": True,
    },
    {
        "role_id": "project_construction_management",
        "canonical_title": "Director de Obra y Proyectos",
        "seniority_level": "director",
        "functional_domain": "projects",
        "country_code": "ALL",
        "aliases": [
            "Gerente de Proyectos", "Director de Proyecto", "Residente de Obra", "Project Manager",
            "Gerente de Construcción", "Ingeniero Residente", "Director de Infraestructura"
        ],
        "applicable_sectors": ["construction_infrastructure", "engineering", "real_estate"],
        "usage_count": 260,
        "is_active": True,
    },
    {
        "role_id": "logistics_warehouse_leadership",
        "canonical_title": "Director de Logística y Centros de Distribución",
        "seniority_level": "director",
        "functional_domain": "logistics",
        "country_code": "ALL",
        "aliases": [
            "Gerente de Logística", "Jefe de Almacén", "Gerente de CEDI", "Director de Transporte",
            "Jefe de Despachos", "Logistics Manager", "Jefe de Distribución"
        ],
        "applicable_sectors": ["logistics_warehousing", "retail", "manufacturing", "food_agriculture"],
        "usage_count": 340,
        "is_active": True,
    },
    {
        "role_id": "hospitality_food_beverage",
        "canonical_title": "Gerente de Alimentos y Bebidas",
        "seniority_level": "gerente",
        "functional_domain": "hospitality",
        "country_code": "ALL",
        "aliases": [
            "F&B Manager", "Director de Alimentos y Bebidas", "Chef Ejecutivo",
            "Gerente de Restaurante", "Jefe de Cocina", "Gerente de Hotel", "Director de Operaciones Hoteleras"
        ],
        "applicable_sectors": ["food_agriculture", "hospitality"],
        "usage_count": 170,
        "is_active": True,
    },
]


SECTOR_SEEDS: List[Dict[str, Any]] = [
    {
        "sector_id": "food_agriculture",
        "sector_name": "Alimentos, Bebidas & Agroindustria",
        "country_code": "ALL",
        "ciiu_codes": ["C1011", "C1012", "C1020", "C1030", "C1040", "C1051", "C1052", "C1081", "C1089", "C1101", "G4631"],
        "keywords_include": [
            "alimentos", "agroindustria", "lacteos", "carnicos", "congelados", "avicola",
            "restaurantes", "hoteles", "distribuidora", "viveres", "conservas", "granos", "bebidas", "embutidos"
        ],
        "keywords_exclude_defaults": ["panaderia de barrio", "tienda de esquina", "comida rapida callejera"],
        "usage_count": 150,
        "is_active": True,
    },
    {
        "sector_id": "construction_infrastructure",
        "sector_name": "Construcción, Obras Civiles & Materiales",
        "country_code": "ALL",
        "ciiu_codes": ["F4111", "F4112", "F4210", "F4220", "F4290", "F4311", "F4321", "F4330", "G4663"],
        "keywords_include": [
            "construccion", "obra civil", "materiales", "cemento", "concreto", "acero", "estructuras",
            "contratista", "arquitectura", "ingenieria civil", "ferreteria industrial", "agregados", "acabados"
        ],
        "keywords_exclude_defaults": ["ferreteria menor", "plomeria domiciliaria", "vidrieria de barrio"],
        "usage_count": 180,
        "is_active": True,
    },
    {
        "sector_id": "logistics_warehousing",
        "sector_name": "Logística, Transporte de Carga & CEDI",
        "country_code": "ALL",
        "ciiu_codes": ["H4923", "H5011", "H5120", "H5210", "H5224", "H5229", "H5310"],
        "keywords_include": [
            "logistica", "transporte pesado", "flota", "carga seca", "carga refrigerada", "almacenamiento",
            "bodega", "cedi", "parque industrial", "agenciamiento aduanero", "importacion", "exportacion", "3pl"
        ],
        "keywords_exclude_defaults": ["mudanzas", "trasteos", "taxis", "transporte escolar", "mensajeria en moto"],
        "usage_count": 210,
        "is_active": True,
    },
    {
        "sector_id": "tech_software_telecom",
        "sector_name": "Software, Telecomunicaciones & Cloud B2B",
        "country_code": "ALL",
        "ciiu_codes": ["J5820", "J6110", "J6120", "J6190", "J6201", "J6202", "J6209", "J6311"],
        "keywords_include": [
            "software", "saas", "cloud", "ciberseguridad", "erp", "crm", "facturacion electronica",
            "apis", "infraestructura ti", "desarrollo", "telecomunicaciones", "servidores", "inteligencia artificial"
        ],
        "keywords_exclude_defaults": ["cafe internet", "reparacion de celulares", "venta de fundas"],
        "usage_count": 240,
        "is_active": True,
    },
    {
        "sector_id": "manufacturing_industrial",
        "sector_name": "Manufactura, Empaques & Químicos",
        "country_code": "ALL",
        "ciiu_codes": ["C1311", "C1701", "C1702", "C2011", "C2021", "C2029", "C2220", "C2511", "C2819"],
        "keywords_include": [
            "manufactura", "empaques", "carton", "plastico", "quimicos", "polimeros", "resinas",
            "metalmecanica", "maquinaria industrial", "transformacion", "materia prima", "textiles"
        ],
        "keywords_exclude_defaults": ["taller artesanal", "manualidades", "costura domiciliaria"],
        "usage_count": 130,
        "is_active": True,
    },
    {
        "sector_id": "healthcare_pharma",
        "sector_name": "Salud, Dispositivos Médicos & Farmacéutica",
        "country_code": "ALL",
        "ciiu_codes": ["C2100", "G4646", "Q8610", "Q8621", "Q8699"],
        "keywords_include": [
            "farmaceutica", "dispositivos medicos", "insumos medicos", "laboratorio clinico", "clinica",
            "hospital", "ips", "equipos biomedicos", "medicamentos", "odontologia especializada"
        ],
        "keywords_exclude_defaults": ["drogueria de barrio", "tienda naturista"],
        "usage_count": 120,
        "is_active": True,
    },
    {
        "sector_id": "corporate_real_estate",
        "sector_name": "Espacios Corporativos & Sedes Empresariales",
        "country_code": "ALL",
        "ciiu_codes": ["L6810", "L6820"],
        "keywords_include": [
            "oficinas", "sedes corporativas", "coworking", "edificio empresarial", "milla de oro",
            "chico", "piantini", "arriendo corporativo", "espacio llave en mano", "salas de juntas"
        ],
        "keywords_exclude_defaults": ["habitacion compartida", "apartamento residencial", "pension"],
        "usage_count": 190,
        "is_active": True,
    },
    {
        "sector_id": "facility_security_services",
        "sector_name": "Facility Management, Seguridad & Aseo",
        "country_code": "ALL",
        "ciiu_codes": ["N8110", "N8121", "N8129", "N8010", "N8020"],
        "keywords_include": [
            "facility management", "seguridad privada", "vigilancia", "aseo corporativo", "limpieza industrial",
            "mantenimiento locativo", "porteria", "control de acceso"
        ],
        "keywords_exclude_defaults": ["empleada domestica", "lavado de autos ambulante"],
        "usage_count": 160,
        "is_active": True,
    },
    {
        "sector_id": "energy_fuels_utilities",
        "sector_name": "Energía, Combustibles & Flotas Pesadas",
        "country_code": "ALL",
        "ciiu_codes": ["D3511", "D3512", "D3520", "G4661"],
        "keywords_include": [
            "combustible", "diesel", "gasolina", "acpm", "lubricantes", "distribucion mayorista",
            "energia solar", "gas natural", "estaciones de servicio", "flota pesada"
        ],
        "keywords_exclude_defaults": ["lavado de carros", "cambio de aceite informal"],
        "usage_count": 140,
        "is_active": True,
    },
    {
        "sector_id": "legal_financial_services",
        "sector_name": "Servicios Financieros, Legales & Gestión de Cartera",
        "country_code": "ALL",
        "ciiu_codes": ["K6419", "K6499", "M6910", "M6920", "N8291"],
        "keywords_include": [
            "gestion de cartera", "cobranza", "debida diligencia", "auditoria", "firmas de abogados",
            "banca de inversion", "factoring", "credito empresarial", "asesoria tributaria"
        ],
        "keywords_exclude_defaults": ["prestamos gota a gota", "casas de empeño"],
        "usage_count": 110,
        "is_active": True,
    },
]


def seed_all_taxonomy(session: Session, reset: bool = False) -> Dict[str, int]:
    """
    Seeds locations, roles, and sectors into database session.
    Idempotent: updates existing records or inserts new ones.
    """
    # 1. Locations
    locations_count = 0
    for loc_data in LOCATION_SEEDS:
        loc = session.get(TaxonomyLocationModel, loc_data["location_id"])
        if not loc:
            loc = TaxonomyLocationModel(**loc_data)
            session.add(loc)
        else:
            for k, v in loc_data.items():
                setattr(loc, k, v)
        locations_count += 1

    # 2. Roles
    roles_count = 0
    for role_data in ROLE_SEEDS:
        role = session.get(TaxonomyRoleModel, role_data["role_id"])
        if not role:
            role = TaxonomyRoleModel(**role_data)
            session.add(role)
        else:
            for k, v in role_data.items():
                setattr(role, k, v)
        roles_count += 1

    # 3. Sectors
    sectors_count = 0
    for sec_data in SECTOR_SEEDS:
        sec = session.get(TaxonomySectorModel, sec_data["sector_id"])
        if not sec:
            sec = TaxonomySectorModel(**sec_data)
            session.add(sec)
        else:
            for k, v in sec_data.items():
                setattr(sec, k, v)
        sectors_count += 1

    session.commit()
    return {
        "locations": locations_count,
        "roles": roles_count,
        "sectors": sectors_count,
    }


if __name__ == "__main__":
    from src.adapters.db.sql_order_adapter import SqlOrderAdapter
    adapter = SqlOrderAdapter()
    with adapter._get_session() as s:
        counts = seed_all_taxonomy(s)
        print("✅ Taxonomy seeding complete:")
        print(f"• Locations: {counts['locations']}")
        print(f"• Roles:     {counts['roles']}")
        print(f"• Sectors:   {counts['sectors']}")

