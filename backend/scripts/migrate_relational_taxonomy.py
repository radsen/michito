"""
Idempotent Database Migration & Seeding for Relational Dynamic Taxonomy.
Migrates:
1. taxonomy_isic_codes (Universal 4-digit master activities)
2. taxonomy_isic_country_registries (1-to-N Registry Translation for CO, DO, EC)
3. taxonomy_isic_role_links (N-to-N Executive Role mapping)
4. taxonomy_sector_isic_links (N-to-N Sector to ISIC link)
5. taxonomy_semantic_patterns (Dynamic & Agent-Learned regex patterns)
6. taxonomy_exclusion_rules (Bankrupt/placeholder blacklists & sector contradictions)

Supports PostgreSQL (Production/Dev) and SQLite (Offline fallback).
"""

import argparse
import logging
import os
import re
import sys
from datetime import datetime, timezone
from typing import Dict, Any, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from src.adapters.db.models import (
    Base,
    TaxonomyIsicCodeModel,
    TaxonomyIsicCountryRegistryModel,
    TaxonomyIsicRoleLinkModel,
    TaxonomySectorIsicLinkModel,
    TaxonomySemanticPatternModel,
    TaxonomyExclusionRuleModel,
    TaxonomyRoleModel,
    TaxonomySectorModel,
)
from src.domain.taxonomy.isic_catalog import UNIVERSAL_ISIC_CATALOG
from src.adapters.db.seed_taxonomy import SECTOR_SEEDS, seed_all_taxonomy

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


# Seed regex patterns from CiiuCode
SEED_SEMANTIC_PATTERNS = [
    ("pat_edu_01", r"colegio|escuela|educa|ensenanza|liceo|gimnasio|academ|universidad|institucion educativa|bachillerato|preescolar|carnet", "8530", 10),
    ("pat_food_01", r"alimento|abarrote|viveres|granos|lacteo|carnic|horeca|frutas|conservas|gastronom|comida", "4631", 20),
    ("pat_fuel_01", r"combustible|gasolina|diesel|acpm|lubricante|hidrocarburo|petroleo|petroquimic", "4661", 30),
    ("pat_const_01", r"cemento|concreto|acero|ferreteria industrial|materiales de construccion|ladrillo|prefabricados", "4663", 40),
    ("pat_const_02", r"constructor|construccion|edificac|obras civiles", "4111", 50),
    ("pat_ware_01", r"bodega industrial|cedi|almacenamiento y deposito", "5210", 60),
    ("pat_debt_01", r"cobranza|gestion de cartera|factoring|recuperacion de cartera", "8291", 70),
    ("pat_fac_01", r"facility|limpieza|aseo|mantenimiento locativo|seguridad fisica|seguridad privada|vigilancia|conserj", "8110", 80),
    ("pat_cowork_01", r"cowork|oficinas flexibles|espacios compartidos|espacios de trabajo", "6820", 90),
    ("pat_real_01", r"inmobiliari|bienes raices|propiedad horizontal|arrendamiento", "6810", 100),
    ("pat_log_01", r"logist|transport|carga|aduan|fletes|almacen", "4923", 110),
    ("pat_med_01", r"medical|salud|ips|clinic|farmaceut|biomed|odontol|dispositiv", "3250", 120),
    ("pat_tech_01", r"software|analyt|data|tech|digital|sistemas|program|cloud|\bia\b|\bai\b|ciber", "6201", 130),
    ("pat_tech_02", r"comput|hardware|redes|servidores|telecom", "4651", 140),
    ("pat_legal_01", r"abogad|legal|jurid|derecho|leyes|litig", "6910", 150),
    ("pat_fin_01", r"contab|auditor|financ|tributar|revisoria|impuesto", "6920", 160),
    ("pat_fin_02", r"fintech|invers|fondos|credito|valores", "6499", 170),
    ("pat_eng_01", r"arquitect|ingenier|civil|obras|interventor|diseno tecnico", "7110", 180),
    ("pat_mkt_01", r"publicid|marketing|btl|eventos|comunicacion|medios|agencia", "7310", 190),
    ("pat_mach_01", r"maquinaria|equipos|repuestos|industrial", "4659", 200),
    ("pat_tex_wholes_01", r"(comercio|distribuidora|mayorista|almacen).*(telas|textil|ropa|confeccion)", "4641", 210),
    ("pat_app_ret_01", r"boutique|tienda de ropa|almacen de ropa|venta de prendas|venta de ropa", "4771", 220),
    ("pat_shoe_ret_01", r"zapateria|tienda de calzado|almacen de calzado|venta de calzado", "4772", 230),
    ("pat_app_mfg_01", r"confeccion|confecciones|prendas de vestir|ropa|costura|maquila textil|uniformes|sastreria|camiseria|pantalones|vestidos|lenceria|moda", "1410", 240),
    ("pat_shoe_mfg_01", r"calzado|zapater|fabrica de zapatos|botas|suelas|marroquiner|curtiembre|cueros|bolsos de cuero|billeteras de cuero", "1521", 250),
    ("pat_tex_mfg_01", r"textil|textiles|hilatura|hilados|hilanderia|hilaza|tejeduria|telas|tejidos|dril|denim|indigo|tintoreria textil|estampado textil", "1312", 260),
    ("pat_gen_dist_01", r"distribuid|distribuc|comercializad|comercializac|mayorist", "4690", 270),
    ("pat_gen_cons_01", r"\b(consultor|asesor|asesoria|consultoria|advisory|estrategi)\b", "7020", 280),
]

