"""
Backward-compatibility re-export.
Campaign loader has moved to src.adapters.campaigns.campaign_loader.
"""

from src.adapters.campaigns.campaign_loader import (
    load_campaign,
    list_available_campaigns,
    clean_company_name,
    format_touch,
    compile_teaser_html,
    CAMPAIGNS_DIR,
    DEFAULT_ROLES,
)

__all__ = [
    "load_campaign",
    "list_available_campaigns",
    "clean_company_name",
    "format_touch",
    "compile_teaser_html",
    "CAMPAIGNS_DIR",
    "DEFAULT_ROLES",
]
