import csv
import os
from typing import List, Dict, Any, Optional
from src.application.ports.dossier_export_port import DossierExportPort
from src.application.dto.lead_dossier_dto import LeadDossierDto

try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False


class ExcelDossierAdapter(DossierExportPort):
    def __init__(self, brand_header: str = "Michito Intelligence"):
        self.brand_header = brand_header

    def export(self, dossiers: List[LeadDossierDto], output_path: str) -> str:
        """
        Original export method for LeadDossierDto.
        Writes CSV if output_path ends with .csv, or delegates to CSV fallback.
        """
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

    def export_prospects_xlsx(
        self,
        rows: List[Dict[str, Any]],
        output_path: str,
        campaign_title: str = "Michito Intelligence"
    ) -> str:
        """
        Exports a list of B2B prospect dictionaries into a styled, CRM-ready .xlsx spreadsheet.
        Features:
        - Frozen header at row 1 (A2)
        - Dark Navy (#1E293B) header with crisp white text
        - Auto-filters enabled across all columns
        - Zebra striping for enhanced visual scanning
        - Auto-fitted column widths with min/max caps
        - Hyperlinks for websites, LinkedIn X-Ray, and Hiring X-Ray URLs
        - No multiline text walls (CRM ingestion safe)
        """
        if not rows:
            # Empty workbook fallback
            if OPENPYXL_AVAILABLE:
                wb = openpyxl.Workbook()
                ws = wb.active if wb.active is not None else wb.create_sheet()
                ws.title = "Prospectos"
                wb.save(output_path)
            else:
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write("")
            return output_path

        if not OPENPYXL_AVAILABLE:
            # Fallback to CSV if openpyxl is not installed
            csv_path = output_path.replace(".xlsx", ".csv")
            with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)
            return csv_path

        wb = openpyxl.Workbook()
        ws = wb.active if wb.active is not None else wb.create_sheet()
        ws.title = "Prospectos CRM"
        ws.sheet_view.showGridLines = True

        headers = list(rows[0].keys())

        # Define Styles
        header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
        header_font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
        header_align = Alignment(vertical="center", horizontal="center", wrap_text=False)

        thin_side = Side(border_style="thin", color="E2E8F0")
        cell_border = Border(top=thin_side, left=thin_side, right=thin_side, bottom=thin_side)

        data_font = Font(name="Calibri", size=10, color="0F172A")
        link_font = Font(name="Calibri", size=10, color="2563EB", underline="single")

        even_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
        odd_fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")

        # 1. Write Header Row
        ws.row_dimensions[1].height = 26
        for col_idx, header_name in enumerate(headers, start=1):
            cell = ws.cell(row=1, column=col_idx, value=header_name)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = header_align
            cell.border = cell_border

        # 2. Write Data Rows
        for row_idx, r_dict in enumerate(rows, start=2):
            ws.row_dimensions[row_idx].height = 20
            row_fill = even_fill if (row_idx % 2 == 0) else odd_fill

            for col_idx, header_name in enumerate(headers, start=1):
                val = r_dict.get(header_name, "")
                cell = ws.cell(row=row_idx, column=col_idx)
                cell.fill = row_fill
                cell.border = cell_border
                cell.font = data_font

                # Formats & Hyperlinks
                if isinstance(val, str) and (val.startswith("http://") or val.startswith("https://")):
                    cell.value = val
                    cell.hyperlink = val
                    cell.font = link_font
                    cell.alignment = Alignment(vertical="center", horizontal="left")
                elif header_name in ("Index", "Country", "Tax ID Type", "Activity Code", "Composite Quality Score (0-100)", "Underwriting Grade", "Solvency: Tier"):
                    cell.value = val
                    cell.alignment = Alignment(vertical="center", horizontal="center")
                else:
                    cell.value = val
                    cell.alignment = Alignment(vertical="center", horizontal="left")

        # 3. Freeze Header Row and Enable Filters
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions

        # 4. Auto-fit column widths with min 12 and max 50 caps
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                val_str = str(cell.value or "")
                if len(val_str) > max_len:
                    max_len = len(val_str)
            col_width = min(max(max_len + 3, 12), 50)
            ws.column_dimensions[col_letter].width = col_width

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        wb.save(output_path)
        return output_path
