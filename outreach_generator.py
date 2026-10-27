"""
Outreach Campaign Generator for Colombian B2B Accounts
Generates the complete 5-touch sales outreach cadence:
- Touch 1 (Day 1): LinkedIn Connection Invite (<300 chars)
- Touch 2 (Day 1): Executive Cold Email (Problem & Value Hook)
- Touch 3 (Day 4): Operational / Risk / Efficiency Follow-up
- Touch 4 (Day 8): Social Proof / Financial Case Study
- Touch 5 (Day 14): Soft Breakup & One-Pager Leave-Behind

Supports both dynamic YAML Campaign Profiles and legacy hardcoded profiles.
"""

import urllib.parse
from typing import Dict, Any, List, Optional
try:
    from .campaign_loader import load_campaign, format_touch, clean_company_name
except ImportError:
    from campaign_loader import load_campaign, format_touch, clean_company_name

TARGET_ROLES_DEFAULT = [
    "Gerente General",
    "Director de Operaciones",
    "COO",
    "Director Financiero",
    "CFO",
    "Director de Infraestructura"
]

def generate_linkedin_xray_url(
    company_name: str,
    target_roles: Optional[List[str]] = None,
    product: Optional[str] = None,
    city: str = "Colombia"
) -> str:
    """
    Builds a direct Google X-Ray search URL that bypasses LinkedIn login limits
    and finds the exact decision-maker at the specified Colombian company.
    """
    roles = target_roles
    if not roles:
        if product == "chiketto":
            roles = ["Contador General", "Director Financiero", "Gerente Financiero", "CFO", "Jefe de Facturación"]
        elif product == "hebi":
            roles = ["Director Financiero", "CFO", "Gerente Financiero", "Gerente de Operaciones", "Jefe de Cartera"]
        elif product in ("warehouse", "warehouse_aburra_norte"):
            roles = ["Gerente de Operaciones", "Director de Cadena de Suministro", "Gerente de Logística", "COO", "CFO"]
        else:
            roles = TARGET_ROLES_DEFAULT

    roles_str = " OR ".join([f'"{r}"' for r in roles[:4]])
    clean_name = clean_company_name(company_name)
    query = f'site:co.linkedin.com/in/ "{clean_name}" ({roles_str}) "{city}"'
    encoded_query = urllib.parse.quote(query)
    return f"https://www.google.com/search?q={encoded_query}"

