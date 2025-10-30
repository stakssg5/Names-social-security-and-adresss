#!/usr/bin/env python3
"""
Brain wallet generator/checker for BTC and EVM (Ethereum).

- Derives keys deterministically from a passphrase using SHA-256
- Produces Bitcoin addresses: P2PKH, P2SH-P2WPKH, Bech32 P2WPKH (bc1)
- Produces Ethereum address (EIP-55 checksum), public key and private key

Requirements:
  - ecdsa (pure-python secp256k1)
  - pysha3 (for keccak-256); or pycryptodome as a fallback

This script intentionally avoids heavy dependencies and implements
Base58Check and Bech32 (v0) in pure Python.
"""
from __future__ import annotations

import sys
import os
import getpass
import hashlib
from typing import Iterable, List, Tuple

try:
    from ecdsa import SECP256k1, SigningKey
except Exception as exc:  # pragma: no cover
    sys.stderr.write(
        "Missing dependency 'ecdsa'. Install with: pip install ecdsa\n"
    )
    raise


# -------------------------- Hash helpers --------------------------

def sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def ripemd160(data: bytes) -> bytes:
    try:
        h = hashlib.new("ripemd160")
        h.update(data)
        return h.digest()
    except Exception:  # pragma: no cover
        # Fallback to PyCryptodome if OpenSSL lacks RIPEMD160
        try:
            from Crypto.Hash import RIPEMD160  # type: ignore

            return RIPEMD160.new(data).digest()
        except Exception as e:
            raise RuntimeError(
                "RIPEMD160 not available; install pycryptodome: pip install pycryptodome"
            ) from e


def hash160(data: bytes) -> bytes:
    return ripemd160(sha256(data))


def keccak_256(data: bytes) -> bytes:
    """Return Keccak-256 digest for Ethereum operations.

    Tries pysha3 first, then PyCryptodome. Raises RuntimeError if unavailable.
    """
    # pysha3
    try:  # pragma: no cover
        import sha3  # type: ignore

        k = sha3.keccak_256()
        k.update(data)
        return k.digest()
    except Exception:
        pass

    # PyCryptodome
    try:  # pragma: no cover
        from Crypto.Hash import keccak  # type: ignore

        k = keccak.new(digest_bits=256)
        k.update(data)
        return k.digest()
    except Exception as e:
        raise RuntimeError(
            "Keccak-256 not available; install pysha3 or pycryptodome"
        ) from e


# -------------------------- Base58Check --------------------------
_B58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def _b58_encode(b: bytes) -> str:
    # Convert big-endian bytes to integer
    n = int.from_bytes(b, "big")
    res = []
    while n > 0:
        n, r = divmod(n, 58)
        res.append(_B58_ALPHABET[r])
    # Preserve leading zeroes
    pad = 0
    for ch in b:
        if ch == 0:
            pad += 1
        else:
            break
    return ("1" * pad) + ("".join(reversed(res)) if res else "")


def b58check_encode(version: bytes, payload: bytes) -> str:
    data = version + payload
    checksum = sha256(sha256(data))[:4]
    return _b58_encode(data + checksum)


# -------------------------- Bech32 (BIP173, v0 only) --------------------------
_BECH32_CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"


def _bech32_polymod(values: Iterable[int]) -> int:
    # Generator coefficients per BIP173
    GENERATORS = [0x3b6a57b2, 0x26508e6d, 0x1ea119fa, 0x3d4233dd, 0x2a1462b3]
    chk = 1
    for v in values:
        b = chk >> 25
        chk = ((chk & 0x1FFFFFF) << 5) ^ v
        for i in range(5):
            chk ^= GENERATORS[i] if ((b >> i) & 1) else 0
    return chk


def _bech32_hrp_expand(hrp: str) -> List[int]:
    return [ord(x) >> 5 for x in hrp] + [0] + [ord(x) & 31 for x in hrp]


def _bech32_create_checksum(hrp: str, data: List[int]) -> List[int]:
    values = _bech32_hrp_expand(hrp) + data
    polymod = _bech32_polymod(values + [0, 0, 0, 0, 0, 0]) ^ 1
    return [(polymod >> 5 * (5 - i)) & 31 for i in range(6)]


def _bech32_encode(hrp: str, data: List[int]) -> str:
    combined = data + _bech32_create_checksum(hrp, data)
    return hrp + "1" + "".join([_BECH32_CHARSET[d] for d in combined])


