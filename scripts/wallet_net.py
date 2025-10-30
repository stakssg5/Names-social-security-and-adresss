#!/usr/bin/env python3
"""
Lightweight network helpers to fetch on-chain balances.

- BTC (mainnet) via Blockstream API (fallback: mempool.space)
- ETH (mainnet) via Cloudflare's public JSON-RPC endpoint

No external HTTP libraries are required; uses urllib from the standard library.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Dict, Optional


class NetworkError(RuntimeError):
    pass


# ----------------------------- BTC (sats) -----------------------------

def _http_get_json(url: str, timeout: float = 10.0) -> Dict:
    req = urllib.request.Request(url, headers={"User-Agent": "wallet-net/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
    except urllib.error.URLError as e:  # pragma: no cover
        raise NetworkError(str(e)) from e
    try:
        return json.loads(data.decode("utf-8"))
    except Exception as e:  # pragma: no cover
        raise NetworkError("Invalid JSON response") from e


def fetch_btc_balance_sats(address: str, timeout: float = 10.0) -> int:
    """Return confirmed balance in satoshis for a BTC address.

    Uses Blockstream API; falls back to mempool.space if necessary.
    """
    url_primary = f"https://blockstream.info/api/address/{address}"
    try:
        j = _http_get_json(url_primary, timeout)
        funded = int(j.get("chain_stats", {}).get("funded_txo_sum", 0))
        spent = int(j.get("chain_stats", {}).get("spent_txo_sum", 0))
        return max(funded - spent, 0)
    except Exception:
        # Fallback
        url_fallback = f"https://mempool.space/api/address/{address}"
        j = _http_get_json(url_fallback, timeout)
        funded = int(j.get("chain_stats", {}).get("funded_txo_sum", 0))
        spent = int(j.get("chain_stats", {}).get("spent_txo_sum", 0))
        return max(funded - spent, 0)


# ----------------------------- ETH (wei) ------------------------------

def fetch_eth_balance_wei(address: str, rpc_url: str = "https://cloudflare-eth.com", timeout: float = 10.0) -> int:
    """Return ETH balance in wei using eth_getBalance.

    Args:
        address: EIP-55 or lowercase hex address (0x...)
        rpc_url: Public Ethereum RPC endpoint
        timeout: Request timeout in seconds
    """
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "eth_getBalance",
        "params": [address, "latest"],
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        rpc_url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "wallet-net/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            j = json.loads(raw)
    except urllib.error.URLError as e:  # pragma: no cover
        raise NetworkError(str(e)) from e

    if "error" in j:  # pragma: no cover
        raise NetworkError(f"RPC error: {j['error']}")

    result = j.get("result")
    if not isinstance(result, str) or not result.startswith("0x"):
        raise NetworkError("Invalid RPC result for eth_getBalance")
    return int(result, 16)


def format_eth_from_wei(wei: int) -> str:
    # Format with up to 18 decimals, trimming trailing zeros
    whole = wei // 10**18
    frac = wei % 10**18
    if frac == 0:
        return str(whole)
    frac_str = f"{frac:018d}".rstrip("0")
    return f"{whole}.{frac_str}"
