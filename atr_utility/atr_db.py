from __future__ import annotations

from typing import Dict, List, Tuple

# Minimal sample ATR database (extend as needed)
# Format: ATR hex (no spaces) -> description
KNOWN_ATRS: Dict[str, str] = {
    # JCOP 2.x/3.x common patterns (examples — may vary by card and configuration)
    "3B8F8001804F0CA000000306030001000000006A": "NXP JCOP (example, T=1)",
    "3B9F96801FC78031E073FE211B66D001564A434F5033322E3331": "NXP JCOP 3.2.31 (example)",
    # Generic examples
    "3B00": "Minimal T=0 example (synthetic)",
}


def normalize_hex(s: str) -> str:
    return s.replace(" ", "").replace("-", "").upper()


def search_known_atrs(query: str) -> List[Tuple[str, str]]:
    """Return list of (atr_hex, description) that contain the query substring."""
    q = normalize_hex(query)
    return [(k, v) for k, v in KNOWN_ATRS.items() if q in k]
