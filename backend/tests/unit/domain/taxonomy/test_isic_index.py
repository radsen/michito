"""
Unit tests for the Universal ISIC / CIIU Rev. 4 In-Memory Search Index.
"""

import pytest
from backend.src.domain.taxonomy.isic_index import IsicIndex, normalize_text, tokenize, GLOBAL_ISIC_INDEX


def test_normalize_and_tokenize():
    assert normalize_text("Educación Básica y Colegios Privados!") == "educacion basica y colegios privados"
    tokens = tokenize("Educación de instituciones universitarias y colegios")
    assert "educacion" in tokens
    assert "universitarias" in tokens
    assert "colegios" in tokens
    assert "de" not in tokens
    assert "y" not in tokens


def test_isic_index_exact_code_lookup():
    entry = GLOBAL_ISIC_INDEX.get_by_code("8530")
    assert entry is not None
    assert entry.code == "8530"
    assert "educacion" in entry.title.lower() or "establecimientos" in entry.title.lower()


def test_isic_index_school_search():
    results = GLOBAL_ISIC_INDEX.search("colegios privados escuelas primaria y secundaria", limit=3)
    assert len(results) > 0
    top_entry, score = results[0]
    # Should resolve to education section P (85xx)
    assert top_entry.section == "P"
    assert top_entry.code.startswith("85")


def test_isic_index_furniture_maintenance():
    # User's exact example: "Tinkko look for providers in January to repair furniture for their clients"
    entry = GLOBAL_ISIC_INDEX.resolve_best_match("reparacion y mantenimiento de muebles de oficina")
    assert entry is not None
    # Should match furniture repair (9524) or furniture manufacturing (3100) or facility (8110)
    assert entry.code in ["9524", "3100", "8110"] or entry.section in ["C", "S", "N"]


def test_isic_index_software_and_invoicing():
    # User's exact example: "Chiketto look to become software providers for companies like Tinkko"
    entry = GLOBAL_ISIC_INDEX.resolve_best_match("desarrollo de software y facturacion electronica saas")
    assert entry is not None
    assert entry.code in ["5820", "6201", "6202", "6209", "6311"]
    assert entry.section == "J"


def test_isic_index_suggest_roles():
    roles_co = GLOBAL_ISIC_INDEX.suggest_roles("8530", country_code="CO")
    assert any("Rector" in r for r in roles_co)

    roles_ec = GLOBAL_ISIC_INDEX.suggest_roles("8530", country_code="EC")
    assert len(roles_ec) > 0

    roles_do = GLOBAL_ISIC_INDEX.suggest_roles("8530", country_code="DO")
    assert len(roles_do) > 0
