"""
Campaign Profile Loader & Cadence Formatter
Loads and parses campaign YAML profiles for the Universal B2B Prospector Engine.
"""

import os
import re
import glob
from typing import Dict, Any, List, Optional
import json

try:
    import yaml  # type: ignore
    _yaml_parser: Any = yaml
except ImportError:
    _yaml_parser = None

# Locate campaigns directory at project root
PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../")
)
CAMPAIGNS_DIR = os.path.join(PROJECT_ROOT, "campaigns")

DEFAULT_ROLES = [
    "Gerente General",
    "Director de Operaciones",
    "COO",
    "Director Financiero",
    "CFO",
    "Director de Infraestructura"
]


def list_available_campaigns() -> List[str]:
    """Returns a list of all available campaign profile IDs."""
    if not os.path.exists(CAMPAIGNS_DIR):
        return []
    files = glob.glob(os.path.join(CAMPAIGNS_DIR, "*.yaml")) + glob.glob(os.path.join(CAMPAIGNS_DIR, "*.yml"))
    campaigns = []
    for f in sorted(files):
        base = os.path.splitext(os.path.basename(f))[0]
        campaigns.append(base)
    return campaigns


def load_campaign(campaign_name_or_path: str) -> Dict[str, Any]:
    """
    Loads a campaign profile by ID or direct file path.
    Preserves all multi-client target filters: country, currency, cities, sectors,
    categories, keywords_include, keywords_exclude, and roles.
    """
    # 1. Check direct file path
    file_path = None
    if os.path.exists(campaign_name_or_path):
        file_path = campaign_name_or_path
    else:
        # Check inside campaigns directory
        candidate_yaml = os.path.join(CAMPAIGNS_DIR, f"{campaign_name_or_path}.yaml")
        candidate_yml = os.path.join(CAMPAIGNS_DIR, f"{campaign_name_or_path}.yml")
        if os.path.exists(candidate_yaml):
            file_path = candidate_yaml
        elif os.path.exists(candidate_yml):
            file_path = candidate_yml

    if not file_path or not os.path.exists(file_path):
        available = list_available_campaigns()
        raise FileNotFoundError(
            f"Campaign '{campaign_name_or_path}' not found. "
            f"Available campaigns in {CAMPAIGNS_DIR}: {', '.join(available)}"
        )

    with open(file_path, "r", encoding="utf-8") as f:
        if _yaml_parser is not None and hasattr(_yaml_parser, "safe_load"):
            data = _yaml_parser.safe_load(f) or {}
        else:
            data = json.load(f) or {}

    campaign_id = data.get("id") or os.path.splitext(os.path.basename(file_path))[0]
    name = data.get("name") or campaign_id.replace("_", " ").title()
    target = data.get("target") or {}
    touches = data.get("touches") or {}
    angles = data.get("angles") or {}
    specs = data.get("specs") or {}
    teaser = data.get("teaser") or {}

    roles = target.get("roles") or DEFAULT_ROLES

    return {
        "id": campaign_id,
        "name": name,
        "client_id": data.get("client_id") or campaign_id.split("_")[0],
        "description": data.get("description", ""),
        "target": {
            "country": target.get("country", "CO"),
            "currency": target.get("currency", "DOP" if target.get("country", "CO").upper() == "DO" else "COP"),
            "city": target.get("city", "all"),
            "cities": target.get("cities", []),
            "segment": target.get("segment", "midmarket"),
            "min_revenue_cop": target.get("min_revenue_cop", "$5.000M COP"),
            "sectors": target.get("sectors", ["all"]),
            "categories": target.get("categories", []),
            "keywords_include": target.get("keywords_include", []),
            "keywords_exclude": target.get("keywords_exclude", []),
            "roles": roles
        },
        "specs": specs,
        "angles": {
            "recommended": angles.get("recommended", "Propuesta de Valor Comercial Personalizada")
        },
        "teaser": teaser,
        "touches": touches,
        "file_path": file_path
    }


def clean_company_name(name: str) -> str:
    """Strips standard legal corporate suffixes and parentheticals for natural conversational copy."""
    clean = re.sub(r"\(.*?\)", "", name)
    clean = re.sub(r"\b(S\.A\.S\.|S\.A\.S|SAS|S\.A\.|S\.A|SA|LTDA\.|LTDA|E\.U\.|E\.U|B\.V\.|B\.V|SRL|S\.R\.L\.|EIRL|E\.I\.R\.L\.)\b|(&\s*C[ií]a\.?)", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\s+", " ", clean)
    return clean.strip(" .-,")


def format_touch(template_text: str, context: Dict[str, Any]) -> str:
    """
    Safely interpolates context variables into touch templates without crashing on stray braces.
    """
    if not template_text:
        return ""

    company_name = context.get("company_name", "su empresa")
    clean_name = clean_company_name(company_name)
    contact_name = context.get("contact_name")
    contact_title = context.get("contact_title", "Director(a)")
    city = context.get("city", "Colombia")
    sector = context.get("sector", "general")

    salutation = f"Hola {contact_name}" if contact_name and contact_name not in ("Director(a)", "Gerente", "") else "Hola"

    replacements = {
        "{company_name}": company_name,
        "{clean_name}": clean_name,
        "{contact_name}": contact_name or "Director(a)",
        "{contact_title}": contact_title,
        "{city}": city,
        "{sector}": sector,
        "{salutation}": salutation
    }

    result = template_text
    for key, val in replacements.items():
        result = result.replace(key, str(val))
    return result.strip()


def compile_teaser_html(campaign_config: Dict[str, Any], output_path: str) -> Optional[str]:
    """
    Compiles an institutional 1-page HTML teaser from campaign specs if teaser is enabled.
    """
    teaser = campaign_config.get("teaser") or {}
    if not teaser or not teaser.get("enabled"):
        return None

    template_path = os.path.join(PROJECT_ROOT, "templates", "teaser_one_pager_base.html")
    if not os.path.exists(template_path):
        return None

    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()

    specs = campaign_config.get("specs") or {}
    replacements = {
        "{{ teaser_title }}": campaign_config.get("name", "Ficha Técnica Confidencial"),
        "{{ headline }}": teaser.get("headline", campaign_config.get("name", "")),
        "{{ subheadline }}": teaser.get("subheadline", ""),
        "{{ summary }}": teaser.get("summary", ""),
        "{{ price_cop }}": specs.get("price_cop", "A convenir"),
        "{{ built_area }}": specs.get("built_area", "N/A"),
        "{{ lot_area }}": specs.get("lot_area", "N/A"),
        "{{ clear_height }}": specs.get("clear_height", "N/A"),
        "{{ floor_load }}": specs.get("floor_load", "N/A"),
        "{{ docks }}": specs.get("docks", "N/A"),
        "{{ kva }}": specs.get("kva", "N/A"),
        "{{ pot_impact }}": specs.get("pot_impact", "N/A"),
        "{{ corridor }}": specs.get("corridor", "Antioquia"),
    }
    for k, v in replacements.items():
        html = html.replace(k, str(v))

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    return output_path

