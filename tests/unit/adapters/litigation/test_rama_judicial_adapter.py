import pytest
from src.adapters.litigation.rama_judicial_adapter import RamaJudicialAdapter

def test_rama_judicial_adapter_cobro():
    adapter = RamaJudicialAdapter()
    records = adapter.screen_litigation("900123456")
    assert len(records) == 1
    assert records[0].status == "Proceso Ejecutivo de Cobro"
    assert records[0].company_id == "900123456"

def test_rama_judicial_adapter_laboral():
    adapter = RamaJudicialAdapter()
    records = adapter.screen_litigation("900654321")
    assert len(records) == 1
    assert records[0].status == "Proceso Laboral Ordinario"
    assert records[0].company_id == "900654321"

def test_rama_judicial_adapter_insolvency():
    adapter = RamaJudicialAdapter()
    records = adapter.screen_litigation("900111222")
    assert len(records) == 1
    assert records[0].status == "Ley 1116 Insolvency"
    assert records[0].company_id == "900111222"

def test_rama_judicial_adapter_no_records():
    adapter = RamaJudicialAdapter()
    records = adapter.screen_litigation("000000000")
    assert len(records) == 0
