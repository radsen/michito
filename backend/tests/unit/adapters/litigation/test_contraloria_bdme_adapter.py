import pytest
from src.adapters.litigation.contraloria_bdme_adapter import ContraloriaBdmeAdapter

def test_contraloria_bdme_adapter_sanction_1():
    adapter = ContraloriaBdmeAdapter()
    records = adapter.screen_litigation("800987654")
    assert len(records) == 1
    assert records[0].status == "Fiscal Debt Sanction"
    assert records[0].company_id == "800987654"

def test_contraloria_bdme_adapter_sanction_2():
    adapter = ContraloriaBdmeAdapter()
    records = adapter.screen_litigation("900123456")
    assert len(records) == 1
    assert records[0].status == "Fiscal Debt Sanction"
    assert records[0].company_id == "900123456"

def test_contraloria_bdme_adapter_no_records():
    adapter = ContraloriaBdmeAdapter()
    records = adapter.screen_litigation("000000000")
    assert len(records) == 0
