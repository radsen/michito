import os
import csv
from decimal import Decimal
from src.adapters.export.excel_dossier_adapter import ExcelDossierAdapter
from src.application.dto.lead_dossier_dto import LeadDossierDto

def test_excel_dossier_adapter_export(tmp_path):
    adapter = ExcelDossierAdapter(brand_header="Michito Premium")
    
    dossiers = [
        LeadDossierDto(
            company_id="c1",
            company_name="Tech Co",
            tax_id="900111222",
            industry="IT",
            revenue=Decimal("1000000000"),
            ebitda=Decimal("200000000"),
            ebitda_margin=Decimal("0.2"),
            litigation_count=0,
            email_deliverability="VERIFIED",
            composite_score=0.95
        ),
        LeadDossierDto(
            company_id="c2",
            company_name="Agri Corp",
            tax_id="800333444",
            industry="Agriculture",
            revenue=Decimal("5000000000"),
            ebitda=Decimal("500000000"),
            ebitda_margin=Decimal("0.1"),
            litigation_count=2,
            email_deliverability="RISKY",
            composite_score=0.75
        )
    ]
    
    output_file = os.path.join(tmp_path, "export.csv")
    adapter.export(dossiers, output_file)
    
    assert os.path.exists(output_file)
    
    with open(output_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        rows = list(reader)
        
        assert rows[0][0] == "--- Michito Premium Dossier Export ---"
        assert rows[1] == []
        assert rows[2] == [
            "Company ID", "Company Name", "Tax ID", "Industry", 
            "Revenue (COP)", "EBITDA (COP)", "EBITDA Margin (%)", 
            "Litigation Count", "Email Deliverability", "Composite Score"
        ]
        
        # Check first data row
        assert rows[3][1] == "Tech Co"
        assert rows[3][9] == "0.95"
        
        # Check second data row
        assert rows[4][1] == "Agri Corp"
        assert rows[4][7] == "2"
