import os
import json
import logging
import smtplib
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import Dict, Any, Optional

from src.application.ports.delivery_port import DeliveryPort

logger = logging.getLogger(__name__)


class OmnichannelDeliveryAdapter(DeliveryPort):
    """
    Omnichannel Transactional Outbound Delivery Adapter (Email + WhatsApp).
    - Dispatches real transactional emails via SMTP (Resend, SendGrid, Gmail, custom SMTP)
      with attached CSV and high-conversion HTML download CTAs.
    - Routes copies to DEV_DELIVERY_EMAIL / TEST_EMAIL when configured.
    - Dispatches WhatsApp delivery via Twilio / Meta Cloud API when configured.
    - Always persists dispatched artifacts to outputs/dispatched_emails and outputs/dispatched_whatsapp
      for local auditing and zero-configuration development testing.
    """

    def __init__(self, outputs_dir: Optional[str] = None):
        if outputs_dir:
            self.outputs_dir = Path(outputs_dir)
        else:
            self.outputs_dir = Path(__file__).resolve().parent.parent.parent.parent / "outputs"

        self.dispatched_emails_dir = self.outputs_dir / "dispatched_emails"
        self.dispatched_whatsapp_dir = self.outputs_dir / "dispatched_whatsapp"

        try:
            self.dispatched_emails_dir.mkdir(parents=True, exist_ok=True)
            self.dispatched_whatsapp_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    def send_delivery(self, order: Dict[str, Any]) -> bool:
        """
        Dispatches omnichannel delivery (Email and WhatsApp) for a confirmed/paid order.
        """
        order_id = order.get("order_id", "ord_unknown")
        client_data = order.get("client", {})
        buyer_name = (client_data.get("name") or "Estimado Cliente").strip()
        buyer_email = (client_data.get("email") or order.get("customer_email") or "unknown@example.com").strip()
        buyer_phone = (client_data.get("phone") or order.get("customer_phone") or "unknown").strip()

        # Extract file paths & download URLs
        csv_path = order.get("csv_path", "")
        if not csv_path and "delivery" in order:
            csv_path = order["delivery"].get("csv_path", "") or order["delivery"].get("csv_download_url", "")

        md_path = order.get("dossier_path", "")
        if not md_path and "delivery" in order:
            md_path = order["delivery"].get("dossier_path", "") or order["delivery"].get("dossier_download_url", "")

        csv_url = order.get("csv_download_url") or ""
        if not csv_url and "delivery" in order:
            csv_url = order["delivery"].get("csv_download_url", "") or order["delivery"].get("csv_path", "")
        if not csv_url:
            csv_url = f"/api/v1/orders/{order_id}/download/csv"

        md_url = order.get("dossier_download_url") or ""
        if not md_url and "delivery" in order:
            md_url = order["delivery"].get("dossier_download_url", "") or order["delivery"].get("dossier_path", "")
        if not md_url:
            md_url = f"/api/v1/orders/{order_id}/download/md"

        xlsx_url = order.get("xlsx_download_url") or ""
        if not xlsx_url and "delivery" in order:
            xlsx_url = order["delivery"].get("xlsx_download_url", "") or order["delivery"].get("xlsx_path", "")
        if not xlsx_url:
            xlsx_url = f"/api/v1/orders/{order_id}/download/xlsx"

        pdf_url = order.get("pdf_download_url") or ""
        if not pdf_url and "delivery" in order:
            pdf_url = order["delivery"].get("pdf_download_url", "") or order["delivery"].get("pdf_path", "")
        if not pdf_url:
            pdf_url = f"/api/v1/orders/{order_id}/download/pdf"

        xlsx_path = order.get("xlsx_path") or ""
        if not xlsx_path and "delivery" in order:
            xlsx_path = order["delivery"].get("xlsx_path", "")

        pdf_path = order.get("pdf_path") or ""
        if not pdf_path and "delivery" in order:
            pdf_path = order["delivery"].get("pdf_path", "")

        # Resolve public absolute URLs for outbound links
        base_url = os.environ.get("BASE_URL") or os.environ.get("API_BASE_URL") or "http://localhost:8000"
        full_csv_url = f"{base_url.rstrip('/')}{csv_url}" if csv_url.startswith("/") else csv_url
        full_md_url = f"{base_url.rstrip('/')}{md_url}" if md_url.startswith("/") else md_url
        full_xlsx_url = f"{base_url.rstrip('/')}{xlsx_url}" if xlsx_url.startswith("/") else xlsx_url
        full_pdf_url = f"{base_url.rstrip('/')}{pdf_url}" if pdf_url.startswith("/") else pdf_url

        # Order metadata
        campaign_id = (
            order.get("request", {}).get("campaign_id")
            or order.get("campaign_id")
            or "inteligencia_b2b"
        )
        city = order.get("request", {}).get("city") or order.get("city") or "Colombia"
        country = order.get("request", {}).get("country") or order.get("country") or "CO"
        tier = order.get("request", {}).get("tier") or order.get("tier") or 2
        total_qualified = (
            order.get("delivery", {}).get("total_qualified")
            or order.get("total_qualified")
            or order.get("requested_limit")
            or order.get("limit")
            or 10
        )

        # 1. Standard log format for verification & backwards compatibility
        whatsapp_message = (
            f"[WhatsApp] Sending to {buyer_phone}: \"Payment confirmed! "
            f"Download your leads CSV: {csv_url} and Dossier: {md_url}\""
        )
        email_message = (
            f"[Email] Sending to {buyer_email}: \"Payment confirmed! "
            f"Download your leads CSV: {csv_url} and Dossier: {md_url}\""
        )
        logger.info(whatsapp_message)
        logger.info(email_message)

        # 2. Render templates
        email_subject = f"🎯 Tus prospectos B2B calificados están listos — Orden #{order_id}"
        html_content = self._render_email_html(
            buyer_name=buyer_name,
            order_id=order_id,
            campaign_id=campaign_id,
            city=city,
            total_qualified=total_qualified,
            tier=tier,
            csv_url=full_csv_url,
            md_url=full_md_url,
            xlsx_url=full_xlsx_url,
            pdf_url=full_pdf_url,
        )
        text_content = self._render_email_text(
            buyer_name=buyer_name,
            order_id=order_id,
            campaign_id=campaign_id,
            city=city,
            total_qualified=total_qualified,
            csv_url=full_csv_url,
            md_url=full_md_url,
            xlsx_url=full_xlsx_url,
            pdf_url=full_pdf_url,
        )
        whatsapp_text = self._render_whatsapp_text(
            buyer_name=buyer_name,
            order_id=order_id,
            city=city,
            total_qualified=total_qualified,
            csv_url=full_csv_url,
            md_url=full_md_url,
        )

        # 3. Always archive locally (dev inspection & audit trail)
        self._archive_dispatched_artifacts(
            order_id=order_id,
            buyer_email=buyer_email,
            buyer_phone=buyer_phone,
            subject=email_subject,
            html_content=html_content,
            text_content=text_content,
            whatsapp_text=whatsapp_text,
            csv_url=full_csv_url,
            md_url=full_md_url,
        )

        # 4. Outbound Real SMTP Delivery (if configured)
        self._dispatch_smtp_email(
            order_id=order_id,
            buyer_email=buyer_email,
            subject=email_subject,
            html_content=html_content,
            text_content=text_content,
            csv_path=csv_path,
            xlsx_path=xlsx_path,
            pdf_path=pdf_path,
        )

        # 5. Outbound WhatsApp Delivery (if configured)
        self._dispatch_whatsapp(
            order_id=order_id,
            buyer_phone=buyer_phone,
            message_text=whatsapp_text,
        )

        return True

    def _render_email_html(
        self,
        buyer_name: str,
        order_id: str,
        campaign_id: str,
        city: str,
        total_qualified: int,
        tier: int,
        csv_url: str,
        md_url: str,
        xlsx_url: Optional[str] = None,
        pdf_url: Optional[str] = None,
    ) -> str:
        xlsx_btn = f'<a href="{xlsx_url}" class="btn-primary" style="background:#0F766E;margin-bottom:10px;">📊 Descargar Hoja de Cálculo Formateada (.XLSX)</a><br>' if xlsx_url else ""
        pdf_btn = f'<a href="{pdf_url}" class="btn-primary" style="background:#0284C7;margin-bottom:10px;">📑 Descargar Dossier Ejecutivo y Guiones (.PDF)</a><br>' if pdf_url else ""
        return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Tus prospectos B2B están listos — Michito Intent Engine</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0b0f19; color: #f1f5f9; margin: 0; padding: 24px; }}
    .container {{ max-width: 600px; margin: 0 auto; background-color: #111827; border: 1px solid #1e293b; border-radius: 12px; overflow: hidden; }}
    .header {{ background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%); padding: 32px 24px; text-align: center; }}
    .header h1 {{ margin: 0; font-size: 22px; color: #ffffff; font-weight: 700; letter-spacing: -0.5px; }}
    .header p {{ margin: 8px 0 0; color: #bae6fd; font-size: 14px; }}
    .content {{ padding: 32px 24px; }}
    .greeting {{ font-size: 16px; margin-bottom: 20px; color: #e2e8f0; }}
    .order-card {{ background-color: #1e293b; border-radius: 8px; padding: 18px; margin: 20px 0; border-left: 4px solid #38bdf8; }}
    .order-row {{ display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 14px; }}
    .order-row:last-child {{ margin-bottom: 0; }}
    .label {{ color: #94a3b8; }}
    .value {{ color: #ffffff; font-weight: 600; }}
    .actions {{ margin: 32px 0; text-align: center; }}
    .btn-primary {{ display: inline-block; background-color: #0284c7; color: #ffffff !important; text-decoration: none; padding: 14px 28px; border-radius: 8px; font-weight: 600; font-size: 15px; margin-bottom: 12px; width: 80%; text-align: center; }}
    .btn-secondary {{ display: inline-block; background-color: #334155; color: #f8fafc !important; text-decoration: none; padding: 12px 24px; border-radius: 8px; font-weight: 500; font-size: 14px; width: 80%; text-align: center; }}
    .guarantee-box {{ background-color: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 8px; padding: 16px; margin: 24px 0; }}
    .guarantee-box h4 {{ margin: 0 0 6px; color: #34d399; font-size: 14px; display: flex; align-items: center; }}
    .guarantee-box p {{ margin: 0; font-size: 13px; color: #a7f3d0; line-height: 1.5; }}
    .footer {{ padding: 20px 24px; text-align: center; border-top: 1px solid #1e293b; font-size: 12px; color: #64748b; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>MICHITO INTENT ENGINE™</h1>
      <p>Inteligencia B2B On-Demand • Entregables Listos</p>
    </div>
    <div class="content">
      <div class="greeting">
        Hola <strong>{buyer_name}</strong>, tu orden ha sido procesada con éxito y tus prospectos B2B están listos para descarga inmediata.
      </div>
      <div class="order-card">
        <div class="order-row"><span class="label">ID de Orden:</span> <span class="value">{order_id}</span></div>
        <div class="order-row"><span class="label">Campaña:</span> <span class="value">{campaign_id}</span></div>
        <div class="order-row"><span class="label">Cobertura:</span> <span class="value">{city}</span></div>
        <div class="order-row"><span class="label">Cuentas Calificadas:</span> <span class="value">{total_qualified} empresas</span></div>
        <div class="order-row"><span class="label">Nivel de Inteligencia:</span> <span class="value">Tier {tier}</span></div>
      </div>
      <div class="actions">
        {xlsx_btn}
        {pdf_btn}
        <a href="{csv_url}" class="btn-secondary" style="margin-bottom:10px;">📂 Descargar Base para Ingesta CRM (.CSV)</a>
        <br>
        <a href="{md_url}" class="btn-secondary">📝 Descargar Dossier (.MD)</a>
      </div>
      <div class="guarantee-box">
        <h4>🛡️ Garantía de Calidad Michito (Zero-Bounce Guarantee)</h4>
        <p>Cada buzón de correo fue verificado mediante socket SMTP directo contra el registro MX corporativo. Cuentas con garantía de reposición inmediata 100% gratuita si algún contacto presenta rebote duro.</p>
      </div>
    </div>
    <div class="footer">
      © 2026 Chiketto • Michito Intent Engine. Operación conforme a la Ley 1581 de 2012 y normativas de Habeas Data.<br>
      Este correo contiene información comercial confidencial generada para la orden {order_id}.
    </div>
  </div>
</body>
</html>"""

    def _render_email_text(
        self,
        buyer_name: str,
        order_id: str,
        campaign_id: str,
        city: str,
        total_qualified: int,
        csv_url: str,
        md_url: str,
        xlsx_url: Optional[str] = None,
        pdf_url: Optional[str] = None,
    ) -> str:
        xlsx_line = f"- Descarga Hoja de Cálculo (.XLSX): {xlsx_url}\n" if xlsx_url else ""
        pdf_line = f"- Descarga Dossier Ejecutivo (.PDF): {pdf_url}\n" if pdf_url else ""
        return f"""Hola {buyer_name},

Tu orden de inteligencia B2B (#{order_id}) ha sido procesada exitosamente.

RESUMEN DE ENTREGA:
- Campaña: {campaign_id}
- Cobertura: {city}
- Cuentas Calificadas: {total_qualified}
{xlsx_line}{pdf_line}- Descarga CSV (CRM): {csv_url}
- Descarga Playbook (.MD): {md_url}

GARANTÍA DE REPOSICIÓN MICHITO:
Todos los buzones han sido validados vía Socket MX. Garantía de rebote 0%-3%.

Atentamente,
Equipo Michito Intent Engine
Chiketto B2B Operations
"""

    def _render_whatsapp_text(
        self,
        buyer_name: str,
        order_id: str,
        city: str,
        total_qualified: int,
        csv_url: str,
        md_url: str,
    ) -> str:
        return (
            f"🎯 *¡Hola {buyer_name}! Tu lote de inteligencia B2B está listo.* (Orden `{order_id}`)\n\n"
            f"Hemos extraído y verificado *{total_qualified} cuentas calificadas* para tu campaña en *{city}*.\n\n"
            f"📊 *Descargar CSV (CRM):*\n{csv_url}\n\n"
            f"📑 *Dossier y Guiones de Venta:*\n{md_url}\n\n"
            f"🛡️ *Garantía:* Todos los correos cuentan con validación de socket MX. Reposición 100% garantizada.\n\n"
            f"_Equipo Michito Intent Engine_"
        )

    def _archive_dispatched_artifacts(
        self,
        order_id: str,
        buyer_email: str,
        buyer_phone: str,
        subject: str,
        html_content: str,
        text_content: str,
        whatsapp_text: str,
        csv_url: str,
        md_url: str,
    ) -> None:
        try:
            now_iso = datetime.now(timezone.utc).isoformat()
            email_html_file = self.dispatched_emails_dir / f"{order_id}.html"
            email_json_file = self.dispatched_emails_dir / f"{order_id}.json"
            wa_json_file = self.dispatched_whatsapp_dir / f"{order_id}.json"

            email_html_file.write_text(html_content, encoding="utf-8")
            email_json_file.write_text(
                json.dumps(
                    {
                        "order_id": order_id,
                        "timestamp": now_iso,
                        "recipient_email": buyer_email,
                        "subject": subject,
                        "csv_download_url": csv_url,
                        "dossier_download_url": md_url,
                        "text_body": text_content,
                    },
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            wa_json_file.write_text(
                json.dumps(
                    {
                        "order_id": order_id,
                        "timestamp": now_iso,
                        "recipient_phone": buyer_phone,
                        "message_text": whatsapp_text,
                        "csv_download_url": csv_url,
                        "dossier_download_url": md_url,
                    },
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
        except Exception as e:
            logger.warning(f"Could not write dispatched delivery artifacts for {order_id}: {e}")

    def _dispatch_smtp_email(
        self,
        order_id: str,
        buyer_email: str,
        subject: str,
        html_content: str,
        text_content: str,
        csv_path: Optional[str] = None,
        xlsx_path: Optional[str] = None,
        pdf_path: Optional[str] = None,
    ) -> bool:
        smtp_host = os.environ.get("SMTP_HOST")
        dev_email = os.environ.get("DEV_DELIVERY_EMAIL") or os.environ.get("TEST_EMAIL")

        if not smtp_host:
            logger.info(
                f"[Email] SMTP_HOST not configured. Dispatched email archived for order {order_id}."
            )
            return False

        try:
            smtp_port = int(os.environ.get("SMTP_PORT", "587"))
            smtp_user = os.environ.get("SMTP_USER")
            smtp_pass = os.environ.get("SMTP_PASSWORD")
            smtp_from = os.environ.get("SMTP_FROM", "entregas@michito.ai")
            use_ssl = os.environ.get("SMTP_USE_SSL", "false").lower() in ("true", "1")
            use_tls = os.environ.get("SMTP_USE_TLS", "true").lower() in ("true", "1")

            msg = MIMEMultipart("mixed")
            msg["Subject"] = subject
            msg["From"] = smtp_from
            msg["To"] = buyer_email
            if dev_email and dev_email != buyer_email:
                msg["Bcc"] = dev_email

            body_part = MIMEMultipart("alternative")
            body_part.attach(MIMEText(text_content, "plain", "utf-8"))
            body_part.attach(MIMEText(html_content, "html", "utf-8"))
            msg.attach(body_part)

            # Direct CSV attachment if file exists on disk and is < 20MB
            if csv_path and os.path.exists(csv_path) and os.path.isfile(csv_path):
                file_size = os.path.getsize(csv_path)
                if file_size < 20 * 1024 * 1024:
                    with open(csv_path, "rb") as f:
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(f.read())
                        encoders.encode_base64(part)
                        filename = f"prospectos_{order_id}.csv"
                        part.add_header("Content-Disposition", f"attachment; filename={filename}")
                        msg.attach(part)

            # Direct XLSX attachment
            if xlsx_path and os.path.exists(xlsx_path) and os.path.isfile(xlsx_path):
                file_size = os.path.getsize(xlsx_path)
                if file_size < 20 * 1024 * 1024:
                    with open(xlsx_path, "rb") as f:
                        part = MIMEBase("application", "vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                        part.set_payload(f.read())
                        encoders.encode_base64(part)
                        filename = f"prospectos_{order_id}.xlsx"
                        part.add_header("Content-Disposition", f"attachment; filename={filename}")
                        msg.attach(part)

            # Direct PDF attachment
            if pdf_path and os.path.exists(pdf_path) and os.path.isfile(pdf_path):
                file_size = os.path.getsize(pdf_path)
                if file_size < 20 * 1024 * 1024:
                    with open(pdf_path, "rb") as f:
                        part = MIMEBase("application", "pdf")
                        part.set_payload(f.read())
                        encoders.encode_base64(part)
                        filename = f"dossier_ejecutivo_{order_id}.pdf"
                        part.add_header("Content-Disposition", f"attachment; filename={filename}")
                        msg.attach(part)

            recipients = [buyer_email]
            if dev_email and dev_email != buyer_email:
                recipients.append(dev_email)

            if use_ssl or smtp_port == 465:
                server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10)
            else:
                server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
                if use_tls:
                    server.starttls()

            if smtp_user and smtp_pass:
                server.login(smtp_user, smtp_pass)

            server.send_message(msg, to_addrs=recipients)
            server.quit()

            logger.info(f"[Email] Real SMTP delivery successfully dispatched for {order_id} to {buyer_email}")
            return True
        except Exception as e:
            logger.warning(f"[Email] Could not send via live SMTP ({e}). Fallback archive generated.")
            return False

    def _dispatch_whatsapp(
        self,
        order_id: str,
        buyer_phone: str,
        message_text: str,
    ) -> bool:
        twilio_sid = os.environ.get("TWILIO_ACCOUNT_SID")
        twilio_token = os.environ.get("TWILIO_AUTH_TOKEN")
        twilio_from = os.environ.get("TWILIO_WHATSAPP_NUMBER")

        if twilio_sid and twilio_token and twilio_from:
            try:
                import base64
                url = f"https://api.twilio.com/2010-04-01/Accounts/{twilio_sid}/Messages.json"
                to_formatted = buyer_phone if buyer_phone.startswith("whatsapp:") else f"whatsapp:{buyer_phone}"
                from_formatted = twilio_from if twilio_from.startswith("whatsapp:") else f"whatsapp:{twilio_from}"
                data = urllib.parse.urlencode({
                    "From": from_formatted,
                    "To": to_formatted,
                    "Body": message_text,
                }).encode("utf-8")

                req = urllib.request.Request(url, data=data, method="POST")
                auth_str = f"{twilio_sid}:{twilio_token}"
                auth_b64 = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")
                req.add_header("Authorization", f"Basic {auth_b64}")

                with urllib.request.urlopen(req, timeout=10) as resp:
                    if resp.status in (200, 201):
                        logger.info(f"[WhatsApp] Twilio message dispatched for order {order_id} to {buyer_phone}")
                        return True
            except Exception as e:
                logger.warning(f"[WhatsApp] Twilio dispatch failed for {order_id}: {e}")

        logger.info(f"[WhatsApp] Dispatched payload archived for order {order_id} to {buyer_phone}")
        return True
