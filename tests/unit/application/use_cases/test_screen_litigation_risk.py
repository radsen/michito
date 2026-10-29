import pytest
from src.application.use_cases.screen_litigation_risk import ScreenLitigationRiskUseCase
from src.adapters.litigation.rama_judicial_adapter import RamaJudicialAdapter
from src.adapters.litigation.contraloria_bdme_adapter import ContraloriaBdmeAdapter

def test_screen_litigation_risk_use_case_aggregation():
    rama_adapter = RamaJudicialAdapter()
    contraloria_adapter = ContraloriaBdmeAdapter()
    
    use_case = ScreenLitigationRiskUseCase(adapters=[rama_adapter, contraloria_adapter])
    
    # 900123456 has a record in Rama Judicial and Contraloria
    records = use_case.execute("900123456")
    assert len(records) == 2
    
    statuses = [r.status for r in records]
    assert "Proceso Ejecutivo de Cobro" in statuses
    assert "Fiscal Debt Sanction" in statuses

def test_screen_litigation_risk_use_case_empty():
    rama_adapter = RamaJudicialAdapter()
    contraloria_adapter = ContraloriaBdmeAdapter()
    
    use_case = ScreenLitigationRiskUseCase(adapters=[rama_adapter, contraloria_adapter])
    
    records = use_case.execute("000000000")
    assert len(records) == 0

def test_screen_litigation_risk_use_case_single_adapter_has_record():
    rama_adapter = RamaJudicialAdapter()
    contraloria_adapter = ContraloriaBdmeAdapter()
    
    use_case = ScreenLitigationRiskUseCase(adapters=[rama_adapter, contraloria_adapter])
    
    records = use_case.execute("800987654")
    assert len(records) == 1
    assert records[0].status == "Fiscal Debt Sanction"