# Seed procurement mappings for Dominican Republic 🇩🇴 (DGCP) and Ecuador 🇪🇨 (SERCOP)
DGCP_RUBROS_MAP: Dict[str, List[str]] = {
    "13": ["textiles", "telas", "hilos", "hilanderia"],
    "14": ["confecciones", "prendas de vestir", "uniformes", "ropa"],
    "15": ["calzado", "zapatos", "botas", "articulos de cuero"],
    "31": ["muebles", "sillas", "silleria", "mobiliario"],
    "41": ["construccion", "obras civiles", "edificaciones"],
    "46": ["distribuidora", "suministros", "comercio al por mayor"],
    "47": ["tiendas especializadas", "almacenes", "retail"],
    "49": ["transporte", "carga", "fletes", "camiones"],
    "62": ["software", "tecnologia", "sistemas", "informatica", "desarrollo"],
    "63": ["hosting", "datos", "servidores", "cloud"],
    "69": ["legal", "abogados", "juridico", "contabilidad", "auditoria"],
    "70": ["consultoria", "gestion empresarial", "estrategia"],
    "81": ["limpieza", "facility", "mantenimiento locativo", "seguridad"],
    "85": ["educacion", "capacitacion", "colegio", "escuela", "carnet"],
    "86": ["salud", "medico", "hospital", "clinica", "dispositivos"],
    "95": ["reparacion", "mantenimiento", "tapiceria"],
}

SERCOP_CPC_MAP: Dict[str, List[str]] = {
    "13": ["productos textiles", "hilados", "tejidos", "telas"],
    "14": ["prendas de vestir", "confecciones", "uniformes"],
    "15": ["calzado", "cueros", "artículos de piel"],
    "31": ["muebles", "sillas", "mobiliario de oficina", "silletería"],
    "41": ["construcción", "obras civiles", "edificaciones"],
    "49": ["transporte de carga", "logística", "fletes", "camiones"],
    "62": ["software", "sistemas", "computación", "tecnología", "desarrollo"],
    "63": ["procesamiento de datos", "hosting", "servidores", "nube"],
    "69": ["jurídico", "abogados", "contabilidad", "auditoría"],
    "70": ["consultoría de gestión", "estrategia empresarial"],
    "81": ["limpieza", "mantenimiento de edificios", "seguridad", "facility"],
    "85": ["educación", "enseñanza", "colegio", "escuela", "capacitación"],
    "86": ["salud", "atención médica", "hospitales", "dispositivos médicos"],
    "95": ["reparación", "mantenimiento de muebles", "tapicería"],
}

# Exclusion rules / Blacklist
SEED_EXCLUSION_RULES = [
    ("rule_rep_01", None, "ALL", "representative_placeholder", "liquidador"),
    ("rule_rep_02", None, "ALL", "representative_placeholder", "liquidadora"),
    ("rule_rep_03", None, "ALL", "bankrupt_status", "en liquidacion"),
    ("rule_rep_04", None, "ALL", "bankrupt_status", "en liquidación"),
    ("rule_rep_05", None, "ALL", "representative_placeholder", "revisor fiscal"),
    ("rule_rep_06", None, "ALL", "representative_placeholder", "secretario ad-hoc"),
    ("rule_rep_07", None, "ALL", "representative_placeholder", "agente especial"),
    ("rule_rep_08", None, "ALL", "representative_placeholder", "no registra"),
    ("rule_rep_09", None, "ALL", "representative_placeholder", "no reporta"),
    ("rule_rep_10", None, "ALL", "representative_placeholder", "sin representante"),
    ("rule_rep_11", None, "ALL", "representative_placeholder", "en tramite"),
    ("rule_rep_12", None, "ALL", "representative_placeholder", "en trámite"),
    ("rule_food_contra_01", "food_agriculture", "ALL", "sector_contradiction", "papeleria"),
    ("rule_food_contra_02", "food_agriculture", "ALL", "sector_contradiction", "contabilidad"),
    ("rule_food_contra_03", "food_agriculture", "ALL", "sector_contradiction", "construccion"),
    ("rule_food_contra_04", "food_agriculture", "ALL", "sector_contradiction", "metalmecanica"),
    ("rule_food_contra_05", "food_agriculture", "ALL", "sector_contradiction", "software"),
    ("rule_food_contra_06", "food_agriculture", "ALL", "sector_contradiction", "inmobiliaria"),
]


