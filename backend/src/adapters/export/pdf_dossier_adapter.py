"""
Executive PDF Dossier Adapter for Michito B2B Engine.
Compiles qualified prospect batches into an institutional, print-ready PDF
dossier with executive metrics, master qualification tables, and 5-touch omnichannel cadences.
"""

import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
    HRFlowable,
)
from reportlab.pdfgen import canvas


class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically compute and stamp total page count
    and institutional confidentiality footer.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count: int):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))

        # Footer
        footer_text = f"Michito B2B Intent Engine™ • Dossier Confidencial de Prospección • Página {self._pageNumber} de {page_count}"
        self.drawString(36, 24, footer_text)
        guarantee_text = "Garantía 2-por-1 Fair Replacement activa para rebotes duros >3%"
        self.drawRightString(letter[0] - 36, 24, guarantee_text)

        # Thin footer line
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(36, 34, letter[0] - 36, 34)

        self.restoreState()


class PdfDossierAdapter:
    """
    Generates high-impact, C-level executive PDF dossiers for Michito orders.
    """

    def __init__(self, brand_title: str = "Michito B2B Intent Engine"):
        self.brand_title = brand_title

    def generate_dossier_pdf(
        self,
        campaign_cfg: Dict[str, Any],
        leads: List[Dict[str, Any]],
        output_path: str,
        order_id: Optional[str] = None,
        tier: int = 2,
        metrics: Optional[Dict[str, Any]] = None,
    ) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=45,
        )

        styles = getSampleStyleSheet()

        # Custom Professional Palette Styles
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#0F172A"),
        )
        subtitle_style = ParagraphStyle(
            "DocSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=13,
            textColor=colors.HexColor("#475569"),
        )
        h2_style = ParagraphStyle(
            "Heading2Custom",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            textColor=colors.HexColor("#0F172A"),
            spaceBefore=10,
            spaceAfter=6,
        )
        h3_style = ParagraphStyle(
            "Heading3Custom",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            textColor=colors.HexColor("#0369A1"),
            spaceBefore=8,
            spaceAfter=4,
        )
        body_style = ParagraphStyle(
            "BodyCustom",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11.5,
            textColor=colors.HexColor("#1E293B"),
        )
        cadence_header_style = ParagraphStyle(
            "CadenceHeader",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#0369A1"),
        )
        cadence_body_style = ParagraphStyle(
            "CadenceBody",
            parent=styles["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=7.5,
            leading=10,
            textColor=colors.HexColor("#334155"),
        )
        table_cell_style = ParagraphStyle(
            "TableCell",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=9.5,
            textColor=colors.HexColor("#1E293B"),
        )
        table_cell_bold = ParagraphStyle(
            "TableCellBold",
            parent=table_cell_style,
            fontName="Helvetica-Bold",
        )

        elements = []

        # 1. Header Banner Box
        campaign_name = campaign_cfg.get("name", "Campaña B2B")
        campaign_id = campaign_cfg.get("id", "b2b_batch")
        country = campaign_cfg.get("target", {}).get("country", "CO").upper()
        country_display = "Ecuador" if country == "EC" else ("Rep. Dominicana" if country == "DO" else ("Multi-País" if country == "MULTI" else "Colombia"))
        flag_icon = "🇪🇨" if country == "EC" else ("🇩🇴" if country == "DO" else ("🌎" if country == "MULTI" else "🇨🇴"))

        now_str = datetime.now(timezone.utc).strftime("%d/%m/%Y")
        order_tag = f" | Orden: {order_id}" if order_id else ""

        banner_data = [
            [
                Paragraph(f"<b>MICHITO INTENT ENGINE™</b> — DOSSIER EJECUTIVO", ParagraphStyle("Brand", fontName="Helvetica-Bold", fontSize=8, textColor=colors.HexColor("#0284C7"))),
                Paragraph(f"Fecha: {now_str}{order_tag}", ParagraphStyle("Date", fontName="Helvetica", fontSize=8, alignment=2, textColor=colors.HexColor("#64748B"))),
            ],
            [
                Paragraph(f"{flag_icon} {campaign_name}", title_style),
                "",
            ],
            [
                Paragraph(f"<b>Mercado Objetivo:</b> {country_display} • <b>Tier:</b> Tier {tier} • <b>Cuentas Calificadas:</b> {len(leads)} • <b>Entregabilidad MX:</b> 100% Verificada", subtitle_style),
                "",
            ]
        ]
        banner_table = Table(banner_data, colWidths=[400, 140])
        banner_table.setStyle(TableStyle([
            ("SPAN", (0, 1), (1, 1)),
            ("SPAN", (0, 2), (1, 2)),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ]))
        elements.append(banner_table)
        elements.append(Spacer(1, 10))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284C7"), spaceAfter=10))

        # 2. Key Metrics Strip Box
        contracts_count = sum(1 for l in leads if l.get("contracts_data", {}).get("has_contracts"))
        contracts_val_str = ""
        for l in leads:
            cd = l.get("contracts_data", {})
            if cd.get("has_contracts") and cd.get("total_value_display") and cd.get("total_value_display") != "$0 COP":
                contracts_val_str = cd.get("total_value_display")
                break

        kpi_data = [
            [
                Paragraph("<b>Total Leads</b>", ParagraphStyle("KpiL", fontName="Helvetica", fontSize=7, textColor=colors.HexColor("#64748B"))),
                Paragraph("<b>Entregabilidad</b>", ParagraphStyle("KpiL", fontName="Helvetica", fontSize=7, textColor=colors.HexColor("#64748B"))),
                Paragraph("<b>Señales Activas</b>", ParagraphStyle("KpiL", fontName="Helvetica", fontSize=7, textColor=colors.HexColor("#64748B"))),
                Paragraph("<b>Garantía</b>", ParagraphStyle("KpiL", fontName="Helvetica", fontSize=7, textColor=colors.HexColor("#64748B"))),
            ],
            [
                Paragraph(f"<b>{len(leads)}</b> Cuentas", ParagraphStyle("KpiV", fontName="Helvetica-Bold", fontSize=11, textColor=colors.HexColor("#0F172A"))),
                Paragraph("<b>100%</b> Socket MX", ParagraphStyle("KpiV", fontName="Helvetica-Bold", fontSize=11, textColor=colors.HexColor("#059669"))),
                Paragraph(f"<b>{contracts_count}</b> Contratos / Exp.", ParagraphStyle("KpiV", fontName="Helvetica-Bold", fontSize=11, textColor=colors.HexColor("#0284C7"))),
                Paragraph("<b>2-for-1</b> Fair Replace", ParagraphStyle("KpiV", fontName="Helvetica-Bold", fontSize=11, textColor=colors.HexColor("#475569"))),
            ]
        ]
        kpi_table = Table(kpi_data, colWidths=[135, 135, 135, 135])
        kpi_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ]))
        elements.append(kpi_table)
        elements.append(Spacer(1, 14))

        # 3. Master Summary Table
        elements.append(Paragraph("📋 Resumen Maestro de Cuentas Calificadas", h2_style))
        summary_headers = [
            Paragraph("<b>#</b>", table_cell_bold),
            Paragraph("<b>Empresa / Razón Social</b>", table_cell_bold),
            Paragraph("<b>Ciudad</b>", table_cell_bold),
            Paragraph("<b>Contacto Clave</b>", table_cell_bold),
            Paragraph("<b>Email Corporativo</b>", table_cell_bold),
            Paragraph("<b>Celular / WhatsApp</b>", table_cell_bold),
            Paragraph("<b>Señal Detectada</b>", table_cell_bold),
        ]
        summary_rows = [summary_headers]

        for idx, lead in enumerate(leads, start=1):
            c_name = lead.get("clean_name") or lead.get("company_name", "")
            c_tax = f"{lead.get('tax_id_type', 'NIT')}: {lead.get('nit', '')}"
            rep = lead.get("decision_maker_name", "")
            title = lead.get("decision_maker_title", "")
            contracts = lead.get("contracts_data", {})
            signal = contracts.get("intent_level") or lead.get("expansion_flag") or "Operación Activa"

            row = [
                Paragraph(str(idx), table_cell_style),
                Paragraph(f"<b>{c_name}</b><br/><font color='#64748B'>{c_tax}</font>", table_cell_style),
                Paragraph(lead.get("city", ""), table_cell_style),
                Paragraph(f"<b>{rep}</b><br/><font color='#64748B'>{title[:25]}</font>", table_cell_style),
                Paragraph(lead.get("email", ""), table_cell_style),
                Paragraph(lead.get("phone", ""), table_cell_style),
                Paragraph(f"<font color='#0284C7'>{signal[:25]}</font>", table_cell_style),
            ]
            summary_rows.append(row)

        summary_table = Table(summary_rows, colWidths=[20, 110, 55, 95, 105, 75, 80])
        summary_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E293B")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        # Apply zebra striping
        for r_idx in range(1, len(summary_rows)):
            bg = colors.HexColor("#F8FAFC") if r_idx % 2 == 1 else colors.white
            summary_table.setStyle(TableStyle([("BACKGROUND", (0, r_idx), (-1, r_idx), bg)]))

        elements.append(summary_table)
        elements.append(Spacer(1, 16))

        # 4. Detailed Profiles & 5-Touch Cadences
        elements.append(Paragraph("🎯 Perfiles Detallados & Cadencias de Contacto Multicanal (5-Touch)", h2_style))
        elements.append(Paragraph("A continuación se presenta la ficha técnica de cada cuenta con sus canales verificados y la estrategia multitoque recomendada:", subtitle_style))
        elements.append(Spacer(1, 10))

        for idx, lead in enumerate(leads, start=1):
            clean_name = lead.get("clean_name") or lead.get("company_name", "")
            city = lead.get("city", "")
            ciiu = lead.get("ciiu")
            activity_desc = getattr(ciiu, "description", str(ciiu or ""))
            sector_macro = getattr(ciiu, "sector_macro", "")
            rep_name = lead.get("decision_maker_name", "")
            rep_title = lead.get("decision_maker_title", "")
            email = lead.get("email", "")
            phone = lead.get("phone", "")
            website = lead.get("website_url", "")
            tax_type = lead.get("tax_id_type", "NIT")
            tax_val = lead.get("nit", "")
            contracts = lead.get("contracts_data", {})

            # Format touches
            touches = campaign_cfg.get("touches", {})
            salutation = f"Hola {lead.get('first_name', 'Líder')}"
            t1 = touches.get("touch1_linkedin_invite", "").format(salutation=salutation, clean_name=clean_name, city=city).strip()
            t2_sub = touches.get("touch2_email_subject", "").format(clean_name=clean_name, city=city).strip()
            t2_body = touches.get("touch2_email_body", "").format(contact_title=rep_title, clean_name=clean_name, city=city).strip()

            # Contract mention inject
            if contracts.get("has_contracts") and contracts.get("total_value_cop", 0) > 0:
                t2_body += f"\n\n[Trigger: Adjudicación de contrato con {contracts.get('top_contract_entity')} por {contracts.get('total_value_display')}]."

            t3_sub = touches.get("touch3_email_subject", "").format(clean_name=clean_name, city=city).strip()
            t3_body = touches.get("touch3_email_body", "").format(contact_title=rep_title, clean_name=clean_name, city=city).strip()
            t4_sub = touches.get("touch4_email_subject", "").format(clean_name=clean_name, city=city).strip()
            t4_body = touches.get("touch4_email_body", "").format(contact_title=rep_title, clean_name=clean_name, city=city).strip()
            t5_sub = touches.get("touch5_email_subject", "").format(clean_name=clean_name, city=city).strip()
            t5_body = touches.get("touch5_email_body", "").format(contact_title=rep_title, clean_name=clean_name, city=city).strip()

            profile_elements = []

            # Account Title Line
            profile_elements.append(Paragraph(f"<b>{idx}. {clean_name}</b> ({city})", h3_style))
            
            # Identity Strip
            id_text = f"<b>{tax_type}:</b> {tax_val} • <b>Actividad:</b> {activity_desc[:40]} ({sector_macro}) • <b>Web:</b> {website[:35]}"
            profile_elements.append(Paragraph(id_text, body_style))

            # Contact Strip
            contact_text = f"<b>Contacto Registrado:</b> <b>{rep_name}</b> ({rep_title}) • <b>Email:</b> <font color='#0284C7'>{email}</font> • <b>Celular:</b> <b>{phone}</b>"
            profile_elements.append(Paragraph(contact_text, body_style))

            # Triggers Strip
            if contracts.get("has_contracts"):
                trig_text = f"<b>Trigger 1 (Contratos Ganados):</b> <font color='#059669'><b>{contracts.get('total_value_display')}</b></font> — {contracts.get('top_contract_entity')} (<i>{contracts.get('intent_level')}</i>)"
                profile_elements.append(Paragraph(trig_text, body_style))

            # Underwriting Strip (Tier 3)
            if tier == 3 and "underwriting" in lead:
                uw = lead["underwriting"]
                uw_text = f"<b>🏛️ Suscripción NIIF:</b> Calificación: <b>{uw.get('underwriting_grade')}</b> | Solvencia: <b>Tier {uw.get('solvency_tier')}</b> | Semáforo Legal: <b>{uw.get('litigation_risk_status')}</b>"
                profile_elements.append(Paragraph(uw_text, body_style))

            profile_elements.append(Spacer(1, 4))

            # Cadence Callout Box
            cadence_rows = [
                [Paragraph("<b>🔹 Touch 1: LinkedIn Note (<300 car.)</b>", cadence_header_style)],
                [Paragraph(t1.replace('\n', ' '), cadence_body_style)],
                [Paragraph(f"<b>🔹 Touch 2: Cold Email (Día 1) — Asunto:</b> <i>{t2_sub}</i>", cadence_header_style)],
                [Paragraph(t2_body.replace('\n', '<br/>'), cadence_body_style)],
                [Paragraph(f"<b>🔹 Touch 3: Seguimiento Operativo (Día 4) — Asunto:</b> <i>{t3_sub}</i>", cadence_header_style)],
                [Paragraph(t3_body.replace('\n', '<br/>'), cadence_body_style)],
                [Paragraph(f"<b>🔹 Touch 4: Prueba Social / VIP (Día 8) — Asunto:</b> <i>{t4_sub}</i>", cadence_header_style)],
                [Paragraph(t4_body.replace('\n', '<br/>'), cadence_body_style)],
                [Paragraph(f"<b>🔹 Touch 5: Cierre / Catálogo (Día 14) — Asunto:</b> <i>{t5_sub}</i>", cadence_header_style)],
                [Paragraph(t5_body.replace('\n', '<br/>'), cadence_body_style)],
            ]
            cadence_table = Table(cadence_rows, colWidths=[540])
            cadence_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor("#E2E8F0")),
                ("LINEBELOW", (0, 2), (-1, 2), 0.5, colors.HexColor("#E2E8F0")),
                ("LINEBELOW", (0, 4), (-1, 4), 0.5, colors.HexColor("#E2E8F0")),
                ("LINEBELOW", (0, 6), (-1, 6), 0.5, colors.HexColor("#E2E8F0")),
                ("LINEBELOW", (0, 8), (-1, 8), 0.5, colors.HexColor("#E2E8F0")),
                ("TOPPADDING", (0, 0), (-1, -1), 2.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]))
            profile_elements.append(cadence_table)
            profile_elements.append(Spacer(1, 10))

            # Keep individual account blocks together on the page when possible
            elements.append(KeepTogether(profile_elements))

        # Build Document
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        doc.build(elements, canvasmaker=NumberedCanvas)
        return output_path

    export_dossier_pdf = generate_dossier_pdf

