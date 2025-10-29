from __future__ import annotations

from typing import List, Optional, Tuple

try:
    from smartcard.System import readers as pcsc_readers
except Exception:  # pragma: no cover - pyscard may not be installed
    pcsc_readers = None  # type: ignore


def list_readers() -> List[str]:
    if pcsc_readers is None:
        return []
    return [str(r) for r in pcsc_readers()]


def connect_and_get_atr(reader_identifier: Optional[str | int] = None) -> Tuple[str, bytes]:
    """Connect to a reader and return (reader_name, ATR bytes).

    reader_identifier can be an index (int) or case-insensitive substring of the reader name.
    """
    if pcsc_readers is None:
        raise RuntimeError(
            "pyscard not available. Install system PC/SC libraries and the pyscard package."
        )

    available = pcsc_readers()
    if not available:
        raise RuntimeError("No PC/SC readers found")

    if reader_identifier is None:
        # default to first reader
        reader = available[0]
    elif isinstance(reader_identifier, int):
        if reader_identifier < 0 or reader_identifier >= len(available):
            raise IndexError("Reader index out of range")
        reader = available[reader_identifier]
    else:
        name_lower = str(reader_identifier).lower()
        matches = [r for r in available if name_lower in str(r).lower()]
        if not matches:
            raise RuntimeError("No reader matched given name/substr")
        reader = matches[0]

    connection = reader.createConnection()
    connection.connect()  # default protocol negotiation
    atr: bytes = bytes(connection.getATR())
    return (str(reader), atr)
