from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Optional


def _bytes_from_hex(s: str) -> bytes:
    s = s.strip().replace(" ", "").replace("-", "")
    if s.startswith("0x") or s.startswith("0X"):
        s = s[2:]
    if len(s) % 2 != 0:
        raise ValueError("Hex string must have an even number of characters")
    return bytes.fromhex(s)


def to_hex(data: bytes) -> str:
    return data.hex(" ").upper()


@dataclass
class ATRParseResult:
    raw: bytes
    ts: int
    t0: int
    k: int
    historical_bytes: bytes
    interface_bytes: List[Dict[str, int]]
    protocols: List[int]
    tck: Optional[int]
    computed_tck: Optional[int]
    tck_valid: Optional[bool]

    def to_dict(self) -> Dict[str, object]:
        return {
            "raw": to_hex(self.raw),
            "ts": f"0x{self.ts:02X}",
            "t0": f"0x{self.t0:02X}",
            "k": self.k,
            "historical_bytes": to_hex(self.historical_bytes),
            "interface_bytes": [
                {k: f"0x{v:02X}" for k, v in group.items()} for group in self.interface_bytes
            ],
            "protocols": [f"T={p}" for p in self.protocols],
            "tck": None if self.tck is None else f"0x{self.tck:02X}",
            "computed_tck": None
            if self.computed_tck is None
            else f"0x{self.computed_tck:02X}",
            "tck_valid": self.tck_valid,
        }


def parse_atr(data: bytes | str) -> ATRParseResult:
    """Parse an ATR and return a structured result.

    Notes:
    - TCK is present when any protocol T != 0 is indicated in any TDx.
    - TCK validates when XOR of T0..last historical byte XOR TCK == 0x00.
    """
    if isinstance(data, str):
        raw = _bytes_from_hex(data)
    else:
        raw = bytes(data)

    if len(raw) < 2:
        raise ValueError("ATR must be at least 2 bytes (TS and T0)")

    idx = 0
    ts = raw[idx]
    idx += 1
    t0 = raw[idx]
    idx += 1

    y = (t0 & 0xF0) >> 4  # presence bits for TA1/TB1/TC1/TD1
    k = t0 & 0x0F  # number of historical bytes

    interface_bytes: List[Dict[str, int]] = []
    protocols: List[int] = []

    y_i = y
    group_index = 1
    td_present = (y_i & 0x8) != 0

    while True:
        group: Dict[str, int] = {}
        if y_i & 0x1:
            group[f"TA{group_index}"] = raw[idx]
            idx += 1
        if y_i & 0x2:
            group[f"TB{group_index}"] = raw[idx]
            idx += 1
        if y_i & 0x4:
            group[f"TC{group_index}"] = raw[idx]
            idx += 1
        if y_i & 0x8:
            td = raw[idx]
            group[f"TD{group_index}"] = td
            idx += 1
            protocols.append(td & 0x0F)
            y_i = (td & 0xF0) >> 4
            td_present = True
        else:
            td_present = False

        if group:
            interface_bytes.append(group)

        if not td_present:
            break
        group_index += 1

    # Historical bytes
    if len(raw) < idx + k:
        raise ValueError("ATR malformed: not enough bytes for historical bytes")
    historical = raw[idx : idx + k]
    idx += k

    # TCK (check byte) present only if any T != 0
    tck: Optional[int] = None
    computed_tck: Optional[int] = None
    tck_valid: Optional[bool] = None

    if any(p != 0 for p in protocols):
        if len(raw) <= idx:
            raise ValueError("ATR indicates TCK present but data ended early")
        tck = raw[idx]
        idx += 1
        # Compute bytes T0 .. byte before TCK
        xor_val = 0
        for b in raw[1 : len(raw) - 1]:
            xor_val ^= b
        computed_tck = xor_val
        tck_valid = (computed_tck ^ tck) == 0

    # If extra trailing bytes exist, that's malformed but include them in raw; basic parser stops here

    return ATRParseResult(
        raw=raw,
        ts=ts,
        t0=t0,
        k=k,
        historical_bytes=historical,
        interface_bytes=interface_bytes,
        protocols=protocols if protocols else [0],
        tck=tck,
        computed_tck=computed_tck,
        tck_valid=tck_valid,
    )


def build_simple_atr(
    *,
    ts: int = 0x3B,
    protocol: int = 0,  # 0 or 1
    historical_bytes: bytes | str = b"",
    ta1: Optional[int] = None,
    tb1: Optional[int] = None,
    tc1: Optional[int] = None,
) -> bytes:
    """Build a simple ATR with optional TA1/TB1/TC1 and a single protocol.

    This does not attempt to craft complex multi-group interface bytes.
    - If protocol != 0, a TCK will be appended automatically.
    - historical_bytes can be a hex string or bytes.
    """
    if isinstance(historical_bytes, str):
        hist = _bytes_from_hex(historical_bytes) if historical_bytes else b""
    else:
        hist = historical_bytes

    y1 = 0
    if ta1 is not None:
        y1 |= 0x1
    if tb1 is not None:
        y1 |= 0x2
    if tc1 is not None:
        y1 |= 0x4
    # We will always include TD1 to announce protocol
    y1 |= 0x8

    k = len(hist)
    if k > 15:
        raise ValueError("Historical bytes length must be <= 15 for simple builder")

    t0 = (y1 << 4) | k

    out: List[int] = [ts, t0]
    if ta1 is not None:
        out.append(ta1 & 0xFF)
    if tb1 is not None:
        out.append(tb1 & 0xFF)
    if tc1 is not None:
        out.append(tc1 & 0xFF)
    # TD1
    td1 = (0x00 << 4) | (protocol & 0x0F)  # no further groups
    out.append(td1)

    out.extend(hist)

    if protocol != 0:
        # Compute and append TCK so that XOR(T0..TCK) == 0
        xor_val = 0
        for b in out[1:]:
            xor_val ^= b
        tck = xor_val
        out.append(tck)

    return bytes(out)
