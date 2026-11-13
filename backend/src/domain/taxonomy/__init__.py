"""
Taxonomy Domain Module.
Provides Universal UN ISIC Rev. 4 / DANE CIIU Rev. 4 A.C. classification,
sub-millisecond token index, and dynamic multi-country resolution.
"""

from .isic_catalog import UNIVERSAL_ISIC_CATALOG, IsicEntry
from .isic_index import IsicIndex, get_isic_index

__all__ = ["UNIVERSAL_ISIC_CATALOG", "IsicEntry", "IsicIndex", "get_isic_index"]