def run_migration(db_url: str):
    logger.info(f"Connecting to database: {db_url}")
    engine = create_engine(db_url)

    # 1. Create tables
    logger.info("Step 1: Creating taxonomy schema tables if missing...")
    Base.metadata.create_all(bind=engine)

    # 1.0 Alter Enterprise Graph columns to VARCHAR(128) if PostgreSQL
    if engine.dialect.name == "postgresql":
        logger.info("Step 1.0: Ensuring VARCHAR(128) on enterprise graph primary and foreign keys...")
        with engine.begin() as conn:
            for ddl in (
                "ALTER TABLE company_individual_roles ALTER COLUMN role_id TYPE VARCHAR(128)",
                "ALTER TABLE company_individual_roles ALTER COLUMN company_id TYPE VARCHAR(128)",
                "ALTER TABLE company_individual_roles ALTER COLUMN individual_id TYPE VARCHAR(128)",
                "ALTER TABLE company_channel_links ALTER COLUMN link_id TYPE VARCHAR(128)",
                "ALTER TABLE company_channel_links ALTER COLUMN company_id TYPE VARCHAR(128)",
                "ALTER TABLE company_channel_links ALTER COLUMN channel_id TYPE VARCHAR(128)",
                "ALTER TABLE individual_channel_links ALTER COLUMN link_id TYPE VARCHAR(128)",
                "ALTER TABLE individual_channel_links ALTER COLUMN individual_id TYPE VARCHAR(128)",
                "ALTER TABLE individual_channel_links ALTER COLUMN channel_id TYPE VARCHAR(128)",
                "ALTER TABLE contact_channels ALTER COLUMN channel_id TYPE VARCHAR(128)",
                "ALTER TABLE individuals ALTER COLUMN individual_id TYPE VARCHAR(128)",
                "ALTER TABLE companies ALTER COLUMN company_id TYPE VARCHAR(128)",
            ):
                try:
                    conn.execute(text(ddl))
                except Exception as alter_err:
                    logger.debug(f"DDL alter notice ({ddl}): {alter_err}")

    with Session(engine) as session:
        # 1.1 Seed fundamental locations, roles, and sectors
        logger.info("Step 1.1: Seeding fundamental locations, roles, and sectors...")
        seed_stats = seed_all_taxonomy(session)
        logger.info(f"Fundamental taxonomy seeded: {seed_stats}")

        # 2. Seed taxonomy_isic_codes
        logger.info("Step 2: Seeding Universal ISIC codes into taxonomy_isic_codes...")
        existing_codes = set(session.scalars(select(TaxonomyIsicCodeModel.code)).all())
        new_isic_count = 0

        for code, entry in UNIVERSAL_ISIC_CATALOG.items():
            if code not in existing_codes:
                isic_model = TaxonomyIsicCodeModel(
                    code=code,
                    division=entry.division,
                    section=entry.section,
                    section_title=entry.section_title,
                    title=entry.title,
                    sector_macro=entry.sector_macro,
                    keywords=list(entry.keywords),
                    is_active=True,
                    version=1,
                )
                session.add(isic_model)
                existing_codes.add(code)
                new_isic_count += 1

        session.commit()
        logger.info(f"Seeded {new_isic_count} new ISIC codes (Total in DB: {len(existing_codes)}).")

        # 3. Seed taxonomy_roles and taxonomy_isic_role_links
        logger.info("Step 3: Seeding executive roles and ISIC-role junction links...")
        existing_roles = {r.canonical_title: r.role_id for r in session.scalars(select(TaxonomyRoleModel)).all()}
        role_links_seeded = 0

        for code, entry in UNIVERSAL_ISIC_CATALOG.items():
            for country_key, roles in entry.typical_roles.items():
                for rank, r_title in enumerate(roles, start=1):
                    # Ensure role exists in taxonomy_roles
                    if r_title not in existing_roles:
                        slug = re.sub(r"[^\w]+", "_", r_title.lower()).strip("_")
                        role_id = f"role_{slug}"[:64]
                        new_role = TaxonomyRoleModel(
                            role_id=role_id,
                            canonical_title=r_title,
                            seniority_level="directivo",
                            functional_domain="general",
                            country_code="ALL",
                            is_active=True,
                        )
                        session.add(new_role)
                        session.flush()
                        existing_roles[r_title] = role_id

                    role_id = existing_roles[r_title]

                    # Check link
                    exists = session.scalar(
                        select(TaxonomyIsicRoleLinkModel.link_id).where(
                            TaxonomyIsicRoleLinkModel.isic_code == code,
                            TaxonomyIsicRoleLinkModel.role_id == role_id,
                            TaxonomyIsicRoleLinkModel.country_code == country_key,
                        )
                    )
                    if not exists:
                        link = TaxonomyIsicRoleLinkModel(
                            isic_code=code,
                            role_id=role_id,
                            country_code=country_key,
                            priority_rank=rank,
                        )
                        session.add(link)
                        role_links_seeded += 1

        session.commit()
        logger.info(f"Seeded {role_links_seeded} ISIC-role junction links.")

        # 4. Seed taxonomy_isic_country_registries
        logger.info("Step 4: Seeding cross-country procurement registry translations...")
        registry_links_seeded = 0

        for code, entry in UNIVERSAL_ISIC_CATALOG.items():
            div = entry.division

            # Colombia 🇨🇴 SECOP/SODA registry mapping
            exists_co = session.scalar(
                select(TaxonomyIsicCountryRegistryModel.registry_id).where(
                    TaxonomyIsicCountryRegistryModel.isic_code == code,
                    TaxonomyIsicCountryRegistryModel.country_code == "CO",
                    TaxonomyIsicCountryRegistryModel.registry_system == "secop_soda",
                )
            )
            if not exists_co:
                search_kw = entry.keywords[0] if entry.keywords else entry.title
                reg_co = TaxonomyIsicCountryRegistryModel(
                    isic_code=code,
                    country_code="CO",
                    registry_system="secop_soda",
                    external_code=code,
                    external_label=entry.title,
                    search_keyword=search_kw,
                    is_active=True,
                )
                session.add(reg_co)
                registry_links_seeded += 1

            # Dominican Republic 🇩🇴 DGCP rubros
            if div in DGCP_RUBROS_MAP:
                rubros = DGCP_RUBROS_MAP[div]
                for rub in rubros:
                    exists_do = session.scalar(
                        select(TaxonomyIsicCountryRegistryModel.registry_id).where(
                            TaxonomyIsicCountryRegistryModel.isic_code == code,
                            TaxonomyIsicCountryRegistryModel.country_code == "DO",
                            TaxonomyIsicCountryRegistryModel.registry_system == "dgcp_rubro",
                            TaxonomyIsicCountryRegistryModel.external_code == rub,
                        )
                    )
                    if not exists_do:
                        reg_do = TaxonomyIsicCountryRegistryModel(
                            isic_code=code,
                            country_code="DO",
                            registry_system="dgcp_rubro",
                            external_code=rub,
                            external_label=f"Rubro {rub.title()} ({entry.title})",
                            search_keyword=rub,
                            is_active=True,
                        )
                        session.add(reg_do)
                        registry_links_seeded += 1

            # Ecuador 🇪🇨 SERCOP CPC codes
            if div in SERCOP_CPC_MAP:
                cpcs = SERCOP_CPC_MAP[div]
                for cpc_term in cpcs:
                    exists_ec = session.scalar(
                        select(TaxonomyIsicCountryRegistryModel.registry_id).where(
                            TaxonomyIsicCountryRegistryModel.isic_code == code,
                            TaxonomyIsicCountryRegistryModel.country_code == "EC",
                            TaxonomyIsicCountryRegistryModel.registry_system == "sercop_cpc",
                            TaxonomyIsicCountryRegistryModel.external_code == cpc_term,
                        )
                    )
                    if not exists_ec:
                        reg_ec = TaxonomyIsicCountryRegistryModel(
                            isic_code=code,
                            country_code="EC",
                            registry_system="sercop_cpc",
                            external_code=cpc_term,
                            external_label=f"CPC {cpc_term.title()} ({entry.title})",
                            search_keyword=cpc_term,
                            is_active=True,
                        )
                        session.add(reg_ec)
                        registry_links_seeded += 1

        session.commit()
        logger.info(f"Seeded {registry_links_seeded} cross-country registry translation rows.")

        # 5. Seed taxonomy_sector_isic_links
        logger.info("Step 5: Seeding Sector-ISIC junction relationships...")
        sector_links_seeded = 0

        # Ensure SECTOR_SEEDS are in taxonomy_sectors
        for s_data in SECTOR_SEEDS:
            sec_id = s_data["sector_id"]
            sec_exists = session.scalar(select(TaxonomySectorModel.sector_id).where(TaxonomySectorModel.sector_id == sec_id))
            if not sec_exists:
                sec_obj = TaxonomySectorModel(
                    sector_id=sec_id,
                    sector_name=s_data["sector_name"],
                    country_code=s_data.get("country_code", "ALL"),
                    allowed_isic_divisions=s_data.get("allowed_isic_divisions", []),
                    forbidden_isic_divisions=s_data.get("forbidden_isic_divisions", []),
                    keywords_include=s_data.get("keywords_include", []),
                    keywords_exclude_defaults=s_data.get("keywords_exclude_defaults", []),
                    is_active=True,
                )
                session.add(sec_obj)
                session.flush()

            allowed_divs = set(s_data.get("allowed_isic_divisions", []))
            forbidden_divs = set(s_data.get("forbidden_isic_divisions", []))

            for code, entry in UNIVERSAL_ISIC_CATALOG.items():
                rel = None
                if entry.division in allowed_divs:
                    rel = "allowed"
                elif entry.division in forbidden_divs:
                    rel = "forbidden"

                if rel:
                    link_exists = session.scalar(
                        select(TaxonomySectorIsicLinkModel.link_id).where(
                            TaxonomySectorIsicLinkModel.sector_id == sec_id,
                            TaxonomySectorIsicLinkModel.isic_code == code,
                            TaxonomySectorIsicLinkModel.relation_type == rel,
                        )
                    )
                    if not link_exists:
                        sec_link = TaxonomySectorIsicLinkModel(
                            sector_id=sec_id,
                            isic_code=code,
                            relation_type=rel,
                        )
                        session.add(sec_link)
                        sector_links_seeded += 1

        session.commit()
        logger.info(f"Seeded {sector_links_seeded} Sector-ISIC links.")

        # 6. Seed taxonomy_semantic_patterns
        logger.info("Step 6: Seeding deterministic & agent-learned semantic patterns...")
        patterns_seeded = 0
        for pat_id, regex, target_code, prio in SEED_SEMANTIC_PATTERNS:
            pat_exists = session.scalar(select(TaxonomySemanticPatternModel.pattern_id).where(TaxonomySemanticPatternModel.pattern_id == pat_id))
            if not pat_exists:
                pat_obj = TaxonomySemanticPatternModel(
                    pattern_id=pat_id,
                    target_isic_code=target_code,
                    regex_pattern=regex,
                    country_code="ALL",
                    priority=prio,
                    source="seed",
                    is_active=True,
                )
                session.add(pat_obj)
                patterns_seeded += 1

        session.commit()
        logger.info(f"Seeded {patterns_seeded} semantic classification patterns.")

        # 7. Seed taxonomy_exclusion_rules
        logger.info("Step 7: Seeding exclusion rules & representative blacklists...")
        exclusions_seeded = 0
        for r_id, s_id, c_code, r_type, r_term in SEED_EXCLUSION_RULES:
            ex_exists = session.scalar(select(TaxonomyExclusionRuleModel.rule_id).where(TaxonomyExclusionRuleModel.rule_id == r_id))
            if not ex_exists:
                ex_obj = TaxonomyExclusionRuleModel(
                    rule_id=r_id,
                    target_sector_id=s_id,
                    country_code=c_code,
                    rule_type=r_type,
                    term=r_term,
                    is_active=True,
                )
                session.add(ex_obj)
                exclusions_seeded += 1

        session.commit()
        logger.info(f"Seeded {exclusions_seeded} exclusion rules.")

    logger.info("Relational taxonomy migration & seeding completed successfully!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate and seed relational taxonomy schema")
    parser.add_argument("--db-url", type=str, default="", help="PostgreSQL or SQLite database connection URL")
    args = parser.parse_args()

    target_url = args.db_url or os.getenv("DATABASE_URL", "postgresql+psycopg://127.0.0.1:5432/michito")
    run_migration(target_url)
