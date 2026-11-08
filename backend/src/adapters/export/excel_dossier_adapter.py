import csv
from typing import List
from src.application.ports.dossier_export_port import DossierExportPort
from src.application.dto.lead_dossier_dto import LeadDossierDto

class ExcelDossierAdapter(DossierExportPort):
    def __init__(self, brand_header: str = "Michito Intelligence"):
        self.brand_header = brand_header

    def export(self, dossiers: List[LeadDossierDto], output_path: str) -> str:
        # Since openpyxl is not available, we fall back to a "CSV" based "Excel" export
        # Excel opens CSV files naturally.
        with open(output_path, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            
            # Branded header
            writer.writerow([f"--- {self.brand_header} Dossier Export ---"])
            writer.writerow([])
            
            # Column headers
            headers = [
                "Company ID", "Company Name", "Tax ID", "Industry", 
                "Revenue (COP)", "EBITDA (COP)", "EBITDA Margin (%)", 
                "Litigation Count", "Email Deliverability", "Composite Score"
            ]
            writer.writerow(headers)
            
            for d in dossiers:
                writer.writerow([
                    d.company_id,
                    d.company_name,
                    d.tax_id,
                    d.industry,
                    str(d.revenue),
                    str(d.ebitda),
                    str(d.ebitda_margin),
                    d.litigation_count,
                    d.email_deliverability,
                    str(d.composite_score)
                ])
                
        return output_path
