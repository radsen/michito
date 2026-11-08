"""
Backward-compatibility re-export.
Deduplication ledger has moved to src.adapters.storage.deduplication_ledger.
"""

from src.adapters.storage.deduplication_ledger import (
    DeduplicationLedger,
    DEFAULT_LEDGER_PATH,
    PERMANENT_EXCLUDED_NITS,
    PERMANENT_EXCLUDED_KEYWORDS,
)

__all__ = [
    "DeduplicationLedger",
    "DEFAULT_LEDGER_PATH",
    "PERMANENT_EXCLUDED_NITS",
    "PERMANENT_EXCLUDED_KEYWORDS",
]
