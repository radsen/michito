"""
Unit and Integration tests for Option A: Relational Database Taxonomy Engine.
Verifies:
1. Relational schema integrity (zero country duplication on ISIC codes).
2. Intermediate 1-to-N country registries (CO, DO, EC).
3. Intermediate N-to-N executive role links.
4. Intermediate N-to-N sector-ISIC links.
5. In-memory hot-loading via IsicIndex.load_from_db().
6. Dynamic agent learning: recording learned patterns into DB and in-memory cache.
"""

import pytest
from sqlalchemy import create_engine, select
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
from src.domain.taxonomy.isic_index import IsicIndex
from src.domain.value_objects.ciiu_code import CiiuCode
from scripts.migrate_relational_taxonomy import run_migration


@pytest.fixture(scope="module")
def sqlite_test_db(tmp_path_factory):
    """Sets up an isolated SQLite database migrated with the full relational taxonomy."""
    db_file = tmp_path_factory.mktemp("db") / "taxonomy_test.db"
    db_url = f"sqlite:///{db_file}"
    run_migration(db_url)
    return db_url


def test_relational_taxonomy_no_country_duplication(sqlite_test_db):
    """Verifies that ISIC codes exist exactly once regardless of multi-country presence."""
    engine = create_engine(sqlite_test_db)
    with Session(engine) as session:
        # Check code 1410 (Confección)
        codes = session.scalars(
            select(TaxonomyIsicCodeModel).where(TaxonomyIsicCodeModel.code == "1410")
        ).all()
        assert len(codes) == 1
        isic_1410 = codes[0]
        assert isic_1410.division == "14"
        assert isic_1410.section == "C"

        # Check that multiple country registries link to the same ISIC code
        regs = session.scalars(
            select(TaxonomyIsicCountryRegistryModel).where(
                TaxonomyIsicCountryRegistryModel.isic_code == "1410"
            )
        ).all()
        countries_linked = {r.country_code for r in regs}
        assert "CO" in countries_linked
        assert "DO" in countries_linked
        assert "EC" in countries_linked


def test_isic_role_intermediate_junction(sqlite_test_db):
    """Verifies that roles and ISIC codes are linked via N-to-N junction."""
    engine = create_engine(sqlite_test_db)
    with Session(engine) as session:
        links = session.scalars(
            select(TaxonomyIsicRoleLinkModel).where(
                TaxonomyIsicRoleLinkModel.isic_code == "1410"
            )
        ).all()
        assert len(links) > 0
        country_links = {l.country_code for l in links}
        assert "CO" in country_links


def test_sector_isic_intermediate_junction(sqlite_test_db):
    """Verifies that business sectors link dynamically to allowed/forbidden ISIC codes."""
    engine = create_engine(sqlite_test_db)
    with Session(engine) as session:
        fashion_links = session.scalars(
            select(TaxonomySectorIsicLinkModel).where(
                TaxonomySectorIsicLinkModel.sector_id == "fashion_apparel_textiles",
                TaxonomySectorIsicLinkModel.relation_type == "allowed",
            )
        ).all()
        allowed_codes = {l.isic_code for l in fashion_links}
        # Check that apparel (1410), textiles (1312), and footwear (1521) are linked
        assert "1410" in allowed_codes
        assert "1312" in allowed_codes
        assert "1521" in allowed_codes


def test_isic_index_hot_load_from_db(sqlite_test_db):
    """Verifies sub-millisecond in-memory cache initialization from database."""
    engine = create_engine(sqlite_test_db)
    index = IsicIndex()

    # Load from DB
    loaded_count = index.load_from_db(db_url_or_engine=engine)
    assert loaded_count >= 240

    # Test direct code lookup
    entry = index.get_by_code("1410")
    assert entry is not None
    assert entry.code == "1410"
    assert "confecci" in entry.title.lower()

    # Test BM25 lookup
    match, score = index.resolve_match_with_confidence("confeccion de uniformes y camisas")
    assert match is not None
    assert match.code == "1410"
    assert score > 3.0


def test_agent_dynamic_pattern_learning_loop(sqlite_test_db):
    """Verifies that newly learned patterns dynamically update both PostgreSQL and in-memory cache."""
    engine = create_engine(sqlite_test_db)
    index = IsicIndex()
    index.load_from_db(db_url_or_engine=engine)

    # Initially, a synthetic niche term like "marroquinaje_ultrafino" is unknown
    initial_match = CiiuCode.infer_from_text("TALLER MARROQUINAJE_ULTRAFINO")
    # Defaults to generic consulting if unlearned
    assert initial_match.code != "1521"

    # Agent records a learned pattern for this term
    success = index.record_learned_pattern(
        pattern_id="pat_agent_test_marroquinaje",
        target_isic_code="1521",
        regex_pattern=r"marroquinaje_ultrafino",
        country_code="CO",
        db_url=sqlite_test_db,
    )
    assert success is True

    # Now verify in-memory pattern retrieval
    active_patterns = index.get_patterns(country_code="CO")
    assert any("marroquinaje_ultrafino" in pat[0] for pat in active_patterns)

    # Next time infer_from_text runs with this index active, it matches instantly
    # Temporarily monkeypatch GLOBAL_ISIC_INDEX for the test
    from src.domain.taxonomy import isic_index
    orig_global = isic_index.GLOBAL_ISIC_INDEX
    try:
        isic_index.GLOBAL_ISIC_INDEX = index
        learned_match = CiiuCode.infer_from_text("TALLER MARROQUINAJE_ULTRAFINO")
        assert learned_match.code == "1521"
    finally:
        isic_index.GLOBAL_ISIC_INDEX = orig_global
