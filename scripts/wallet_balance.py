#!/usr/bin/env python3
"""
CLI balance checker for BTC and ETH.

Usage examples:
  - Interactive (passphrase -> derive addresses -> balances):
      python3 scripts/wallet_balance.py

  - Provide passphrase via stdin:
      printf "Hello, World!\n" | python3 scripts/wallet_balance.py

  - Check specific addresses:
      python3 scripts/wallet_balance.py --btc bc1... --eth 0x...
"""
from __future__ import annotations

import argparse
import getpass
import importlib.util
import os
import sys
from typing import Optional

THIS_DIR = os.path.dirname(os.path.abspath(__file__))


def _load_module(module_filename: str, module_name: str):
    path = os.path.join(THIS_DIR, module_filename)
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module: {module_name}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    return mod


def _load_wallet_brain():
    return _load_module("wallet_brain.py", "wallet_brain")


def _load_wallet_net():
    return _load_module("wallet_net.py", "wallet_net")


def derive_from_passphrase(passphrase: str):
    wallet_brain = _load_wallet_brain()
    privkey = wallet_brain.private_key_from_passphrase(passphrase)
    _priv, pub_c, pub_u = wallet_brain.derive_keys(privkey)

    # BTC
    bech32_addr, p2sh_addr, p2pkh_addr = (
        wallet_brain.bitcoin_addresses_from_compressed_pubkey(pub_c)
    )

    # ETH
    eth_pub = pub_u[1:]
    eth_addr = wallet_brain.to_checksum_address(
        wallet_brain.keccak_256(eth_pub)[-20:]
    )
    return {
        "btc": {
            "bech32": bech32_addr,
            "p2sh": p2sh_addr,
            "p2pkh": p2pkh_addr,
        },
        "eth": eth_addr,
        "priv_hex": privkey.hex(),
        "pub_c_hex": pub_c.hex(),
    }


def fetch_balances(btc_addr: Optional[str], eth_addr: Optional[str]):
    wallet_net = _load_wallet_net()
    results = {}
    if btc_addr:
        try:
            sats = wallet_net.fetch_btc_balance_sats(btc_addr)
        except Exception as e:
            sats = None
            results["btc_error"] = str(e)
        results["btc_sats"] = sats
    if eth_addr:
        try:
            wei = wallet_net.fetch_eth_balance_wei(eth_addr)
            eth = wallet_net.format_eth_from_wei(wei)
        except Exception as e:
            wei = None
            eth = None
            results["eth_error"] = str(e)
        results["eth_wei"] = wei
        results["eth"] = eth
    return results


def parse_args(argv):
    p = argparse.ArgumentParser(description="Check BTC and ETH balances")
    p.add_argument("--btc", dest="btc", help="BTC address to check")
    p.add_argument("--eth", dest="eth", help="ETH address to check")
    p.add_argument(
        "--no-passphrase", action="store_true", help="Do not prompt for passphrase"
    )
    return p.parse_args(argv)


def main(argv):
    args = parse_args(argv)

    btc_addr = args.btc
    eth_addr = args.eth

    # If neither address provided, and not opting out of passphrase prompt, derive from passphrase
    derived = None
    if not btc_addr and not eth_addr and not args.no_passphrase:
        if sys.stdin.isatty():
            try:
                passphrase = getpass.getpass("Enter passphrase: ")
            except Exception:
                passphrase = input("Enter passphrase: ")
        else:
            passphrase = sys.stdin.read().strip()
        if not passphrase:
            print("Passphrase is empty; aborting.")
            return 1
        derived = derive_from_passphrase(passphrase)
        btc_addr = derived["btc"]["bech32"]
        eth_addr = derived["eth"]

    balances = fetch_balances(btc_addr, eth_addr)

    if derived:
        print("\n[Bitcoin Wallet]")
        print(f"Bech32 address:  {derived['btc']['bech32']}")
        print(f"P2SH address:    {derived['btc']['p2sh']}")
        print(f"P2PKH address:   {derived['btc']['p2pkh']}")
        print(f"public key:      {derived['pub_c_hex']}")
        print(f"private key:     {derived['priv_hex']}")
        if balances.get("btc_sats") is not None:
            print(f"confirmed balance: {balances['btc_sats']} sats")

        print("\n[EVM/Ethereum Wallet]")
        print(f"address:         {derived['eth']}")
        print(f"public key:      0x{derived['pub_c_hex'][2:]}")
        print(f"private key:     0x{derived['priv_hex']}")
        if balances.get("eth") is not None:
            print(f"balance:         {balances['eth']} ETH")

    # If addresses were provided explicitly, just show balances
    if not derived:
        if btc_addr:
            print(f"BTC {btc_addr}")
            if balances.get("btc_sats") is not None:
                print(f"  confirmed: {balances['btc_sats']} sats")
            if "btc_error" in balances:
                print(f"  error: {balances['btc_error']}")
        if eth_addr:
            print(f"ETH {eth_addr}")
            if balances.get("eth") is not None:
                print(f"  balance: {balances['eth']} ETH")
            if "eth_error" in balances:
                print(f"  error: {balances['eth_error']}")

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
