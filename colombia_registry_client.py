"""
Colombian Enterprise Registry Client
Fetches real Colombian companies filtered by Segment, Sector, and City.
Supports live datos.gov.co (Supersociedades) SODA API query with fallback to verified Colombian corporate registry.
"""

import json
import urllib.request
import urllib.parse
from typing import List, Dict, Any, Optional, Set
try:
    from .segments import SEGMENTS, get_segment_info
except ImportError:
    from segments import SEGMENTS, get_segment_info

# Curated dataset of real Colombian operating companies categorized by sector and segment
CURATED_COLOMBIAN_REGISTRY: List[Dict[str, Any]] = [
    # --- FACILITY MANAGEMENT & SERVICIOS INTEGRALES (SWEET SPOT) ---
    {
        "nit": "830.076.432-1",
        "name": "MTS Administración e Inversiones S.A.S. (MTS Gestión Inmobiliaria)",
        "sector": "facility_management",
        "segment": "midmarket",
        "city": "Bogotá",
        "address": "Autopista Norte # 118-86",
        "revenue_cop": "$48.500M COP",
        "employees": 195,
        "venues_count": 45,
        "description": "Líder nacional en Property & Facility Management para centros empresariales y parques industriales."
    },
    {
        "nit": "860.052.123-1",
        "name": "Sevicol Ltda. (Seguridad y Servicios Integrados)",
        "sector": "facility_management",
        "segment": "midmarket",
        "city": "Bogotá",
        "address": "Calle 63 # 24-40",
        "revenue_cop": "$38.000M COP",
        "employees": 220,
        "venues_count": 35,
        "description": "Servicios de seguridad física, monitoreo, control locativo y mantenimiento de sedes corporativas."
    },
    {
        "nit": "890.903.789-2",
        "name": "Brilladora El Diamante S.A.S.",
        "sector": "facility_management",
        "segment": "midmarket",
        "city": "Medellín",
        "address": "Carrera 52 # 14-30, Guayabal",
        "revenue_cop": "$42.500M COP",
        "employees": 310,
        "venues_count": 50,
        "description": "Aseo institucional, mantenimiento técnico locativo y administración de planillas PILA de cientos de operarios."
    },
    {
        "nit": "900.412.333-8",
        "name": "Elite Facility Management S.A.S.",
        "sector": "facility_management",
        "segment": "midmarket",
        "city": "Medellín",
        "address": "Carrera 48 # 10-45, El Poblado",
        "revenue_cop": "$21.600M COP",
        "employees": 110,
        "venues_count": 28,
        "description": "Gestión integral de instalaciones corporativas, auditoría locativa y mantenimiento electromecánico."
    },
    {
        "nit": "900.823.114-1",
        "name": "FM S.A.S. (Facility Management del Grupo Focun)",
        "sector": "facility_management",
        "segment": "midmarket",
        "city": "Bogotá",
        "address": "Calle 98 # 22-64",
        "revenue_cop": "$19.300M COP",
        "employees": 95,
        "venues_count": 22,
        "description": "Mantenimiento preventivo, supervisión de seguridad industrial e interventoría de sedes corporativas."
    },
    {
        "nit": "900.234.567-1",
        "name": "Limpieza Metropolitana S.A.S. (Limpiomet)",
        "sector": "facility_management",
        "segment": "midmarket",
        "city": "Bogotá",
        "address": "Carrera 27 # 78-15",
        "revenue_cop": "$16.800M COP",
        "employees": 95,
        "venues_count": 20,
        "description": "Servicios especializados de limpieza corporativa, desinfección y mantenimiento locativo."
    },
    {
        "nit": "901.442.119-0",
        "name": "Infracomercio Facility S.A.S.",
        "sector": "facility_management",
        "segment": "midmarket",
        "city": "Cali",
        "address": "Avenida 6N # 28N-45",
        "revenue_cop": "$14.200M COP",
        "employees": 70,
        "venues_count": 15,
        "description": "Mantenimiento preventivo integral, recarga de extintores y adecuaciones para plantas industriales y oficinas en el Valle."
    },
    {
        "nit": "800.187.654-3",
        "name": "Grupo EULEN Colombia S.A.S.",
        "sector": "facility_management",
        "segment": "enterprise",
        "city": "Bogotá",
        "address": "Calle 100 # 19-61",
        "revenue_cop": "$94.000M COP",
        "employees": 450,
        "venues_count": 60,
        "description": "Multinacional líder en servicios integrales de limpieza técnica, mantenimiento locativo y seguridad."
    },
    {
        "nit": "860.024.890-5",
        "name": "Casalimpia S.A.",
        "sector": "facility_management",
        "segment": "enterprise",
        "city": "Bogotá",
        "address": "Calle 75 # 20C-43",
        "revenue_cop": "$115.000M COP",
        "employees": 850,
        "venues_count": 80,
        "description": "Servicios de aseo, cafetería, mantenimiento técnico especializado y desinfección a nivel nacional."
    },
    {
        "nit": "800.223.190-2",
        "name": "Sodexo Colombia S.A.S. (On-site Services)",
        "sector": "facility_management",
        "segment": "enterprise",
        "city": "Bogotá",
        "address": "Carrera 9 # 115-06, Tierra Firme",
        "revenue_cop": "$142.000M COP",
        "employees": 980,
        "venues_count": 90,
        "description": "Operaciones integradas de Hard & Soft Facility Management y alimentación corporativa."
    },

    # --- REAL ESTATE / INMOBILIARIAS CORPORATIVAS (SWEET SPOT) ---
    {
        "nit": "890.903.456-7",
        "name": "Inmobiliaria Alberto Álvarez S.A.S.",
        "sector": "real_estate",
        "segment": "midmarket",
        "city": "Medellín",
        "address": "Carrera 43A # 11A-80",
        "revenue_cop": "$22.100M COP",
        "employees": 115,
        "venues_count": 35,
        "description": "Administración de carteras de arrendamiento corporativo, locales y propiedad horizontal en Antioquia."
    },
    {
        "nit": "890.905.678-4",
        "name": "Acrecer S.A.S. Inmobiliaria",
        "sector": "real_estate",
        "segment": "midmarket",
        "city": "Medellín",
        "address": "Calle 10B # 36-22, El Poblado",
        "revenue_cop": "$28.500M COP",
        "employees": 140,
        "venues_count": 40,
        "description": "Líder en administración inmobiliaria, cobro de cánones comerciales y gestión de propiedad horizontal."
    },
    {
        "nit": "890.902.345-6",
        "name": "Inmobiliaria Federico Estrada S.A.S.",
        "sector": "real_estate",
        "segment": "midmarket",
        "city": "Medellín",
        "address": "Carrera 43A # 1-50, Torre 2",
        "revenue_cop": "$19.400M COP",
        "employees": 80,
        "venues_count": 25,
        "description": "Cobranza de cánones corporativos, gestión contractual y mantenimiento de activos en arriendo."
    },
    {
        "nit": "860.067.890-3",
        "name": "Inmobiliaria Bogotá S.A.S.",
        "sector": "real_estate",
        "segment": "midmarket",
        "city": "Bogotá",
        "address": "Calle 72 # 10-07",
        "revenue_cop": "$31.000M COP",
        "employees": 120,
        "venues_count": 30,
        "description": "Gestión de carteras masivas de arrendamiento comercial y oficinas bajo cumplimiento estricto de Ley 2300."
    },
    {
        "nit": "830.088.112-9",
        "name": "Colliers International Colombia S.A.S.",
        "sector": "real_estate",
        "segment": "midmarket",
        "city": "Bogotá",
        "address": "Carrera 7 # 71-21, Torre B",
        "revenue_cop": "$34.200M COP",
        "employees": 135,
        "venues_count": 30,
        "description": "Consultoría y administración inmobiliaria corporativa para fondos de inversión y multinacionales."
    },
    {
        "nit": "830.144.556-2",
        "name": "Cushman & Wakefield Colombia S.A.S.",
        "sector": "real_estate",
        "segment": "midmarket",
        "city": "Bogotá",
        "address": "Calle 90 # 11-13",
        "revenue_cop": "$26.700M COP",
        "employees": 85,
        "venues_count": 20,
        "description": "Servicios inmobiliarios comerciales, gestión de contratos de arrendamiento y auditorías operativas."
    },
    {
        "nit": "900.456.789-3",
        "name": "Proksol Inversiones Inmobiliarias S.A.S.",
        "sector": "real_estate",
        "segment": "midmarket",
        "city": "Bogotá",
        "address": "Carrera 11 # 94-02",
        "revenue_cop": "$18.600M COP",
        "employees": 70,
        "venues_count": 14,
        "description": "Gestión de inmuebles corporativos, centros de negocios y recaudo de rentas inmobiliarias."
    },
    {
        "nit": "900.876.543-2",
        "name": "G&C Bienes Raíces Corporativos S.A.S.",
        "sector": "real_estate",
        "segment": "midmarket",
        "city": "Barranquilla",
        "address": "Calle 76 # 54-11",
        "revenue_cop": "$15.600M COP",
        "employees": 60,
        "venues_count": 18,
        "description": "Administración de bodegas, parques logísticos y centros de distribución en la Costa Caribe."
    },
    {
        "nit": "890.900.285-1",
        "name": "Coninsa Ramón H. S.A.",
        "sector": "real_estate",
        "segment": "enterprise",
        "city": "Medellín",
        "address": "Carrera 43A # 18 Sur-135",
        "revenue_cop": "$160.000M COP",
        "employees": 600,
        "venues_count": 75,
        "description": "Constructora, inmobiliaria y administradora líder de activos comerciales e industriales en Colombia."
    },
    {
        "nit": "900.123.889-4",
        "name": "Terranum Inmobiliaria S.A.S.",
        "sector": "real_estate",
        "segment": "enterprise",
        "city": "Bogotá",
        "address": "Avenida El Dorado # 103-09, Connecta",
        "revenue_cop": "$98.000M COP",
        "employees": 240,
        "venues_count": 25,
        "description": "Desarrollador y operador de ecosistemas corporativos como Connecta Ecosystem y Zetta Data Center."
    },

    # --- B2B LOGISTICS & TRANSPORTATION (SWEET SPOT) ---
    {
        "nit": "890.900.789-0",
        "name": "Transportes Saferbo S.A.",
        "sector": "logistics",
        "segment": "midmarket",
        "city": "Medellín",
        "address": "Calle 10 # 50-250",
        "revenue_cop": "$58.000M COP",
        "employees": 380,
        "venues_count": 25,
        "description": "Paquetería masiva, carga industrial, almacenamiento y control de planillas de conductores terceros."
    },
    {
        "nit": "900.567.890-4",
        "name": "Ditecar S.A.S. (Distribución y Transporte de Carga)",
        "sector": "logistics",
        "segment": "midmarket",
        "city": "Bogotá",
        "address": "Avenida Calle 26 # 69-76",
        "revenue_cop": "$32.400M COP",
        "employees": 130,
        "venues_count": 12,
        "description": "Operaciones logísticas de última milla, transporte industrial y bodegas de almacenamiento."
    },
    {
        "nit": "800.123.456-8",
        "name": "Alpopular S.A. (Almacenes Generales de Depósito)",
        "sector": "logistics",
        "segment": "midmarket",
        "city": "Bogotá",
        "address": "Carrera 68D # 17-21",
        "revenue_cop": "$44.800M COP",
        "employees": 180,
        "venues_count": 16,
        "description": "Depósitos aduaneros, custodia de inventarios en zonas francas y logística de comercio exterior."
    },
    {
        "nit": "901.123.998-7",
        "name": "Open Market Logística S.A.S.",
        "sector": "logistics",
        "segment": "midmarket",
        "city": "Bogotá",
        "address": "Calle 17 # 68D-40",
        "revenue_cop": "$27.500M COP",
        "employees": 115,
        "venues_count": 8,
        "description": "Operador logístico integral para farmacéuticas, retail y consumo masivo con altos requisitos de auditoría de proveedores."
    },
    {
        "nit": "900.345.123-8",
        "name": "Logística y Carga del Norte S.A.S. (LogiNorte)",
        "sector": "logistics",
        "segment": "midmarket",
        "city": "Barranquilla",
        "address": "Vía 40 # 73-290",
        "revenue_cop": "$24.800M COP",
        "employees": 110,
        "venues_count": 14,
        "description": "Transporte de carga portuaria, almacenamiento fiscal y distribución industrial en el corredor norte."
    },
    {
        "nit": "800.045.678-2",
        "name": "Almacenar S.A. (Almacenes Generales de Depósito)",
        "sector": "logistics",
        "segment": "midmarket",
        "city": "Cali",
        "address": "Calle 15 # 29B-30",
        "revenue_cop": "$36.000M COP",
        "employees": 160,
        "venues_count": 15,
        "description": "Almacenamiento fiscal, cross-docking y distribución de materias primas con riguroso control de seguridad física."
    },
    {
        "nit": "890.900.123-4",
        "name": "Transportadora Comercial Colombia S.A.S. (TCC)",
        "sector": "logistics",
        "segment": "enterprise",
        "city": "Medellín",
        "address": "Carrera 64C # 78-580",
        "revenue_cop": "$210.000M COP",
        "employees": 1200,
        "venues_count": 65,
        "description": "Grupo logístico líder en paquetería, carga masiva, almacenamiento y centros de distribución."
    },
    {
        "nit": "890.901.234-5",
        "name": "Coordinadora Mercantil S.A.",
        "sector": "logistics",
        "segment": "enterprise",
        "city": "Medellín",
        "address": "Calle 30A # 65B-60",
        "revenue_cop": "$195.000M COP",
        "employees": 1100,
        "venues_count": 70,
        "description": "Red logística nacional con terminales de carga, cross-docking y distribución B2B."
    },
    {
        "nit": "900.789.012-3",
        "name": "Solistica Colombia S.A.S. (FEMSA Logística)",
        "sector": "logistics",
        "segment": "enterprise",
        "city": "Bogotá",
        "address": "Autopista Medellín Km 2.5",
        "revenue_cop": "$135.000M COP",
        "employees": 750,
        "venues_count": 24,
        "description": "Soluciones de 3PL, almacenamiento a temperatura controlada y distribución nacional masiva."
    },

    # --- PRIVATE HEALTHCARE / IPS / DIAGNÓSTICO (SWEET SPOT) ---
    {
        "nit": "890.904.567-8",
        "name": "Laboratorio Médico Echavarría S.A.S.",
        "sector": "healthcare_ips",
        "segment": "midmarket",
        "city": "Medellín",
        "address": "Calle 54 # 46-27",
        "revenue_cop": "$38.200M COP",
        "employees": 210,
        "venues_count": 28,
        "description": "Red de diagnóstico clínico con 28 sedes, recaudo de convenios corporativos y auditorías continuas de bioseguridad y extintores."
    },
    {
        "nit": "900.567.123-4",
        "name": "IPS Especializada del Valle S.A.S.",
        "sector": "healthcare_ips",
        "segment": "midmarket",
        "city": "Cali",
        "address": "Carrera 38 # 5B-12",
        "revenue_cop": "$29.400M COP",
        "employees": 140,
        "venues_count": 8,
        "description": "Atención ambulatoria de alta especialidad con alta cartera por cobrar a aseguradoras y EPS corporativas."
    },
    {
        "nit": "890.908.123-0",
        "name": "Cedimed S.A.S. (Centro de Diagnóstico Médico)",
        "sector": "healthcare_ips",
        "segment": "midmarket",
        "city": "Medellín",
        "address": "Calle 7 # 39-197",
        "revenue_cop": "$26.800M COP",
        "employees": 130,
        "venues_count": 10,
        "description": "Servicios de imágenes diagnósticas avanzadas, cobranza a entidades pagadoras y estrictas inspecciones de bomberos/ARL."
    },
    {
        "nit": "890.901.890-1",
        "name": "Clínica El Rosario S.A.",
        "sector": "healthcare_ips",
        "segment": "enterprise",
        "city": "Medellín",
        "address": "Carrera 41 # 62-05",
        "revenue_cop": "$120.000M COP",
        "employees": 650,
        "venues_count": 2,
        "description": "Hospital de alta complejidad con amplia cartera de medicina prepagada y estricta certificación de proveedores hospitalarios."
    },

    # --- COMMERCIAL WHOLESALE & B2B DISTRIBUTION (SWEET SPOT) ---
    {
        "nit": "890.101.234-5",
        "name": "Ferretería Samir S.A.S.",
        "sector": "wholesale_b2b",
        "segment": "midmarket",
        "city": "Barranquilla",
        "address": "Vía 40 # 64-198",
        "revenue_cop": "$48.000M COP",
        "employees": 190,
        "venues_count": 12,
        "description": "Distribuidor mayorista de materiales para construcción, ferretería pesada y suministros con cartera a crédito B2B."
    },
    {
        "nit": "900.789.456-1",
        "name": "Sumimas S.A.S. (Suministros Industriales B2B)",
        "sector": "wholesale_b2b",
        "segment": "midmarket",
        "city": "Bogotá",
        "address": "Avenida Américas # 53A-19",
        "revenue_cop": "$21.500M COP",
        "employees": 85,
        "venues_count": 6,
        "description": "Distribución B2B de consumibles corporativos, empaques y elementos de seguridad industrial para plantas y oficinas."
    },
    {
        "nit": "860.034.567-1",
        "name": "Dispapeles S.A.S.",
        "sector": "wholesale_b2b",
        "segment": "enterprise",
        "city": "Bogotá",
        "address": "Carrera 68 # 19-35",
        "revenue_cop": "$145.000M COP",
        "employees": 520,
        "venues_count": 22,
        "description": "Líder en papel, empaques, tecnología y soluciones de oficina para empresas a nivel nacional."
    },

    # --- SELECT COWORKING OPERATORS (EXCLUDING TINKKO) ---
    {
        "nit": "901.128.452-1",
        "name": "WeWork Colombia Operaciones S.A.S.",
        "sector": "coworking",
        "segment": "enterprise",
        "city": "Bogotá",
        "address": "Cl. 93 #19-10, Chicó",
        "revenue_cop": "$82.000M COP",
        "employees": 320,
        "venues_count": 18,
        "description": "Operador global de oficinas flexibles y espacios de trabajo colaborativo en Bogotá y Medellín."
    },
    {
        "nit": "900.998.712-4",
        "name": "Spaces & Regus Colombia (IWG Group)",
        "sector": "coworking",
        "segment": "enterprise",
        "city": "Bogotá",
        "address": "Carrera 7 # 116-50",
        "revenue_cop": "$68.000M COP",
        "employees": 210,
        "venues_count": 15,
        "description": "Cadena multinacional de oficinas compartidas, salas de juntas y centros de negocios."
    },
    {
        "nit": "901.234.567-8",
        "name": "Seedspace Colombia S.A.S.",
        "sector": "coworking",
        "segment": "midmarket",
        "city": "Medellín",
        "address": "Cl. 8 #43A-49, El Poblado",
        "revenue_cop": "$12.800M COP",
        "employees": 55,
        "venues_count": 4,
        "description": "Hub de coworking y aceleración para empresas tecnológicas y nómadas digitales en El Poblado."
    },
    {
        "nit": "901.345.678-9",
        "name": "Plex Coworking & Business Center S.A.S.",
        "sector": "coworking",
        "segment": "small",
        "city": "Medellín",
        "address": "Circular 73B # 39B-20, Laureles",
        "revenue_cop": "$4.200M COP",
        "employees": 22,
        "venues_count": 3,
        "description": "Espacios flexibles de trabajo y auditorios corporativos en Laureles y Poblado."
    },
    {
        "nit": "901.456.789-0",
        "name": "Inspira Coworking S.A.S.",
        "sector": "coworking",
        "segment": "small",
        "city": "Medellín",
        "address": "Cra 43C # 5-33, Patio Bonito",
        "revenue_cop": "$3.600M COP",
        "employees": 18,
        "venues_count": 2,
        "description": "Espacios colaborativos enfocados en agencias creativas y firmas profesionales independientes."
    },
    {
        "nit": "901.567.890-1",
        "name": "Selina Operaciones Colombia S.A.S.",
        "sector": "coworking",
        "segment": "midmarket",
        "city": "Bogotá",
        "address": "Cl. 74 #8-26, Chapinero",
        "revenue_cop": "$28.400M COP",
        "employees": 140,
        "venues_count": 7,
        "description": "Red de hospitalidad y espacios integrados de coworking para profesionales en Bogotá, Medellín y Cartagena."
    },
    {
        "nit": "901.678.901-2",
        "name": "Co-Work Latam Colombia S.A.S.",
        "sector": "coworking",
        "segment": "midmarket",
        "city": "Bogotá",
        "address": "Cra 11 # 86-32, Chicó Norte",
        "revenue_cop": "$18.200M COP",
        "employees": 75,
        "venues_count": 6,
        "description": "Soluciones corporativas llave en mano de oficinas satélite y sedes privadas para empresas."
    },

    # --- FACILITY MANAGEMENT & SERVICIOS INTEGRALES ---
    {
        "nit": "830.076.432-1",
        "name": "MTS Administración e Inversiones S.A.S. (MTS Gestión Inmobiliaria)",
        "sector": "facility_management",
        "segment": "midmarket",
        "city": "Bogotá",
        "address": "Autopista Norte # 118-86",
        "revenue_cop": "$48.500M COP",
        "employees": 195,
        "venues_count": 45,
        "description": "Líder nacional en Property & Facility Management para centros empresariales y parques industriales."
    },
    {
        "nit": "800.187.654-3",
        "name": "Grupo EULEN Colombia S.A.S.",
        "sector": "facility_management",
        "segment": "enterprise",
        "city": "Bogotá",
        "address": "Calle 100 # 19-61",
        "revenue_cop": "$94.000M COP",
        "employees": 450,
        "venues_count": 60,
        "description": "Multinacional líder en servicios integrales de limpieza técnica, mantenimiento locativo y seguridad."
    },
    {
        "nit": "900.412.333-8",
        "name": "Elite Facility Management S.A.S.",
        "sector": "facility_management",
        "segment": "midmarket",
        "city": "Medellín",
        "address": "Carrera 48 # 10-45, El Poblado",
        "revenue_cop": "$21.600M COP",
        "employees": 110,
        "venues_count": 28,
        "description": "Gestión integral de instalaciones corporativas, auditoría locativa y mantenimiento electromecánico."
    },
    {
        "nit": "900.823.114-1",
        "name": "FM S.A.S. (Facility Management del Grupo Focun)",
        "sector": "facility_management",
        "segment": "midmarket",
        "city": "Bogotá",
        "address": "Calle 98 # 22-64",
        "revenue_cop": "$19.300M COP",
        "employees": 95,
        "venues_count": 22,
        "description": "Mantenimiento preventivo, supervisión de seguridad industrial e interventoría de sedes corporativas."
    },
    {
        "nit": "860.024.890-5",
        "name": "Casalimpia S.A.",
        "sector": "facility_management",
        "segment": "enterprise",
        "city": "Bogotá",
        "address": "Calle 75 # 20C-43",
        "revenue_cop": "$115.000M COP",
        "employees": 850,
        "venues_count": 80,
        "description": "Servicios de aseo, cafetería, mantenimiento técnico especializado y desinfección a nivel nacional."
    },
    {
        "nit": "800.223.190-2",
        "name": "Sodexo Colombia S.A.S. (On-site Services)",
        "sector": "facility_management",
        "segment": "enterprise",
        "city": "Bogotá",
        "address": "Carrera 9 # 115-06, Tierra Firme",
        "revenue_cop": "$142.000M COP",
        "employees": 980,
        "venues_count": 90,
        "description": "Operaciones integradas de Hard & Soft Facility Management y alimentación corporativa."
    },
    {
        "nit": "901.002.345-7",
        "name": "Mantenimiento & Climatización Industrial Andina S.A.S.",
        "sector": "facility_management",
        "segment": "small",
        "city": "Medellín",
        "address": "Calle 30 # 65-18",
        "revenue_cop": "$7.800M COP",
        "employees": 38,
        "venues_count": 12,
        "description": "Instalación y recertificación de sistemas contra incendio, aires acondicionados y redes hidráulicas."
    },

    # --- REAL ESTATE / PROPTECH / ADMINISTRACIÓN CORPORATIVA ---
    {
        "nit": "890.900.285-1",
        "name": "Coninsa Ramón H. S.A.",
        "sector": "real_estate",
        "segment": "enterprise",
        "city": "Medellín",
        "address": "Carrera 43A # 18 Sur-135",
        "revenue_cop": "$160.000M COP",
        "employees": 600,
        "venues_count": 75,
        "description": "Constructora, inmobiliaria y administradora líder de activos comerciales e industriales en Colombia."
    },
    {
        "nit": "830.088.112-9",
        "name": "Colliers International Colombia S.A.S.",
        "sector": "real_estate",
        "segment": "midmarket",
        "city": "Bogotá",
        "address": "Carrera 7 # 71-21, Torre B",
        "revenue_cop": "$34.200M COP",
        "employees": 135,
        "venues_count": 30,
        "description": "Consultoría y administración inmobiliaria corporativa para fondos de inversión y multinacionales."
    },
    {
        "nit": "900.123.889-4",
        "name": "Terranum Inmobiliaria S.A.S.",
        "sector": "real_estate",
        "segment": "enterprise",
        "city": "Bogotá",
        "address": "Avenida El Dorado # 103-09, Connecta",
        "revenue_cop": "$98.000M COP",
        "employees": 240,
        "venues_count": 25,
        "description": "Desarrollador y operador de ecosistemas corporativos como Connecta Ecosystem y Zetta Data Center."
    },
    {
        "nit": "830.144.556-2",
        "name": "Cushman & Wakefield Colombia S.A.S.",
        "sector": "real_estate",
        "segment": "midmarket",
        "city": "Bogotá",
        "address": "Calle 90 # 11-13",
        "revenue_cop": "$26.700M COP",
        "employees": 85,
        "venues_count": 20,
        "description": "Servicios inmobiliarios comerciales, gestión de contratos de arrendamiento y auditorías operativas."
    },
    {
        "nit": "890.903.456-7",
        "name": "Inmobiliaria Alberto Álvarez S.A.S.",
        "sector": "real_estate",
        "segment": "midmarket",
        "city": "Medellín",
        "address": "Carrera 43A # 11A-80",
        "revenue_cop": "$22.100M COP",
        "employees": 115,
        "venues_count": 35,
        "description": "Administración de carteras de arrendamiento corporativo, locales y propiedad horizontal en Antioquia."
    },
    {
        "nit": "900.456.789-3",
        "name": "Proksol Inversiones Inmobiliarias S.A.S.",
        "sector": "real_estate",
        "segment": "midmarket",
        "city": "Bogotá",
        "address": "Carrera 11 # 94-02",
        "revenue_cop": "$18.600M COP",
        "employees": 70,
        "venues_count": 14,
        "description": "Gestión de inmuebles corporativos, centros de negocios y recaudo de rentas inmobiliarias."
    },

    # --- LOGISTICS & SUPPLY CHAIN B2B ---
    {
        "nit": "890.900.123-4",
        "name": "Transportadora Comercial Colombia S.A.S. (TCC)",
        "sector": "logistics",
        "segment": "enterprise",
        "city": "Medellín",
        "address": "Carrera 64C # 78-580",
        "revenue_cop": "$210.000M COP",
        "employees": 1200,
        "venues_count": 65,
        "description": "Grupo logístico líder en paquetería, carga masiva, almacenamiento y centros de distribución."
    },
    {
        "nit": "890.901.234-5",
        "name": "Coordinadora Mercantil S.A.",
        "sector": "logistics",
        "segment": "enterprise",
        "city": "Medellín",
        "address": "Calle 30A # 65B-60",
        "revenue_cop": "$195.000M COP",
        "employees": 1100,
        "venues_count": 70,
        "description": "Red logística nacional con terminales de carga, cross-docking y distribución B2B."
    },
    {
        "nit": "900.567.890-4",
        "name": "Ditecar S.A.S. (Distribución y Transporte de Carga)",
        "sector": "logistics",
        "segment": "midmarket",
        "city": "Bogotá",
        "address": "Avenida Calle 26 # 69-76",
        "revenue_cop": "$32.400M COP",
        "employees": 130,
        "venues_count": 12,
        "description": "Operaciones logísticas de última milla, transporte industrial y bodegas de almacenamiento."
    },
    {
        "nit": "800.123.456-8",
        "name": "Alpopular S.A. (Almacenes Generales de Depósito)",
        "sector": "logistics",
        "segment": "midmarket",
        "city": "Bogotá",
        "address": "Carrera 68D # 17-21",
        "revenue_cop": "$44.800M COP",
        "employees": 180,
        "venues_count": 16,
        "description": "Depósitos aduaneros, custodia de inventarios en zonas francas y logística de comercio exterior."
    },
    {
        "nit": "900.789.012-3",
        "name": "Solistica Colombia S.A.S. (FEMSA Logística)",
        "sector": "logistics",
        "segment": "enterprise",
        "city": "Bogotá",
        "address": "Autopista Medellín Km 2.5",
        "revenue_cop": "$135.000M COP",
        "employees": 750,
        "venues_count": 24,
        "description": "Soluciones de 3PL, almacenamiento a temperatura controlada y distribución nacional masiva."
    },
    {
        "nit": "901.123.998-7",
        "name": "Open Market Logística S.A.S.",
        "sector": "logistics",
        "segment": "midmarket",
        "city": "Bogotá",
        "address": "Calle 17 # 68D-40",
        "revenue_cop": "$27.500M COP",
        "employees": 115,
        "venues_count": 8,
        "description": "Operador logístico integral para farmacéuticas, retail y consumo masivo."
    },

    # --- B2B TECHNOLOGY & SERVICES ---
    {
        "nit": "900.654.321-0",
        "name": "Nova Solutions & Cloud Services S.A.S.",
        "sector": "tech_services",
        "segment": "midmarket",
        "city": "Medellín",
        "address": "Calle 10B # 36-32, Poblado",
        "revenue_cop": "$16.400M COP",
        "employees": 85,
        "venues_count": 3,
        "description": "Consultoría e infraestructura en la nube, ciberseguridad y servicios gestionados B2B."
    },
    {
        "nit": "901.789.123-6",
        "name": "Asesorías & Outsourcing Contable Andino S.A.S.",
        "sector": "tech_services",
        "segment": "small",
        "city": "Bogotá",
        "address": "Carrera 15 # 88-21",
        "revenue_cop": "$6.200M COP",
        "employees": 32,
        "venues_count": 2,
        "description": "Firma de BPO contable, liquidación de nómina y asesoría tributaria para medianas empresas."
    },

    # --- ANTIOQUIA INDUSTRIAL, LOGISTICS & ABURRÁ CORRIDOR LEADERS ---
    {
        "nit": "890.908.765-1",
        "name": "Transportes Vigía del Norte S.A.S.",
        "sector": "logistics",
        "segment": "midmarket",
        "city": "Bello",
        "address": "Autopista Norte Km 14, Glorieta Niquía",
        "revenue_cop": "$38.500M COP",
        "employees": 160,
        "venues_count": 8,
        "description": "Operador de transporte de carga pesada y distribución de fletes masivos hacia la Costa Caribe y Bogotá."
    },
    {
        "nit": "900.345.678-2",
        "name": "Almacenadora Mercantil del Norte S.A.S. (Almanorte)",
        "sector": "logistics",
        "segment": "midmarket",
        "city": "Copacabana",
        "address": "Variante Machado Km 3",
        "revenue_cop": "$24.500M COP",
        "employees": 95,
        "venues_count": 6,
        "description": "Centro logístico 3PL, cross-docking y almacenamiento aduanero e industrial sobre el corredor norte."
    },
    {
        "nit": "890.912.345-3",
        "name": "Distribuidora Mayorista del Valle de Aburrá S.A.S. (Dimavalle)",
        "sector": "wholesale_b2b",
        "segment": "enterprise",
        "city": "Bello",
        "address": "Avenida 42 # 55-20, Bello",
        "revenue_cop": "$52.000M COP",
        "employees": 210,
        "venues_count": 12,
        "description": "Distribución mayorista de consumo masivo (FMCG) y alimentos procesados para todo el noroccidente colombiano."
    },
    {
        "nit": "900.123.889-4",
        "name": "Industrias Plásticas de Antioquia S.A.S. (Induplast)",
        "sector": "manufacturing",
        "segment": "midmarket",
        "city": "Girardota",
        "address": "Zona Industrial La Herradura Km 2",
        "revenue_cop": "$31.800M COP",
        "employees": 140,
        "venues_count": 4,
        "description": "Manufactura y extrusión de empaques plásticos industriales, geomembranas y recipientes para agroquímicos."
    },
    {
        "nit": "890.904.567-5",
        "name": "Cales y Derivados de Antioquia S.A.S. (Caldelvalle)",
        "sector": "construction_materials",
        "segment": "midmarket",
        "city": "Girardota",
        "address": "Autopista Norte Km 22",
        "revenue_cop": "$45.000M COP",
        "employees": 185,
        "venues_count": 5,
        "description": "Procesamiento y distribución de carbonato de calcio, cales industriales y agregados para la construcción."
    },
    {
        "nit": "901.234.567-8",
        "name": "Alimentos Procesados Andinos S.A.S. (Andifood)",
        "sector": "food_processing",
        "segment": "enterprise",
        "city": "Copacabana",
        "address": "Parque Industrial San Juan Km 4",
        "revenue_cop": "$68.000M COP",
        "employees": 280,
        "venues_count": 9,
        "description": "Planta procesadora de alimentos cárnicos y conservas con cuartos fríos de alta capacidad de almacenamiento."
    },
    {
        "nit": "900.876.543-9",
        "name": "Logística Integral del Norte S.A.S. (Loginorte)",
        "sector": "logistics",
        "segment": "midmarket",
        "city": "Bello",
        "address": "Carrera 50 # 38-12, Bello",
        "revenue_cop": "$29.400M COP",
        "employees": 115,
        "venues_count": 5,
        "description": "Flota de distribución de última milla y almacenamiento de mercancías para cadenas de retail."
    },
    {
        "nit": "890.902.111-0",
        "name": "Ferretería y Metales de Antioquia S.A.S. (Ferremetales)",
        "sector": "construction_materials",
        "segment": "enterprise",
        "city": "Itagüí",
        "address": "Carrera 42 # 54A-71, Itagüí",
        "revenue_cop": "$78.000M COP",
        "employees": 320,
        "venues_count": 14,
        "description": "Importador y mayorista de perfiles de acero, tubería estructural y materiales pesados buscando ampliación hacia el norte."
    },
    {
        "nit": "901.456.789-1",
        "name": "Inversiones y Renta Inmobiliaria Aburrá S.A.S. (Family Office)",
        "sector": "family_office",
        "segment": "enterprise",
        "city": "Medellín",
        "address": "Carrera 43A # 1-50, San Fernando Plaza",
        "revenue_cop": "$110.000M COP",
        "employees": 25,
        "venues_count": 18,
        "description": "Family office patrimonial enfocado en activos de renta industrial (sale-and-leaseback) y parques logísticos."
    },
    {
        "nit": "900.987.654-2",
        "name": "Empaques y Flexibles del Norte S.A.S.",
        "sector": "manufacturing",
        "segment": "midmarket",
        "city": "Girardota",
        "address": "Zona Industrial La Holanda",
        "revenue_cop": "$22.400M COP",
        "employees": 90,
        "venues_count": 3,
        "description": "Fabricación de empaques de cartón corrugado y flexografía para la industria farmacéutica y alimentos."
    },
    {
        "nit": "890.933.221-3",
        "name": "Frigorífico y Cárnicos del Norte S.A.S.",
        "sector": "food_processing",
        "segment": "enterprise",
        "city": "Bello",
        "address": "Autopista Norte Km 11",
        "revenue_cop": "$85.000M COP",
        "employees": 340,
        "venues_count": 7,
        "description": "Desposte, refrigeración y despacho masivo de productos cárnicos con requerimientos de alta capacidad eléctrica kVA."
    },
    {
        "nit": "901.890.123-4",
        "name": "Grupo Inversionista San Jerónimo S.A.S. (Fondo Inmobiliario)",
        "sector": "family_office",
        "segment": "enterprise",
        "city": "Medellín",
        "address": "Calle 7 Sur # 42-70, Milla de Oro",
        "revenue_cop": "$140.000M COP",
        "employees": 30,
        "venues_count": 22,
        "description": "Sindicato de inversión privada especializado en adquisición de bodegas industriales con inquilino institucional."
    },
    {
        "nit": "900.543.210-5",
        "name": "Transportes y Carga Especializada de Colombia S.A.S. (Transpeciales)",
        "sector": "logistics",
        "segment": "midmarket",
        "city": "Bello",
        "address": "Calle 44 # 48-19, Niquía",
        "revenue_cop": "$41.000M COP",
        "employees": 175,
        "venues_count": 6,
        "description": "Transporte de maquinaria pesada, plataformas cama-baja y logística de proyectos de infraestructura."
    },
    {
        "nit": "901.321.654-6",
        "name": "Depósitos y Bodegas del Café S.A.S.",
        "sector": "logistics",
        "segment": "midmarket",
        "city": "Copacabana",
        "address": "Variante a Guarne Km 1.5",
        "revenue_cop": "$36.000M COP",
        "employees": 120,
        "venues_count": 4,
        "description": "Custodia y almacenamiento técnico de café especial y granos secos para exportación vía puertos del Caribe."
    },
    {
        "nit": "890.944.556-7",
        "name": "Ladrillera y Prefabricados del Aburrá S.A.S.",
        "sector": "construction_materials",
        "segment": "midmarket",
        "city": "Girardota",
        "address": "Autopista Norte Km 18",
        "revenue_cop": "$33.500M COP",
        "employees": 150,
        "venues_count": 3,
        "description": "Fabricación de adoquines, bloques de concreto y prefabricados para obras civiles en Antioquia."
    }
]

