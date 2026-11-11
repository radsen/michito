import os
import pytest
from src.adapters.export.pdf_dossier_adapter import PdfDossierAdapter

def test_pdf_dossier_adapter_generation(tmp_path):
    adapter = PdfDossierAdapter()
    
    rows = [
        {
            "Index": 1,
            "Country": "CO",
            "Country Name": "Colombia",
            "Company Name": "Constructora Andina SAS",
            "Tax ID Type": "NIT",
            "Tax ID": "900123456-1",
            "City": "Medellín",
            "Activity Code": "4111",
            "Sector Macro": "Construcción e Ingeniería",
            "Economic Activity": "Construcción de edificios residenciales",
            "Company Size": "Mediana Empresa",
            "Revenue Bracket": "$10.000M - $65.000M COP",
            "Estimated Employees": "50 - 200 empleados",
            "Address": "Cra 43A # 1-50 Of 402",
            "Website": "https://andina.co",
            "Website Audit Status": "Sitio Web Activo (HTTP 200)",
            "Decision Maker Name": "Carlos Mario Restrepo",
            "Official Title": "Representante Legal Estatutario",
            "Verified Work Email": "carlos.restrepo@andina.co",
            "Direct Mobile Phone": "+57 312 456 7890",
            "Mail Server (MX)": "mail.andina.co",
            "Trigger 1: Total Contracts Won": "$1,450,000,000 COP",
            "Trigger 1: Currency": "COP",
            "Trigger 1: Top Contracting Entity": "Alcaldía de Medellín",
            "Trigger 1: Top Contract Object": "Construcción de infraestructura educativa comunitaria",
            "Trigger 1: Intent Score": "Alto",
            "Trigger 2: Hiring X-Ray Search URL": "https://google.com/search?q=andina+jobs",
            "Trigger 3: Regional Expansion Flag": "Expansión Regional Activa",
            "LinkedIn X-Ray URL": "https://google.com/search?q=andina+linkedin",
            "Touch 1: LinkedIn Connection Note": "Hola Carlos, felicitaciones por la adjudicación del contrato con Alcaldía de Medellín.",
            "Touch 2: Cold Email Subject": "Espacios flexibles para el equipo de obra en Medellín",
            "Touch 2: Cold Email Body": "Estimado Carlos,\n\nFelicitaciones por la adjudicación del contrato reciente.\nOfrecemos sedes corporativas flexibles.",
            "Touch 3: Operational Follow-up Subject": "Seguimiento operativo para Constructora Andina",
            "Touch 3: Operational Follow-up Body": "Hola Carlos, ¿pudiste revisar la propuesta anterior?",
            "Touch 4: Social Proof / VIP Subject": "Pase VIP corporativo para Constructora Andina",
            "Touch 4: Social Proof / VIP Body": "Te invitamos un día de prueba en nuestras instalaciones.",
            "Touch 5: Breakup / Catalog Subject": "Catálogo corporativo y despedida temporal",
            "Touch 5: Breakup / Catalog Body": "Te dejo nuestro catálogo corporativo por si lo necesitan en el futuro.",
            "Underwriting Grade": "AAA",
            "Composite Quality Score (0-100)": 96,
            "Solvency: Estimated EBITDA (COP)": 450000000.0,
            "Solvency: EBITDA Margin (%)": 22.5,
            "Solvency: Tier": "Solvente",
            "Solvency: Profile Summary": "Excelente liquidez patrimonial y EBITDA positivo",
            "Legal Risk: Litigation Status": "Bajo Riesgo (Sin Demandas)",
            "Legal Risk: Dockets & Sanctions Summary": "0 procesos en Rama Judicial",
            "Credit Terms Recommendation": "Aprobado para crédito comercial",
        }
    ]

    output_pdf = os.path.join(tmp_path, "dossier.pdf")
    res = adapter.generate_dossier_pdf(
        campaign_cfg={"name": "Tinkko Enterprise Offices", "id": "tinkko_enterprise_offices", "target": {"country": "CO"}},
        leads=rows,
        output_path=output_pdf,
        tier=3
    )

    assert os.path.exists(res)
    assert os.path.getsize(res) > 2000  # ReportLab generates a multi-kilobyte PDF

