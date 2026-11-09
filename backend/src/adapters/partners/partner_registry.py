"""
Commercial Partner Registry Adapter for Michito v1.2.
Provides multi-partner affiliate resolution, commission rates, and partner discounts.
"""

from typing import Dict, Optional, List
from src.domain.entities.partner import Partner


class PartnerRegistry:
    """
    Registry of authorized commercial partners and channel affiliates.
    Supports multi-partner attribution (Tinkko, Event Fairs, Hebi, Innpulsa, Ruta N).
    """

    _PARTNERS: Dict[str, Partner] = {
        "direct": Partner(
            partner_id="direct",
            name="Direct Web Customer",
            commission_rate=0.0,
            discount_rate=0.0,
            badge_text="Michito Intent Engine™ Directo",
            default_campaign_id="chiketto",
            description="Ventas directas orgánicas desde michito.co.",
            active=True,
        ),
        "tinkko": Partner(
            partner_id="tinkko",
            name="Tinkko Coworking & Sedes",
            commission_rate=0.25,
            discount_rate=0.10,
            badge_text="🤝 Alianza Oficial: Beneficio Exclusivo para Residentes Tinkko",
            default_campaign_id="tinkko_enterprise_offices",
            description="Red de espacios corporativos y coworking en Medellín y Bogotá.",
            active=True,
        ),
        "eventos_medellin": Partner(
            partner_id="eventos_medellin",
            name="Plaza Mayor & Eventos B2B",
            commission_rate=0.20,
            discount_rate=0.10,
            badge_text="🎪 Partner Oficial de Ferias y Convenciones",
            default_campaign_id="eventos_ferias_b2b",
            description="Operadores de ferias comerciales, congresos y matchmaking de compradores.",
            active=True,
        ),
        "plazamayor": Partner(
            partner_id="plazamayor",
            name="Plaza Mayor Medellín",
            commission_rate=0.20,
            discount_rate=0.10,
            badge_text="🎪 Alianza Plaza Mayor Convenciones & Exposiciones",
            default_campaign_id="eventos_ferias_b2b",
            description="Pabellones feriales y ruedas de negocios en Plaza Mayor Medellín.",
            active=True,
        ),
        "hebi": Partner(
            partner_id="hebi",
            name="Hebi B2B Cartera",
            commission_rate=0.20,
            discount_rate=0.05,
            badge_text="🛡️ Partner Oficial Hebi Due Diligence",
            default_campaign_id="hebi",
            description="Debida diligencia de contratistas y recuperación de cartera B2B.",
            active=True,
        ),
        "rutan": Partner(
            partner_id="rutan",
            name="Ruta N Medellín",
            commission_rate=0.15,
            discount_rate=0.15,
            badge_text="🚀 Ecosistema de Innovación Ruta N",
            default_campaign_id="chiketto",
            description="Comunidad de startups y empresas tecnológicas de base digital.",
            active=True,
        ),
    }

    @classmethod
    def get(cls, partner_id: Optional[str]) -> Partner:
        """
        Resolves a partner by slug (case-insensitive).
        Defaults cleanly to 'direct' if not found or empty.
        """
        if not partner_id:
            return cls._PARTNERS["direct"]
        clean_id = partner_id.strip().lower()
        return cls._PARTNERS.get(clean_id, cls._PARTNERS["direct"])

    @classmethod
    def list_active(cls) -> List[Partner]:
        """Returns all currently active commercial partners."""
        return [p for p in cls._PARTNERS.values() if p.active and p.partner_id != "direct"]

    @classmethod
    def register_partner(cls, partner: Partner) -> None:
        """Dynamically registers or updates a partner."""
        cls._PARTNERS[partner.partner_id.lower()] = partner
