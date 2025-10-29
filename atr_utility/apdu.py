from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

from .atr import ATRParseResult, parse_atr, to_hex

try:
    # pyscard runtime (optional for environments without PC/SC)
    from smartcard.System import readers as pcsc_readers
except Exception:  # pragma: no cover
    pcsc_readers = None  # type: ignore


@dataclass
class APDUResult:
    apdu: bytes
    sw1: int
    sw2: int
    data: bytes


def _hex_to_bytes(s: str) -> bytes:
    s = s.strip().replace(" ", "").replace("-", "")
    if not s:
        return b""
    return bytes.fromhex(s)


def _expand_variables(text: str, parsed: ATRParseResult) -> str:
    hist_hex = parsed.historical_bytes.hex(" ").upper()
    hist_ns = hist_hex.replace(" ", "")
    atr_hex = parsed.raw.hex(" ").upper()
    atr_ns = atr_hex.replace(" ", "")
    tck = "" if parsed.tck is None else f"{parsed.tck:02X}"
    computed_tck = "" if parsed.computed_tck is None else f"{parsed.computed_tck:02X}"
    variables: Dict[str, str] = {
        "ATR_HEX": atr_hex,
        "ATR_NS": atr_ns,
        "TS": f"{parsed.ts:02X}",
        "T0": f"{parsed.t0:02X}",
        "K": str(parsed.k),
        "HIST_HEX": hist_hex,
        "HIST_NS": hist_ns,
        "TCK": tck,
        "COMPUTED_TCK": computed_tck,
        "PROTOCOLS": " ".join([f"{p:02X}" for p in parsed.protocols]),
    }
    out = text
    for key, value in variables.items():
        out = out.replace("{" + key + "}", value)
    return out


def parse_apdu_script(script_text: str, atr_for_vars: bytes | str) -> List[bytes]:
    """Parse a simple APDU script.

    Format:
      - One command per line: hex bytes separated by spaces
      - Lines beginning with '#' are comments
      - Empty lines are skipped
      - Variables like {ATR_HEX}, {HIST_NS}, {TS}, {T0}, {TCK} are expanded
    """
    parsed = parse_atr(atr_for_vars)
    expanded = _expand_variables(script_text, parsed)
    apdus: List[bytes] = []
    for raw_line in expanded.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.upper().startswith("RESET"):
            # Ignored for now; connection is reset by reinsertion; reserved for future
            continue
        apdus.append(_hex_to_bytes(line))
    return apdus


def send_apdus(reader_identifier: Optional[int | str], apdus: Iterable[bytes]) -> List[APDUResult]:
    if pcsc_readers is None:
        raise RuntimeError("pyscard not available. Install pyscard to use this feature.")
    rlist = pcsc_readers()
    if not rlist:
        raise RuntimeError("No PC/SC readers found")
    if reader_identifier is None:
        reader = rlist[0]
    elif isinstance(reader_identifier, int):
        if reader_identifier < 0 or reader_identifier >= len(rlist):
            raise IndexError("Reader index out of range")
        reader = rlist[reader_identifier]
    else:
        name_lower = str(reader_identifier).lower()
        matches = [r for r in rlist if name_lower in str(r).lower()]
        if not matches:
            raise RuntimeError("No reader matched given name/substr")
        reader = matches[0]

    connection = reader.createConnection()
    connection.connect()  # default protocols

    results: List[APDUResult] = []
    for apdu in apdus:
        data, sw1, sw2 = connection.transmit(list(apdu))
        results.append(APDUResult(apdu=apdu, sw1=sw1, sw2=sw2, data=bytes(data)))
    return results