def generate_full_campaign(
    company_name: str,
    sector: str,
    city: str,
    segment: str,
    contact_name: Optional[str] = None,
    contact_title: Optional[str] = None,
    product: str = "hebi",
    campaign_config: Optional[Dict[str, Any]] = None
) -> Dict[str, str]:
    """
    Crafts the entire 5-touch multi-channel cadence tailored for the account.
    If campaign_config is passed (or product matches a YAML campaign), uses the dynamic campaign touches.
    """
    # 1. Load campaign config if not passed
    cfg = campaign_config
    if not cfg:
        try:
            cfg = load_campaign(product)
        except Exception:
            cfg = None

    clean_name = clean_company_name(company_name)
    salutation = f"Hola {contact_name}" if contact_name and contact_name not in ("Director(a)", "Gerente", "") else "Hola"

    # Context dict for touch interpolation
    ctx = {
        "company_name": company_name,
        "clean_name": clean_name,
        "contact_name": contact_name,
        "contact_title": contact_title or (cfg.get("target", {}).get("roles", ["Director(a)"])[0] if cfg else "Director(a)"),
        "city": city,
        "sector": sector,
        "salutation": salutation
    }

    # 2. If dynamic campaign config is active, use its touches
    if cfg and cfg.get("touches"):
        touches = cfg["touches"]
        t1 = format_touch(touches.get("touch1_linkedin_invite", ""), ctx)
        t2_sub = format_touch(touches.get("touch2_email_subject", ""), ctx)
        t2_body = format_touch(touches.get("touch2_email_body", ""), ctx)
        t3_sub = format_touch(touches.get("touch3_email_subject", ""), ctx)
        t3_body = format_touch(touches.get("touch3_email_body", ""), ctx)
        t4_sub = format_touch(touches.get("touch4_email_subject", ""), ctx)
        t4_body = format_touch(touches.get("touch4_email_body", ""), ctx)
        t5_sub = format_touch(touches.get("touch5_email_subject", ""), ctx)
        t5_body = format_touch(touches.get("touch5_email_body", ""), ctx)

        recommended_angle = cfg.get("angles", {}).get("recommended", cfg.get("name", "Propuesta de Valor Comercial"))

        # Safe character bound for LinkedIn connection message (max 300 chars)
        if len(t1) > 298:
            cut = t1[:298]
            last_space = cut.rfind(" ")
            t1 = cut[:last_space] if last_space > 200 else cut

        return {
            "recommended_angle": recommended_angle,
            "touch1_linkedin_invite": t1,
            "touch2_email_subject": t2_sub,
            "touch2_email_body": t2_body,
            "touch3_email_subject": t3_sub,
            "touch3_email_body": t3_body,
            "touch4_email_subject": t4_sub,
            "touch4_email_body": t4_body,
            "touch5_email_subject": t5_sub,
            "touch5_email_body": t5_body,
        }

    # 3. Fallback to hardcoded Hebi / Chiketto
    if product == "chiketto":
        touch1 = (
            f"{salutation}, vi que lideras operaciones en {clean_name} en {city}. "
            f"En Chiketto automatizamos la emisión de facturación electrónica recurrente hacia la DIAN "
            f"sin fricción en portales ni costos desmedidos por documento. ¿Abierto a conectar?"
        )
        touch2_subject = f"Facturación electrónica DIAN automatizada para {clean_name}"
        touch2_body = (
            f"{salutation},\n\n"
            f"Te contacto porque en {clean_name} emiten facturación recurrente en Colombia. "
            f"Con Chiketto simplificamos la integración directa con la DIAN y pasarelas de pago como Wompi "
            f"para que la emisión de facturas mensuales y el recaudo ocurran automáticamente sin digitar manualmente en el portal gratuito.\n\n"
            f"¿Tendrías 15 minutos esta semana para mostrarte el flujo en vivo?"
        )
        touch3_subject = f"Re: {clean_name} — Reducción de costos de emisión y rechazos DIAN"
        touch3_body = (
            f"{salutation},\n\n"
            f"Quería dar seguimiento breve a mi mensaje anterior. Muchas empresas en {city} pierden horas "
            f"cada fin de mes corrigiendo CUFEs rechazados y cuadrando retenciones en la fuente.\n\n"
            f"Chiketto valida la estructura XML antes del envío a la DIAN y emite los documentos en menos de 2 segundos.\n\n"
            f"¿Te interesaría una demostración rápida de 10 minutos este jueves?"
        )
        touch4_subject = f"Automatización de facturación B2B recurrente sin costo por documento"
        touch4_body = (
            f"{salutation},\n\n"
            f"Quería compartirte que clientes en Colombia han reducido su tiempo de emisión mensual de 3 días a solo 15 minutos, "
            f"conciliando recaudos contra Odoo y Excel de forma nativa.\n\n"
            f"¿Cuadramos un café virtual de 15 minutos para ver si aplica para {clean_name}?"
        )
        touch5_subject = f"Ficha técnica Chiketto para {clean_name} (Último intento)"
        touch5_body = (
            f"{salutation},\n\n"
            f"Entiendo que deben estar enfocados en prioridades operativas de cierre de mes. "
            f"No insistiré más por este canal. Te dejo el acceso a nuestra plataforma en https://www.hebisend.com "
            f"en caso de que más adelante quieran automatizar su emisión DIAN.\n\n"
            f"¡Muchos éxitos en la gestión de {clean_name}!"
        )
        recommended_angle = "Automatización de Facturación Electrónica DIAN y Conciliación Recurrente"
    else:
        # Standard Hebi Triad
        touch1 = (
            f"{salutation}, un gusto saludarte. En Hebi ayudamos a empresas en Colombia como {clean_name} "
            f"a acelerar su recaudo B2B (DSO -14 días) bajo Ley 2300 y auditar a todos sus proveedores "
            f"cada 365 días para proteger la deducibilidad tributaria ante la DIAN. ¿Conectamos?"
        )
        recommended_angle = "Aceleración de Cartera B2B Ley 2300 y Auditoría DIAN 365 días"
        touch2_subject = f"Optimización de cartera B2B (Ley 2300) y debida diligencia en {clean_name}"
        touch2_body = (
            f"Estimado(a) Director(a),\n\n"
            f"Te contacto desde Hebi Technologies en Colombia. Sabemos que en empresas como {clean_name}, "
            f"gestionar cartera empresarial y coordinar la documentación obligatoria de contratistas suele demandar decenas de horas al mes.\n\n"
            f"En Hebi automatizamos toda la Tríada Operativa (Cartera, Debida Diligencia y Extintores QR).\n\n"
            f"¿Tendrías 15 minutos esta semana para una demostración ejecutiva sin compromiso?"
        )
        touch3_subject = f"Re: {clean_name} — Cálculo de intereses de mora y multas SIC (Ley 2300)"
        touch3_body = f"Estimado(a) Director(a),\n\nDando alcance a mi correo anterior..."
        touch4_subject = f"Caso de éxito: Cómo Tinkko redujo 14 días de DSO en 11 sedes corporativas"
        touch4_body = f"Estimado(a) Director(a),\n\nPara ilustrar el impacto real..."
        touch5_subject = f"Ficha ejecutiva Hebi para {clean_name} (Último contacto)"
        touch5_body = f"Estimado(a) Director(a),\n\nEntiendo que en este momento..."

    return {
        "recommended_angle": recommended_angle,
        "touch1_linkedin_invite": touch1[:298],
        "touch2_email_subject": touch2_subject,
        "touch2_email_body": touch2_body,
        "touch3_email_subject": touch3_subject,
        "touch3_email_body": touch3_body,
        "touch4_email_subject": touch4_subject,
        "touch4_email_body": touch4_body,
        "touch5_email_subject": touch5_subject,
        "touch5_email_body": touch5_body,
    }