def _convertbits(data: Iterable[int], frombits: int, tobits: int, pad: bool = True) -> List[int]:
    acc = 0
    bits = 0
    ret = []
    maxv = (1 << tobits) - 1
    max_acc = (1 << (frombits + tobits - 1)) - 1
    for value in data:
        if value < 0 or (value >> frombits):
            raise ValueError("invalid value for convertbits")
        acc = ((acc << frombits) | value) & max_acc
        bits += frombits
        while bits >= tobits:
            bits -= tobits
            ret.append((acc >> bits) & maxv)
    if pad:
        if bits:
            ret.append((acc << (tobits - bits)) & maxv)
    elif bits >= frombits or ((acc << (tobits - bits)) & maxv):
        raise ValueError("invalid incomplete group")
    return ret


def bech32_address_p2wpkh(hrp: str, pubkey_hash160: bytes) -> str:
    # witness version 0, program = 20-byte pubkey hash
    data = [0] + _convertbits(pubkey_hash160, 8, 5, True)
    return _bech32_encode(hrp, data)


# -------------------------- Key derivation --------------------------

def private_key_from_passphrase(passphrase: str) -> bytes:
    # Derive 32-byte secret via SHA-256 of UTF-8 bytes
    secret = sha256(passphrase.encode("utf-8"))
    # Ensure in [1, n-1]; if zero (virtually impossible), tweak
    n = SECP256k1.order
    key_int = int.from_bytes(secret, "big") % n
    if key_int == 0:
        key_int = 1
    return key_int.to_bytes(32, "big")


def derive_keys(privkey: bytes) -> Tuple[bytes, bytes, bytes]:
    sk = SigningKey.from_string(privkey, curve=SECP256k1)
    vk = sk.get_verifying_key()
    uncompressed = b"\x04" + vk.to_string()
    x_bytes = vk.to_string()[:32]
    y_bytes = vk.to_string()[32:]
    prefix = b"\x02" if (int.from_bytes(y_bytes, "big") % 2 == 0) else b"\x03"
    compressed = prefix + x_bytes
    return privkey, compressed, uncompressed


# -------------------------- Bitcoin helpers --------------------------

def bitcoin_addresses_from_compressed_pubkey(pubkey_compressed: bytes) -> Tuple[str, str, str]:
    pubkey_hash = hash160(pubkey_compressed)

    # P2PKH (Base58Check, version 0x00)
    p2pkh = b58check_encode(b"\x00", pubkey_hash)

    # P2SH-P2WPKH (Base58Check, version 0x05) with redeem script 0x0014{20-byte-hash}
    redeem_script = b"\x00\x14" + pubkey_hash
    redeem_hash = hash160(redeem_script)
    p2sh_p2wpkh = b58check_encode(b"\x05", redeem_hash)

    # Bech32 P2WPKH (bc1)
    bech32 = bech32_address_p2wpkh("bc", pubkey_hash)

    return bech32, p2sh_p2wpkh, p2pkh


# -------------------------- Ethereum helpers --------------------------

def to_checksum_address(addr_bytes: bytes) -> str:
    hex_addr = addr_bytes.hex()
    hashed = keccak_256(hex_addr.encode("ascii")).hex()
    checksummed = [
        (c.upper() if int(hashed[i], 16) >= 8 else c)
        for i, c in enumerate(hex_addr)
    ]
    return "0x" + "".join(checksummed)


# -------------------------- CLI --------------------------

def main(argv: List[str]) -> int:
    print("""
************************************************************
  WalletGen (brain-wallet) — minimal Python implementation
************************************************************
""".rstrip())

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

    privkey = private_key_from_passphrase(passphrase)
    priv_hex = privkey.hex()
    priv, pub_c, pub_u = derive_keys(privkey)

    # Bitcoin
    bech32_addr, p2sh_addr, p2pkh_addr = bitcoin_addresses_from_compressed_pubkey(pub_c)

    # Ethereum
    # Ethereum public key is the 64-byte X||Y (uncompressed without 0x04)
    eth_pub = pub_u[1:]
    eth_addr = to_checksum_address(keccak_256(eth_pub)[-20:])

    print("\n[Bitcoin Wallet]")
    print(f"Bech32 address:  {bech32_addr}")
    print(f"P2SH address:    {p2sh_addr}")
    print(f"P2PKH address:   {p2pkh_addr}")
    print(f"public key:      {pub_c.hex()}")
    print(f"private key:     {priv_hex}")
    print(f"mnemonic:        {passphrase}")

    print("\n[EVM/Ethereum Wallet]")
    print(f"address:         {eth_addr}")
    print(f"public key:      0x{eth_pub.hex()}")
    print(f"private key:     0x{priv_hex}")
    print(f"mnemonic:        {passphrase}")

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
