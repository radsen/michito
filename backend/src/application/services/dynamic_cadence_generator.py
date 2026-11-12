"""
Dynamic Omnichannel Cadence Generator.
Generates tailored 5-touch B2B outbound sales cadences (LinkedIn + Executive Email)
for any commercial offer across any economic sector in Latin America.
"""

from typing import Dict, Any, List, Optional
import re


def generate_dynamic_touches(
    offer_description: Optional[str] = None,
    sectors: Optional[List[str]] = None,
    roles: Optional[List[str]] = None,
) -> Dict[str, str]:
    """
    Synthesizes a 5-touch cadence tailored to the user's specific commercial offer.
    Uses placeholders {salutation}, {clean_name}, {city}, and {contact_title}
    for per-lead interpolation.
    """
    clean_offer = (offer_description or "").strip()
    if not clean_offer:
        clean_offer = "soluciones estratégicas orientadas a optimizar costos operativos y acelerar la productividad comercial"

    # Truncate or summarize offer for conversational flow if too verbose
    pitch_core = clean_offer
    if len(pitch_core) > 280:
        pitch_core = pitch_core[:277].rstrip() + "..."

    # Extract sector context if provided
    sector_label = "su sector"
    if sectors and len(sectors) > 0:
        s0 = sectors[0].replace("_", " ").lower()
        if "agro" in s0 or "food" in s0 or "alimento" in s0:
            sector_label = "la industria agroalimentaria y de consumo"
        elif "construc" in s0 or "inmobiliario" in s0 or "infraestruct" in s0:
            sector_label = "el sector de construcción e infraestructura"
        elif "logist" in s0 or "transporte" in s0 or "carga" in s0:
            sector_label = "la cadena logística y de distribución"
        elif "salud" in s0 or "farma" in s0 or "medico" in s0:
            sector_label = "el sector salud y farmacéutico"
        elif "software" in s0 or "tech" in s0 or "ti" in s0:
            sector_label = "la industria de tecnología y servicios empresariales"
        elif "manufac" in s0 or "quimic" in s0 or "industrial" in s0:
            sector_label = "el sector industrial y manufacturero"

    # Touch 1: LinkedIn Connection Invite (strictly under 300 chars for LinkedIn limit)
    t1_invite = (
        "{salutation}, sigo el crecimiento de {clean_name} en {city}. "
        f"Nos especializamos en {pitch_core[:95]} para organizaciones de {sector_label}. "
        "Me gustaría conectar para compartir perspectivas del mercado. Saludos."
    )
    if len(t1_invite) > 295:
        t1_invite = (
            "{salutation}, sigo con atención a {clean_name} en {city}. "
            "Me gustaría conectar por aquí para compartir sinergias y buenas prácticas en "
            f"{sector_label}. Saludos."
        )

    # Touch 2: Executive Cold Email (Hook + Core Value + Low Friction Call to Action)
    t2_subject = "{clean_name} // Oportunidad de optimización y eficiencia en {city}"
    t2_body = (
        "{salutation},\n\n"
        "Te contacto porque en tu rol como {contact_title} de {clean_name}, "
        f"garantizar eficiencia y rentabilidad en {sector_label} es una prioridad central.\n\n"
        f"Ayudamos a compañías líderes a través de: {pitch_core}.\n\n"
        "Nuestros clientes suelen experimentar una reducción significativa en fricciones operativas "
        "y una aceleración directa en sus resultados desde las primeras semanas de adopción.\n\n"
        "¿Tendrías 10 minutos este jueves o viernes para revisar brevemente si esta solución "
        "hace sentido dentro de la hoja de ruta de {clean_name}?\n\n"
        "Quedo a tu disposición,\n"
        "Equipo de Desarrollo Corporativo"
    )

    # Touch 3: Follow-up Email (Social Proof & Business Impact)
    t3_subject = "Re: {clean_name} // Caso de éxito y reducción de fricción operativa"
    t3_body = (
        "{salutation},\n\n"
        "Dando seguimiento a mi nota anterior sobre eficiencias para {clean_name}:\n\n"
        f"Compañías de referencia en {sector_label} que han implementado nuestra propuesta "
        "han logrado ahorros operativos medibles y mayor agilidad de respuesta en sus operaciones "
        "en {city}.\n\n"
        "¿Te resultaría conveniente tener una llamada de exploración de 10 minutos esta semana?\n\n"
        "Saludos cordiales,\n"
        "Equipo de Desarrollo Corporativo"
    )

    # Touch 4: Executive Routing Question (Alternative Contact)
    t4_subject = "¿Quién lidera esta iniciativa en {clean_name}?"
    t4_body = (
        "{salutation},\n\n"
        "Comprendo que tu agenda como {contact_title} de {clean_name} debe estar muy apretada.\n\n"
        f"Si tú no eres la persona que evalúa directamente iniciativas de {pitch_core[:60]} "
        "dentro de {clean_name}, ¿me podrías orientar con quién de tu equipo directivo deberíamos coordinar?\n\n"
        "Agradezco mucho tu tiempo y guía.\n\n"
        "Atentamente,\n"
        "Equipo de Desarrollo Corporativo"
    )

    # Touch 5: Graceful Breakup / Keep on file
    t5_subject = "Último contacto // Contacto a futuro con {clean_name}"
    t5_body = (
        "{salutation},\n\n"
        "Para no saturar tu bandeja de entrada, entiendo que por el momento las prioridades de {clean_name} "
        "están enfocadas en otros frentes estratégicos.\n\n"
        f"Dejo nuestros canales abiertos por si más adelante surge la necesidad de activar sinergias en {sector_label}.\n\n"
        "Muchos éxitos en el cierre de metas del equipo,\n"
        "Equipo de Desarrollo Corporativo"
    )

    return {
        "touch1_linkedin_invite": t1_invite,
        "touch2_email_subject": t2_subject,
        "touch2_email_body": t2_body,
        "touch3_email_subject": t3_subject,
        "touch3_email_body": t3_body,
        "touch4_email_subject": t4_subject,
        "touch4_email_body": t4_body,
        "touch5_email_subject": t5_subject,
        "touch5_email_body": t5_body,
    }

