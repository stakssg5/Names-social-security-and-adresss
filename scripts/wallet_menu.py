#!/usr/bin/env python3
"""
Minimal WalletGen-style CLI menu.

- Implements option [9]: brain wallet generate/check
- Other menu options are placeholders for this demo

Reuses the existing wallet logic in scripts/wallet_brain.py via a dynamic import,
so we don't duplicate cryptography helpers here.
"""
from __future__ import annotations

import getpass
import importlib.util
import os
import sys
from typing import Optional


THIS_DIR = os.path.dirname(os.path.abspath(__file__))
WALLET_BRAIN_PATH = os.path.join(THIS_DIR, "wallet_brain.py")
WALLET_NET_PATH = os.path.join(THIS_DIR, "wallet_net.py")


def _load_wallet_brain():
    spec = importlib.util.spec_from_file_location("wallet_brain", WALLET_BRAIN_PATH)
    if spec is None or spec.loader is None:  # pragma: no cover
        raise RuntimeError("Failed to load wallet_brain module")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    return mod


def _load_wallet_net():
    spec = importlib.util.spec_from_file_location("wallet_net", WALLET_NET_PATH)
    if spec is None or spec.loader is None:  # pragma: no cover
        raise RuntimeError("Failed to load wallet_net module")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    return mod


def print_banner() -> None:
    banner = r"""
************************************************************
                  WalletGen by Python (demo)
************************************************************
[1]  - generate one BTC wallet
[2]  - generate one EVM wallet (ETH, BNB, MATIC e.t.c)
[3]  - search BTC wallets with balance (Internet - slower) [demo]
[4]  - search BTC wallets with balance (database - faster) [demo]
[5]  - search EVM wallets with balance (Internet - slower) [demo]
[6]  - search EVM wallets with balance (database - faster) [demo]
[7]  - recovery your bitcoin wallet [demo]
[8]  - support the developer [demo]
[9]  - brain wallet generate/check
""".rstrip()
    print(banner)


def ask_choice() -> Optional[int]:
    try:
        raw = input("\nselect an action using the key: ")
    except EOFError:
        return None
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def handle_brain_wallet(wallet_brain_mod) -> None:
    # Ask for the passphrase; fall back to input if getpass fails
    try:
        passphrase = getpass.getpass("\nEnter passphrase: ")
    except Exception:
        passphrase = input("\nEnter passphrase: ")

    if not passphrase:
        print("Passphrase is empty; aborting.")
        return

    # Reuse helpers from wallet_brain
    privkey = wallet_brain_mod.private_key_from_passphrase(passphrase)
    priv_hex = privkey.hex()
    _priv, pub_c, pub_u = wallet_brain_mod.derive_keys(privkey)

    # Bitcoin addresses
    bech32_addr, p2sh_addr, p2pkh_addr = (
        wallet_brain_mod.bitcoin_addresses_from_compressed_pubkey(pub_c)
    )

    # Ethereum address
    eth_pub = pub_u[1:]
    eth_addr = wallet_brain_mod.to_checksum_address(
        wallet_brain_mod.keccak_256(eth_pub)[-20:]
    )

    # Try to fetch live balances
    btc_balance_line = None
    eth_balance_line = None
    try:
        wallet_net = _load_wallet_net()
        sats = wallet_net.fetch_btc_balance_sats(bech32_addr)
        btc_balance_line = f"confirmed balance: {sats} sats"
        wei = wallet_net.fetch_eth_balance_wei(eth_addr)
        eth_balance_line = f"balance:         {wallet_net.format_eth_from_wei(wei)} ETH"
    except Exception:
        # Network optional; continue silently
        pass

    # Output matches the style from wallet_brain.py
    print("\n[Bitcoin Wallet]")
    print(f"Bech32 address:  {bech32_addr}")
    print(f"P2SH address:    {p2sh_addr}")
    print(f"P2PKH address:   {p2pkh_addr}")
    print(f"public key:      {pub_c.hex()}")
    print(f"private key:     {priv_hex}")
    print(f"mnemonic:        {passphrase}")
    if btc_balance_line:
        print(btc_balance_line)

    print("\n[EVM/Ethereum Wallet]")
    print(f"address:         {eth_addr}")
    print(f"public key:      0x{eth_pub.hex()}")
    print(f"private key:     0x{priv_hex}")
    print(f"mnemonic:        {passphrase}")
    if eth_balance_line:
        print(eth_balance_line)


def main() -> int:
    print_banner()
    choice = ask_choice()

    if choice == 9:
        wallet_brain = _load_wallet_brain()
        handle_brain_wallet(wallet_brain)
        return 0

    if choice in {1, 2, 3, 4, 5, 6, 7, 8}:
        print("\nThis option is a placeholder in this demo. Use [9].")
        return 0

    print("\nInvalid selection. Use [9] for brain wallet.")
    return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
