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
        "concentric_rings": {
            "ring_0": ["Bogotá", "Distrito Capital de Bogotá"],
            "ring_1": ["Chía", "Cota", "Soacha", "Cajicá"],
            "ring_2": ["Funza", "Mosquera", "Madrid", "Zipaquirá", "Sopó", "Facatativá"],
        },
        "expansion_rules": {
            "default_scope": "metro_area",
            "max_allowed_ring": 1,
            "min_quota_threshold_percent": 100,
        },
        "registry_sources": ["secop", "supersociedades", "rues", "dian"],
        "is_active": True,
    },
    {
        "location_id": "co_antioquia_medellin",
        "country_code": "CO",
        "country_name": "Colombia",
        "region_name": "Antioquia",
        "city_name": "Medellín",
        "aliases": ["Medellín", "Valle de Aburrá", "Envigado", "Itagüí", "Sabaneta", "Bello", "Rionegro", "Oriente Antioqueño", "Guarne", "Girardota"],
        "concentric_rings": {
            "ring_0": ["Medellín"],
            "ring_1": ["Envigado", "Itagüí", "Sabaneta", "Bello", "La Estrella", "Caldas", "Copacabana", "Girardota"],
            "ring_2": ["Rionegro", "Guarne", "Marinilla", "El Retiro"],
            "ring_3": ["Barbosa", "La Ceja", "Carmen de Viboral"],
        },
        "expansion_rules": {
            "default_scope": "metro_area",
            "max_allowed_ring": 1,
            "min_quota_threshold_percent": 100,
        },
        "registry_sources": ["secop", "supersociedades", "rues", "dian"],
        "is_active": True,
    },
    {
        "location_id": "co_valle_cali",
        "country_code": "CO",
        "country_name": "Colombia",
        "region_name": "Valle del Cauca",
        "city_name": "Cali",
        "aliases": ["Cali", "Santiago de Cali", "Yumbo", "Jamundí", "Palmira", "Buenaventura", "Buga", "Tuluá"],
        "concentric_rings": {
            "ring_0": ["Cali", "Santiago de Cali"],
            "ring_1": ["Yumbo", "Jamundí", "Palmira"],
            "ring_2": ["Buga", "Tuluá", "Candelaria", "Pradera"],
        },
        "expansion_rules": {
            "default_scope": "metro_area",
            "max_allowed_ring": 1,
            "min_quota_threshold_percent": 100,
        },
        "registry_sources": ["secop", "supersociedades", "rues", "dian"],
        "is_active": True,
    },
    {
        "location_id": "co_atlantico_barranquilla",
        "country_code": "CO",
        "country_name": "Colombia",
        "region_name": "Atlántico",
        "city_name": "Barranquilla",
        "aliases": ["Barranquilla", "Soledad", "Puerto Colombia", "Malambo", "Costa Caribe"],
        "concentric_rings": {
            "ring_0": ["Barranquilla"],
            "ring_1": ["Soledad", "Puerto Colombia", "Malambo"],
            "ring_2": ["Galapa", "Baranoa", "Sabanalarga"],
        },
        "expansion_rules": {
            "default_scope": "metro_area",
            "max_allowed_ring": 1,
            "min_quota_threshold_percent": 100,
        },
        "registry_sources": ["secop", "supersociedades", "rues", "dian"],
        "is_active": True,
    },
    {
        "location_id": "co_santander_bucaramanga",
        "country_code": "CO",
        "country_name": "Colombia",
        "region_name": "Santander",
        "city_name": "Bucaramanga",
        "aliases": ["Bucaramanga", "Floridablanca", "Girón", "Piedecuesta", "Barrancabermeja"],
        "concentric_rings": {
            "ring_0": ["Bucaramanga"],
            "ring_1": ["Floridablanca", "Girón", "Piedecuesta"],
            "ring_2": ["Lebrija", "Barrancabermeja"],
        },
        "expansion_rules": {
            "default_scope": "metro_area",
            "max_allowed_ring": 1,
            "min_quota_threshold_percent": 100,
        },
        "registry_sources": ["secop", "supersociedades", "rues", "dian"],
        "is_active": True,
    },
    {
        "location_id": "co_bolivar_cartagena",
        "country_code": "CO",
        "country_name": "Colombia",
        "region_name": "Bolívar",
        "city_name": "Cartagena",
        "aliases": ["Cartagena", "Cartagena de Indias", "Mamonal", "Turbaco", "Costa Caribe"],
        "concentric_rings": {
            "ring_0": ["Cartagena", "Cartagena de Indias"],
            "ring_1": ["Turbaco", "Arjona", "Turbana"],
            "ring_2": ["Pasacaballos", "Santa Rosa de Lima"],
        },
        "expansion_rules": {
            "default_scope": "metro_area",
            "max_allowed_ring": 1,
            "min_quota_threshold_percent": 100,
        },
        "registry_sources": ["secop", "supersociedades", "rues", "dian"],
        "is_active": True,
    },
    {
        "location_id": "co_risaralda_pereira",
        "country_code": "CO",
        "country_name": "Colombia",
        "region_name": "Risaralda",
        "city_name": "Pereira",
        "aliases": ["Pereira", "Dosquebradas", "Eje Cafetero", "Santa Rosa de Cabal"],
        "concentric_rings": {
            "ring_0": ["Pereira"],
            "ring_1": ["Dosquebradas", "Santa Rosa de Cabal"],
            "ring_2": ["Cartago", "La Virginia"],
        },
        "expansion_rules": {
            "default_scope": "metro_area",
            "max_allowed_ring": 1,
            "min_quota_threshold_percent": 100,
        },
        "registry_sources": ["secop", "supersociedades", "rues", "dian"],
        "is_active": True,
    },
    {
        "location_id": "co_caldas_manizales",
        "country_code": "CO",
        "country_name": "Colombia",
        "region_name": "Caldas",
        "city_name": "Manizales",
        "aliases": ["Manizales", "Villamaría", "Eje Cafetero", "Chinchiná"],
        "concentric_rings": {
            "ring_0": ["Manizales"],
            "ring_1": ["Villamaría", "Chinchiná", "Neira", "Palestina"],
        },
        "expansion_rules": {
            "default_scope": "metro_area",
            "max_allowed_ring": 1,
            "min_quota_threshold_percent": 100,
        },
        "registry_sources": ["secop", "supersociedades", "rues", "dian"],
        "is_active": True,
    },
    {
        "location_id": "co_quindio_armenia",
        "country_code": "CO",
        "country_name": "Colombia",
        "region_name": "Quindío",
        "city_name": "Armenia",
        "aliases": ["Armenia", "Calarcá", "Eje Cafetero", "La Tebaida", "Montenegro"],
        "concentric_rings": {
            "ring_0": ["Armenia"],
            "ring_1": ["Calarcá", "La Tebaida", "Montenegro", "Circasia"],
        },
        "expansion_rules": {
            "default_scope": "metro_area",
            "max_allowed_ring": 1,
            "min_quota_threshold_percent": 100,
        },
        "registry_sources": ["secop", "supersociedades", "rues", "dian"],
        "is_active": True,
    },
    {
        "location_id": "co_tolima_ibague",
        "country_code": "CO",
        "country_name": "Colombia",
        "region_name": "Tolima",
        "city_name": "Ibagué",
        "aliases": ["Ibagué", "Espinal"],
        "concentric_rings": {
            "ring_0": ["Ibagué"],
            "ring_1": ["Espinal", "Flandes", "Alvarado"],
        },
        "expansion_rules": {
            "default_scope": "metro_area",
            "max_allowed_ring": 1,
            "min_quota_threshold_percent": 100,
        },
        "registry_sources": ["secop", "supersociedades", "rues", "dian"],
        "is_active": True,
    },
    {
        "location_id": "co_norte_santander_cucuta",
        "country_code": "CO",
        "country_name": "Colombia",
        "region_name": "Norte de Santander",
        "city_name": "Cúcuta",
        "aliases": ["Cúcuta", "Los Patios", "Villa del Rosario"],
        "concentric_rings": {
            "ring_0": ["Cúcuta"],
            "ring_1": ["Los Patios", "Villa del Rosario", "El Zulia"],
        },
        "expansion_rules": {
            "default_scope": "metro_area",
            "max_allowed_ring": 1,
            "min_quota_threshold_percent": 100,
        },
        "registry_sources": ["secop", "supersociedades", "rues", "dian"],
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
        "concentric_rings": {
            "ring_0": ["Santo Domingo", "Distrito Nacional"],
            "ring_1": ["Santo Domingo Este", "Santo Domingo Oeste", "Santo Domingo Norte"],
            "ring_2": ["Boca Chica", "San Cristóbal", "Bajos de Haina", "Pedro Brand", "Los Alcarrizos"],
        },
        "expansion_rules": {
            "default_scope": "metro_area",
            "max_allowed_ring": 1,
            "min_quota_threshold_percent": 100,
        },
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
        "concentric_rings": {
            "ring_0": ["Santiago de los Caballeros", "Santiago"],
            "ring_1": ["Tamboril", "Villa González", "Licey al Medio", "Puñal"],
            "ring_2": ["Moca", "Navarrete"],
        },
        "expansion_rules": {
            "default_scope": "metro_area",
            "max_allowed_ring": 1,
            "min_quota_threshold_percent": 100,
        },
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
        "concentric_rings": {
            "ring_0": ["Punta Cana", "Higüey"],
            "ring_1": ["Bávaro", "Verón", "Cap Cana"],
        },
        "expansion_rules": {
            "default_scope": "metro_area",
            "max_allowed_ring": 1,
            "min_quota_threshold_percent": 100,
        },
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
        "concentric_rings": {
            "ring_0": ["La Romana"],
            "ring_1": ["Bayahíbe", "Guaymate"],
        },
        "expansion_rules": {
            "default_scope": "metro_area",
            "max_allowed_ring": 1,
            "min_quota_threshold_percent": 100,
        },
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
        "concentric_rings": {
            "ring_0": ["San Cristóbal"],
            "ring_1": ["Bajos de Haina", "Haina", "Yaguate"],
        },
        "expansion_rules": {
            "default_scope": "metro_area",
            "max_allowed_ring": 1,
            "min_quota_threshold_percent": 100,
        },
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
        "concentric_rings": {
            "ring_0": ["Quito", "Distrito Metropolitano de Quito"],
            "ring_1": ["Cumbayá", "Tumbaco", "Los Chillos", "Valle de Cumbayá", "Calderón"],
            "ring_2": ["Rumiñahui", "Sangolquí", "Machachi", "Tabacundo"],
        },
        "expansion_rules": {
            "default_scope": "metro_area",
            "max_allowed_ring": 1,
            "min_quota_threshold_percent": 100,
        },
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
        "concentric_rings": {
            "ring_0": ["Guayaquil"],
            "ring_1": ["Samborondón", "Durán", "Daule", "La Puntilla"],
            "ring_2": ["Milagro", "Nobol", "Salitre"],
        },
        "expansion_rules": {
            "default_scope": "metro_area",
            "max_allowed_ring": 1,
            "min_quota_threshold_percent": 100,
        },
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
        "concentric_rings": {
            "ring_0": ["Cuenca"],
            "ring_1": ["Gualaceo", "Paute", "Challuabamba"],
        },
        "expansion_rules": {
            "default_scope": "metro_area",
            "max_allowed_ring": 1,
            "min_quota_threshold_percent": 100,
        },
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
        "concentric_rings": {
            "ring_0": ["Manta"],
            "ring_1": ["Montecristi", "Jaramijó", "Portoviejo"],
        },
        "expansion_rules": {
            "default_scope": "metro_area",
            "max_allowed_ring": 1,
            "min_quota_threshold_percent": 100,
        },
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
        "concentric_rings": {
            "ring_0": ["Machala"],
            "ring_1": ["Puerto Bolívar", "Pasaje", "Santa Rosa", "El Guabo"],
        },
        "expansion_rules": {
            "default_scope": "metro_area",
            "max_allowed_ring": 1,
            "min_quota_threshold_percent": 100,
        },
        "registry_sources": ["sercop", "supercias", "sri"],
        "is_active": True,
    },

    # --- 🇨🇱 CHILE ---
    {
        "location_id": "cl_santiago_centro",
        "country_code": "CL",
        "country_name": "Chile",
        "region_name": "Región Metropolitana de Santiago",
        "city_name": "Santiago",
        "aliases": ["Santiago", "Gran Santiago", "Providencia", "Las Condes", "Vitacura", "Ñuñoa"],
        "concentric_rings": {
            "ring_0": ["Santiago", "Santiago Centro"],
            "ring_1": ["Providencia", "Las Condes", "Vitacura", "Ñuñoa", "San Miguel", "Recoleta"],
            "ring_2": ["Maipú", "La Florida", "Puente Alto", "San Bernardo", "Quilicura"],
        },
        "expansion_rules": {
            "default_scope": "metro_area",
            "max_allowed_ring": 1,
            "min_quota_threshold_percent": 100,
        },
        "registry_sources": ["chilecompra", "res", "sii"],
        "is_active": True,
    },
    {
        "location_id": "cl_valparaiso",
        "country_code": "CL",
        "country_name": "Chile",
        "region_name": "Valparaíso",
        "city_name": "Valparaíso",
        "aliases": ["Valparaíso", "Viña del Mar", "Concón", "Quilpué", "Villa Alemana"],
        "concentric_rings": {
            "ring_0": ["Valparaíso", "Viña del Mar"],
            "ring_1": ["Concón", "Quilpué", "Villa Alemana"],
            "ring_2": ["Quillota", "San Antonio"],
        },
        "expansion_rules": {
            "default_scope": "metro_area",
            "max_allowed_ring": 1,
            "min_quota_threshold_percent": 100,
        },
        "registry_sources": ["chilecompra", "res", "sii"],
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
    {
        "role_id": "school_rector_director",
        "canonical_title": "Rector / Rectora de Institución Educativa",
        "seniority_level": "c_level",
        "functional_domain": "executive",
        "country_code": "ALL",
        "aliases": [
            "Rector", "Rectora", "Director de Colegio", "Directora de Colegio",
            "Principal", "Head of School", "Director Académico", "Directora Académica",
            "Representante Legal", "Gerente Educativo"
        ],
        "applicable_sectors": ["education_schools", "all"],
        "usage_count": 290,
        "is_active": True,
    },
    {
        "role_id": "school_admin_procurement",
        "canonical_title": "Coordinador Administrativo & Compras Escolares",
        "seniority_level": "director",
        "functional_domain": "procurement",
        "country_code": "ALL",
        "aliases": [
            "Coordinador Administrativo", "Coordinadora Administrativa", "Director Administrativo",
            "Jefe de Compras", "Director de Admisiones y Registro", "Coordinador de Recursos",
            "Secretario General", "Secretaria General", "Administrador Escolar"
        ],
        "applicable_sectors": ["education_schools", "all"],
        "usage_count": 240,
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
        "allowed_isic_divisions": ["01", "10", "11", "46", "47", "56"],
        "forbidden_isic_divisions": ["62", "63", "58", "41", "42", "43", "71", "69", "85", "86", "24", "38"],
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
        "allowed_isic_divisions": ["41", "42", "43", "46", "71"],
        "forbidden_isic_divisions": ["62", "63", "58", "85", "86", "56", "79", "10", "11", "24"],
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
        "allowed_isic_divisions": ["49", "50", "51", "52", "53"],
        "forbidden_isic_divisions": ["85", "86", "62", "63", "56", "24", "38"],
        "usage_count": 210,
        "is_active": True,
    },
    {
        "sector_id": "tech_software_telecom",
        "sector_name": "Software, Telecomunicaciones & Cloud B2B",
        "country_code": "ALL",
        "ciiu_codes": ["J5820", "J6110", "J6120", "J6190", "J6201", "J6202", "J6209", "J6311", "G4651"],
        "keywords_include": [
            "software", "saas", "cloud", "ciberseguridad", "erp", "crm", "facturacion electronica",
            "apis", "infraestructura ti", "desarrollo de software", "desarrollo web", "desarrollo de sistemas",
            "telecomunicaciones", "servidores", "inteligencia artificial"
        ],
        "keywords_exclude_defaults": ["cafe internet", "reparacion de celulares", "venta de fundas"],
        "allowed_isic_divisions": ["62", "63", "58", "61", "46"],
        "forbidden_isic_divisions": ["24", "38", "41", "42", "43", "71", "79", "85", "86", "10", "11", "13", "14", "68", "69"],
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
        "allowed_isic_divisions": ["13", "14", "15", "17", "20", "22", "24", "25", "28", "46", "47"],
        "forbidden_isic_divisions": ["62", "63", "85", "86", "56", "79"],
        "usage_count": 130,
        "is_active": True,
    },
    {
        "sector_id": "fashion_apparel_textiles",
        "sector_name": "Moda, Confecciones, Textiles & Calzado",
        "country_code": "ALL",
        "ciiu_codes": ["C1311", "C1312", "C1313", "C1391", "C1392", "C1399", "C1410", "C1420", "C1430", "C1511", "C1512", "C1521", "C1522", "C1523", "G4641", "G4771", "G4772"],
        "keywords_include": [
            "textiles", "confecciones", "prendas de vestir", "moda", "hilanderia", "telas",
            "ropa", "calzado", "marroquineria", "cuero", "maquila textil", "costura industrial", "patronaje"
        ],
        "keywords_exclude_defaults": ["taller de remiendos", "costura casera"],
        "allowed_isic_divisions": ["13", "14", "15", "46", "47"],
        "forbidden_isic_divisions": ["62", "63", "85", "86", "41", "42", "43", "71", "24", "38"],
        "usage_count": 220,
        "is_active": True,
    },
    {
        "sector_id": "healthcare_pharma",
        "sector_name": "Salud, Dispositivos Médicos & Farmacéutica",
        "country_code": "ALL",
        "ciiu_codes": ["C2100", "C3250", "G4646", "Q8610", "Q8621", "Q8699"],
        "keywords_include": [
            "farmaceutica", "dispositivos medicos", "insumos medicos", "laboratorio clinico", "clinica",
            "hospital", "ips", "equipos biomedicos", "medicamentos", "odontologia especializada"
        ],
        "keywords_exclude_defaults": ["drogueria de barrio", "tienda naturista"],
        "allowed_isic_divisions": ["21", "32", "46", "86"],
        "forbidden_isic_divisions": ["62", "41", "42", "43", "24", "38"],
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
        "allowed_isic_divisions": ["68", "70"],
        "forbidden_isic_divisions": ["24", "10", "85", "86", "62", "38"],
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
        "allowed_isic_divisions": ["80", "81", "38"],
        "forbidden_isic_divisions": ["62", "63", "85", "86", "56", "10"],
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
        "allowed_isic_divisions": ["35", "46"],
        "forbidden_isic_divisions": ["62", "85", "86", "56"],
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
        "allowed_isic_divisions": ["64", "69", "82"],
        "forbidden_isic_divisions": ["10", "24", "38", "41", "42"],
        "usage_count": 110,
        "is_active": True,
    },
    {
        "sector_id": "education_schools",
        "sector_name": "Educación, Colegios & Instituciones Académicas",
        "country_code": "ALL",
        "ciiu_codes": ["P8511", "P8512", "P8513", "P8521", "P8522", "P8530", "P8541", "P8543", "P8560"],
        "keywords_include": [
            "colegio", "colegios", "escuela", "escuelas", "institucion educativa", "educacion",
            "liceo", "gimnasio", "academico", "bachillerato", "preescolar", "universidad", "carnets",
            "identificaciones escolares"
        ],
        "keywords_exclude_defaults": ["jardin infantil domiciliario", "clases particulares"],
        "allowed_isic_divisions": ["85", "18"],
        "forbidden_isic_divisions": ["24", "10", "11", "41", "42", "43", "69", "62", "63", "38"],
        "usage_count": 220,
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
        print("[SEED] Taxonomy seeding complete:")
        print(f"• Locations: {counts['locations']}")
        print(f"• Roles:     {counts['roles']}")
        print(f"• Sectors:   {counts['sectors']}")