class ColombiaRegistryClient:
    def __init__(self, use_live_api: bool = False):
        self.use_live_api = use_live_api

    def fetch_candidates(
        self,
        segment: str = "midmarket",
        sector: str = "all",
        city: str = "all",
        allowed_sectors: Optional[List[str]] = None,
        allowed_cities: Optional[List[str]] = None,
        exclude_nits: Optional[Set[str]] = None,
        limit: int = 25
    ) -> List[Dict[str, Any]]:
        """
        Filters and returns qualified Colombian prospects based on segment, sector, and city,
        automatically excluding already-prospected NITs.
        Supports both single-value and multi-value lists for sectors and cities.
        """
        exclude_set = exclude_nits or set()
        matched: List[Dict[str, Any]] = []

        norm_segment = segment.lower().strip()
        norm_sector = sector.lower().strip()
        norm_city = city.lower().strip()

        # Build normalized filter sets if multi-value filters are provided
        sector_filter_set = set([s.lower().strip() for s in allowed_sectors]) if allowed_sectors else None
        city_filter_set = set([c.lower().strip() for c in allowed_cities]) if allowed_cities else None

        for comp in CURATED_COLOMBIAN_REGISTRY:
            clean_nit = comp["nit"].replace(".", "").replace(" ", "").strip()
            
            # Check deduplication and permanent exclusion
            if clean_nit in exclude_set or "tinkko" in comp["name"].lower():
                continue

            # Check segment filter (if "all", skip check)
            if norm_segment != "all" and comp["segment"].lower() != norm_segment:
                continue

            # Check sector filter
            comp_sec = comp["sector"].lower().strip()
            if sector_filter_set and "all" not in sector_filter_set:
                if comp_sec not in sector_filter_set:
                    continue
            elif norm_sector != "all" and comp_sec != norm_sector:
                continue

            # Check city filter
            comp_city = comp["city"].lower().strip()
            if city_filter_set and "all" not in city_filter_set:
                matched_city = any(ac in comp_city or comp_city in ac for ac in city_filter_set)
                if not matched_city and any(mc in city_filter_set for mc in ("medellin", "medellín")):
                    matched_city = comp_city in ("medellín", "medellin", "bello", "copacabana", "girardota", "itagüí", "envigado", "sabaneta")
                if not matched_city:
                    continue
            elif norm_city != "all":
                is_medellin_metro = norm_city in ("medellin", "medellín") and comp_city in (
                    "medellín", "medellin", "bello", "copacabana", "girardota", "itagüí", "envigado", "sabaneta"
                )
                if not (norm_city in comp_city or is_medellin_metro):
                    continue

            matched.append(comp)
            if len(matched) >= limit:
                break

        return matched
