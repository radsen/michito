"""
Backward compatibility bridge for company segments.
Domain source of truth lives in src.domain.value_objects.company_segment.
"""

from src.domain.value_objects.company_segment import (
    SEGMENTS,
    get_segment_info,
    list_supported_segments,
)

__all__ = ["SEGMENTS", "get_segment_info", "list_supported_segments"]

