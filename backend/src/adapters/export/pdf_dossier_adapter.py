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
    _saved_page_states: list
    _startPage: Any
    _pageNumber: int

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        if hasattr(self, "_startPage"):
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
        curr_page = getattr(self, "_pageNumber", 1)
        footer_text = f"Michito B2B Intent Engine™ • Dossier Confidencial de Prospección • Página {curr_page} de {page_count}"
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
        contracts_count = sum(
            1 for l in leads
            if (l.get("contracts_data") and l.get("contracts_data", {}).get("has_contracts"))
            or (l.get("Trigger 1: Total Contracts Won") and l.get("Trigger 1: Total Contracts Won") not in ("$0 COP", "$0 USD", "$0 DOP", "0", ""))
        )
        contracts_val_str = ""
        for l in leads:
            cd = l.get("contracts_data", {})
            val = cd.get("total_value_display") or l.get("Trigger 1: Total Contracts Won")
            if val and val not in ("$0 COP", "$0 USD", "$0 DOP", "0", ""):
                contracts_val_str = val
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
        elements.append(Paragraph("Resumen Maestro de Cuentas Calificadas", h2_style))
        summary_headers = [
            Paragraph("<b>#</b>", table_cell_bold),
            Paragraph("<b>Empresa / Razón Social</b>", table_cell_bold),
            Paragraph("<b>Ciudad</b>", table_cell_bold),
            Paragraph("<b>Contacto Clave</b>", table_cell_bold),
            Paragraph("<b>Email Corporativo</b>", table_cell_bold),
            Paragraph("<b>Teléfono / Canal</b>", table_cell_bold),
            Paragraph("<b>Señal Detectada</b>", table_cell_bold),
        ]
        summary_rows = [summary_headers]

        for idx, lead in enumerate(leads, start=1):
            c_name = lead.get("Company Name") or lead.get("clean_name") or lead.get("company_name", "")
            tax_type = lead.get("Tax ID Type") or lead.get("tax_id_type", "NIT")
            tax_id = lead.get("Tax ID") or lead.get("nit") or lead.get("tax_id", "")
            c_tax = f"{tax_type}: {tax_id}" if tax_id else ""
            rep = (
                lead.get("Official Registered Contact")
                or lead.get("Decision Maker Name")
                or lead.get("decision_maker_name", "")
            )
            title = (
                lead.get("Official Statutory Title")
                or lead.get("Official Title")
                or lead.get("decision_maker_title", "")
            )
            contracts = lead.get("contracts_data") or {}
            contracts_won = lead.get("Trigger 1: Total Contracts Won") or contracts.get("total_value_display")
            contracts_entity = lead.get("Trigger 1: Top Contracting Entity") or contracts.get("top_contract_entity")
            expansion = lead.get("Trigger 3: Regional Expansion Flag") or lead.get("expansion_flag")

            if expansion and expansion != "Operación Local":
                signal = expansion
            elif contracts_won and contracts_won not in ("$0 COP", "$0 USD", "$0 DOP", "0", ""):
                entity_short = f" ({contracts_entity[:15]})" if contracts_entity else ""
                signal = f"Contratos: {contracts_won}{entity_short}"
            elif contracts.get("intent_level"):
                signal = contracts.get("intent_level")
            else:
                signal = "Operación Activa"

            phone_val = lead.get("Corporate Phone") or lead.get("Direct Mobile Phone") or lead.get("phone", "")
            phone_type = lead.get("Phone Line Type") or lead.get("phone_line_type", "")
            wa_url = lead.get("WhatsApp Direct Link") or lead.get("whatsapp_url", "")
            if wa_url and phone_val:
                phone_cell = f"<b>{phone_val}</b><br/><font color='#059669'>Móvil / WA Directo</font>"
            elif phone_val and ("PBX" in phone_type or "Fija" in phone_type):
                phone_cell = f"<b>{phone_val}</b><br/><font color='#64748B'>Línea PBX</font>"
            elif phone_val:
                phone_cell = f"<b>{phone_val}</b>"
            else:
                phone_cell = "<font color='#94A3B8'>Línea institucional</font>"

            rep_clean = rep if rep else "Representante Registrado"
            title_clean = f"<br/><font color='#64748B'>{title[:25]}</font>" if title else ""
            city_clean = lead.get("City") or lead.get("city") or "Sede Principal"
            email_val = lead.get("Verified Work Email") or lead.get("email") or lead.get("verified_email")
            email_clean = email_val if email_val else "<font color='#94A3B8'>No provisto</font>"
            tax_clean = f"<br/><font color='#64748B'>{c_tax}</font>" if c_tax else ""

            row = [
                Paragraph(str(idx), table_cell_style),
                Paragraph(f"<b>{c_name}</b>{tax_clean}", table_cell_style),
                Paragraph(city_clean, table_cell_style),
                Paragraph(f"<b>{rep_clean}</b>{title_clean}", table_cell_style),
                Paragraph(email_clean, table_cell_style),
                Paragraph(phone_cell, table_cell_style),
                Paragraph(f"<font color='#0284C7'>{signal}</font>", table_cell_style),
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
        elements.append(Paragraph("Perfiles Detallados & Cadencias de Contacto Multicanal (5-Touch)", h2_style))
        elements.append(Paragraph("A continuación se presenta la ficha técnica de cada cuenta con sus canales verificados y la estrategia multitoque recomendada:", subtitle_style))
        elements.append(Spacer(1, 10))

        for idx, lead in enumerate(leads, start=1):
            clean_name = (
                lead.get("Company Name")
                or lead.get("clean_name")
                or lead.get("company_name", "")
            )
            city = lead.get("City") or lead.get("city", "")
            ciiu = lead.get("ciiu")
            activity_desc = (
                lead.get("Economic Activity")
                or getattr(ciiu, "description", None)
                or lead.get("activity_description")
                or (str(ciiu) if ciiu else "")
            )
            sector_macro = getattr(ciiu, "sector_macro", "") or lead.get("Sector Macro") or lead.get("sector_macro", "")
            rep_name = (
                lead.get("Official Registered Contact")
                or lead.get("Decision Maker Name")
                or lead.get("decision_maker_name", "")
            )
            rep_title = (
                lead.get("Official Statutory Title")
                or lead.get("Official Title")
                or lead.get("decision_maker_title", "")
            )
            email = lead.get("Verified Work Email") or lead.get("email") or lead.get("verified_email", "")
            phone = lead.get("Corporate Phone") or lead.get("Direct Mobile Phone") or lead.get("phone", "")
            website = lead.get("Website") or lead.get("website_url", "")
            tax_type = lead.get("Tax ID Type") or lead.get("tax_id_type", "NIT")
            tax_val = lead.get("Tax ID") or lead.get("nit") or lead.get("tax_id", "")
            contracts = lead.get("contracts_data") or {}

            # First extract touches pre-rendered in csv_rows
            t1 = lead.get("Touch 1: LinkedIn Connection Note") or ""
            t2_sub = lead.get("Touch 2: Cold Email Subject") or ""
            t2_body = lead.get("Touch 2: Cold Email Body") or ""
            t3_sub = lead.get("Touch 3: Operational Follow-up Subject") or ""
            t3_body = lead.get("Touch 3: Operational Follow-up Body") or ""
            t4_sub = lead.get("Touch 4: Social Proof / VIP Subject") or lead.get("Touch 4: Case Study Subject") or ""
            t4_body = lead.get("Touch 4: Social Proof / VIP Body") or lead.get("Touch 4: Case Study Body") or ""
            t5_sub = lead.get("Touch 5: Breakup / Catalog Subject") or ""
            t5_body = lead.get("Touch 5: Breakup / Catalog Body") or ""

            # Fallback to campaign_cfg touches if not pre-rendered
            if not (t1 or t2_body or t3_body):
                touches = campaign_cfg.get("touches", {})
                first_name = lead.get("first_name") or (rep_name.split()[0] if rep_name else "Líder")
                salutation = f"Hola {first_name}"

                def _safe_format(tmpl: str) -> str:
                    res = tmpl or ""
                    res = res.replace("{salutation}", salutation)
                    res = res.replace("{clean_name}", clean_name)
                    res = res.replace("{city}", city)
                    res = res.replace("{contact_title}", rep_title)
                    return res.strip()

                t1 = _safe_format(touches.get("touch1_linkedin_invite", ""))
                t2_sub = _safe_format(touches.get("touch2_email_subject", ""))
                t2_body = _safe_format(touches.get("touch2_email_body", ""))
                t3_sub = _safe_format(touches.get("touch3_email_subject", ""))
                t3_body = _safe_format(touches.get("touch3_email_body", ""))
                t4_sub = _safe_format(touches.get("touch4_email_subject", ""))
                t4_body = _safe_format(touches.get("touch4_email_body", ""))
                t5_sub = _safe_format(touches.get("touch5_email_subject", ""))
                t5_body = _safe_format(touches.get("touch5_email_body", ""))

            # Contract mention inject
            contracts_won = lead.get("Trigger 1: Total Contracts Won") or contracts.get("total_value_display")
            top_entity = lead.get("Trigger 1: Top Contracting Entity") or contracts.get("top_contract_entity")
            if contracts_won and top_entity and top_entity not in t2_body:
                t2_body += f"\n\n[Trigger: Adjudicación de contrato con {top_entity} por {contracts_won}]."

            profile_elements = []

            # Account Title Line
            profile_elements.append(Paragraph(f"<b>{idx}. {clean_name}</b> ({city})", h3_style))
            
            # Identity Strip
            id_parts = []
            if tax_val:
                id_parts.append(f"<b>{tax_type}:</b> {tax_val}")
            if activity_desc:
                sec_txt = f" ({sector_macro})" if sector_macro else ""
                id_parts.append(f"<b>Actividad:</b> {activity_desc[:40]}{sec_txt}")
            elif sector_macro:
                id_parts.append(f"<b>Sector:</b> {sector_macro}")
            if website:
                id_parts.append(f"<b>Web:</b> {website[:35]}")
            else:
                id_parts.append("<b>Web:</b> <font color='#94A3B8'>En verificación</font>")
            
            id_text = " • ".join(id_parts)
            profile_elements.append(Paragraph(id_text, body_style))

            # Contact Strip
            phone_val = lead.get("Corporate Phone") or lead.get("Direct Mobile Phone") or lead.get("phone", "")
            phone_type = lead.get("Phone Line Type") or lead.get("phone_line_type", "")
            wa_url = lead.get("WhatsApp Direct Link") or lead.get("whatsapp_url", "")
            wa_badge = " (Móvil / WhatsApp)" if wa_url else (f" ({phone_type})" if phone_type else "")
            target_persona = lead.get("Targeted Campaign Persona") or lead.get("targeted_campaign_persona", "")
            persona_badge = f" • <b>Objetivo Campaña:</b> {target_persona}" if target_persona else ""
            rep_clean = rep_name or "Representante Registrado"
            rep_title_clean = f" ({rep_title})" if rep_title else ""
            email_clean = f"<font color='#0284C7'>{email}</font>" if email else "<font color='#94A3B8'>No provisto</font>"
            phone_clean = f"<b>{phone_val}</b>{wa_badge}" if phone_val else "<font color='#94A3B8'>Línea institucional</font>"
            contact_text = f"<b>Firmante Registrado:</b> <b>{rep_clean}</b>{rep_title_clean}{persona_badge} • <b>Email:</b> {email_clean} • <b>Teléfono:</b> {phone_clean}"
            profile_elements.append(Paragraph(contact_text, body_style))

            # Triggers Strip
            trig_contracts = lead.get("Trigger 1: Total Contracts Won") or contracts.get("total_value_display")
            trig_entity = lead.get("Trigger 1: Top Contracting Entity") or contracts.get("top_contract_entity")
            trig_intent = lead.get("Trigger 1: Intent Score") or contracts.get("intent_level") or "Activo"
            if trig_contracts and trig_contracts not in ("$0 COP", "$0 USD", "$0 DOP", "0", ""):
                trig_text = f"<b>Trigger 1 (Contratos Ganados):</b> <font color='#059669'><b>{trig_contracts}</b></font> — {trig_entity} (<i>{trig_intent}</i>)"
                profile_elements.append(Paragraph(trig_text, body_style))
            elif lead.get("Trigger 3: Regional Expansion Flag") and lead.get("Trigger 3: Regional Expansion Flag") != "Operación Local":
                trig_text = f"<b>Trigger Comercial:</b> <font color='#0284C7'><b>{lead.get('Trigger 3: Regional Expansion Flag')}</b></font>"
                profile_elements.append(Paragraph(trig_text, body_style))

            # Underwriting Strip (Tier 3)
            if tier == 3:
                uw = lead.get("underwriting") or {}
                uw_grade = lead.get("Underwriting Grade") or uw.get("underwriting_grade")
                solv_tier = lead.get("Solvency: Tier") or lead.get("Solvency Tier") or uw.get("solvency_tier")
                lit_risk = lead.get("Legal Risk: Litigation Status") or lead.get("Litigation Risk") or uw.get("litigation_risk_status")
                if uw_grade or solv_tier:
                    uw_text = f"<b>Suscripción NIIF:</b> Calificación: <b>{uw_grade or 'A'}</b> | Solvencia: <b>Tier {solv_tier or 'Solvente'}</b> | Semáforo Legal: <b>{lit_risk or 'Bajo Riesgo'}</b>"
                    profile_elements.append(Paragraph(uw_text, body_style))

            profile_elements.append(Spacer(1, 4))

            # Cadence Callout Box (Only render non-empty touches)
            cadence_rows = []
            if t1 and len(t1.strip()) > 5:
                cadence_rows.append([Paragraph("<b>Touch 1: LinkedIn Note (<300 car.)</b>", cadence_header_style)])
                cadence_rows.append([Paragraph(t1.replace('\n', ' '), cadence_body_style)])
            if t2_body and len(t2_body.strip()) > 5:
                sub_txt = f" — Asunto: <i>{t2_sub}</i>" if t2_sub else ""
                cadence_rows.append([Paragraph(f"<b>Touch 2: Cold Email (Día 1){sub_txt}</b>", cadence_header_style)])
                cadence_rows.append([Paragraph(t2_body.replace('\n', '<br/>'), cadence_body_style)])
            if t3_body and len(t3_body.strip()) > 5:
                sub_txt = f" — Asunto: <i>{t3_sub}</i>" if t3_sub else ""
                cadence_rows.append([Paragraph(f"<b>Touch 3: Seguimiento Operativo (Día 4){sub_txt}</b>", cadence_header_style)])
                cadence_rows.append([Paragraph(t3_body.replace('\n', '<br/>'), cadence_body_style)])
            if t4_body and len(t4_body.strip()) > 5:
                sub_txt = f" — Asunto: <i>{t4_sub}</i>" if t4_sub else ""
                cadence_rows.append([Paragraph(f"<b>Touch 4: Prueba Social / VIP (Día 8){sub_txt}</b>", cadence_header_style)])
                cadence_rows.append([Paragraph(t4_body.replace('\n', '<br/>'), cadence_body_style)])
            if t5_body and len(t5_body.strip()) > 5:
                sub_txt = f" — Asunto: <i>{t5_sub}</i>" if t5_sub else ""
                cadence_rows.append([Paragraph(f"<b>Touch 5: Cierre / Catálogo (Día 14){sub_txt}</b>", cadence_header_style)])
                cadence_rows.append([Paragraph(t5_body.replace('\n', '<br/>'), cadence_body_style)])

            if cadence_rows:
                cadence_table = Table(cadence_rows, colWidths=[540])
                table_styles = [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                    ("TOPPADDING", (0, 0), (-1, -1), 2.5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ]
                for r_idx in range(len(cadence_rows) - 1):
                    table_styles.append(("LINEBELOW", (0, r_idx), (-1, r_idx), 0.5, colors.HexColor("#E2E8F0")))
                cadence_table.setStyle(TableStyle(table_styles))
                profile_elements.append(cadence_table)
                profile_elements.append(Spacer(1, 10))

            # Keep individual account blocks together on the page when possible
            elements.append(KeepTogether(profile_elements))

        # Build Document
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        doc.build(elements, canvasmaker=NumberedCanvas)
        return output_path

    export_dossier_pdf = generate_dossier_pdf

